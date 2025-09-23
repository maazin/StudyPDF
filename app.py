import streamlit as st
from groq import Groq
import pdfplumber
import os
import gc
from dotenv import load_dotenv
import base64

# ----------------- Load API Key -----------------
load_dotenv()
API_KEY = os.environ.get("GROQ_API_KEY")
if not API_KEY:
    st.error("GROQ_API_KEY not found. Create a .env file with GROQ_API_KEY=your_key and restart.")
    st.stop()

client = Groq(api_key=API_KEY)

# ----------------- Helpers -----------------
def extract_text_from_pdf(uploaded_file):
    """Extracts full text from a PDF file-like object."""
    text = ""
    try:
        # To read the file, we need to reset the pointer to the beginning
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        st.error(f"Could not extract text from PDF: {e}")
    return text

def build_academic_prompt(mode, context, query):
    base = (
        "You are StudyPDF, an academic assistant. Use the document context to give accurate, helpful, and well-structured answers."
    )
    if mode == "Homework / Problem":
        instruction = "Explain step-by-step and give final answers clearly."
    elif mode == "Research Paper":
        instruction = "Summarize methods, contributions, results, and limitations precisely."
    elif mode == "Lecture / Notes":
        instruction = "Extract key points and explain them simply, with examples if possible."
    elif mode == "Flashcards":
        instruction = "Generate short Q&A flashcards from the document."
    else:
        instruction = ""
    # Ensure the final output is HTML-friendly markdown
    return f"{base}\nMode: {mode}\nInstruction: {instruction}\n\nContext:\n{context}\n\nUser Question: {query}\n\nAnswer (in Markdown):"

def call_groq(prompt):
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(str(e))

# ----------------- Page Config -----------------
st.set_page_config(
    page_title="StudyPDF — Academic PDF Assistant",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- Modern Styles -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #f8fafc !important;
        color: #111827 !important;
        line-height: 1.6;
    }

    /* Reduce free space at top */
    section.main > div:first-child {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }

    .stApp { background: #f8fafc !important; min-height: 100vh; }
    header[data-testid="stHeader"], footer, .stDeployButton, div[data-testid="stToolbar"] { display: none !important; }

    .app-header {
        text-align: center;
        margin-bottom: 3rem;
        padding-bottom: 2rem;
        border-bottom: 2px solid #e5e7eb;
    }

    .app-title {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        color: #1f2937 !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: -0.02em;
    }

    .app-subtitle {
        font-size: 1.25rem !important;
        color: #374151 !important;
        font-weight: 400;
        max-width: 700px;
        margin: 0 auto;
        text-align: center;
    }

    .section-header {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1f2937 !important;
        margin: 1rem 0 !important;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-header::before {
        content: '';
        width: 4px; height: 24px;
        background: #6366f1;
        border-radius: 2px;
    }

    .stFileUploader {
        background: #ffffff !important;
        border: 2px dashed #6366f1 !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        text-align: center !important;
        margin-bottom: 1rem !important;
    }

    .info-box {
        background: #eef2ff;
        border: 1px solid #6366f1;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        color: #1e3a8a;
        font-weight: 500;
        font-size: 0.95rem;
    }

    div[data-baseweb="select"] { overflow: visible !important; z-index: 999 !important; }
    ul[role="listbox"] { z-index: 9999 !important; max-height: 300px !important; overflow-y: auto !important; }

    /* ✅ NEW: Style for the result box to ensure text is visible */
    .result-box {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
        color: #111827 !important;
    }
    .result-box h1, .result-box h2, .result-box h3, .result-box p, .result-box li {
        color: #111827 !important;
    }

    @media (max-width: 768px) {
        .app-title { font-size: 2.5rem !important; }
        .app-subtitle { font-size: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Header -----------------
st.markdown("""
<div class="app-header">
    <h1 class="app-title">📚 StudyPDF</h1>
    <!-- ✅ Centered and widened description -->
    <p class="app-subtitle" style="
        max-width: 700px;
        text-align: center;
        margin: 0 auto;
    ">
        Transform your academic PDFs into interactive learning experiences. 
        Upload, analyze, and get instant answers from textbooks, research papers, and lecture notes.
    </p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "quick_action" not in st.session_state:
    st.session_state.quick_action = None

# ----------------- Main Layout -----------------
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown('<div class="section-header">📤 Upload Document</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">💡 Upload a single academic PDF. For best results, use <b>text-based PDFs</b> rather than scanned documents.</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose your PDF file", type=["pdf"], label_visibility="collapsed")

    st.markdown('<div class="section-header">🎯 Analysis Mode</div>', unsafe_allow_html=True)
    mode = st.selectbox(
        "Select the type of document you're working with:",
        ["Homework / Problem", "Research Paper", "Lecture / Notes", "Flashcards"],
        help="This helps tailor the AI's response style to your needs"
    )

    st.markdown('<div class="section-header">⚡ Quick Actions</div>', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("📋 Summarize", help="Get a structured summary", key="summarize", use_container_width=True):
            st.session_state.quick_action = "Summarize the document, focusing on its key contributions, methods, results, and limitations."
    with col_b:
        if st.button("🎴 Flashcards", help="Generate study flashcards", key="flashcards", use_container_width=True):
            st.session_state.quick_action = "Generate 10 concise Q&A flashcards from this document."
    with col_c:
        if st.button("📝 Quiz Me", help="Create practice questions", key="quiz", use_container_width=True):
            st.session_state.quick_action = "Create a 5-question multiple-choice quiz based on the document, and provide an answer key at the end."

with col2:
    if not uploaded_file:
        st.markdown("""
        <div class="preview-container" style="text-align: center; padding: 3rem;">
            <h3 style="color: #4b5563; margin-bottom: 1rem;">🎯 Ready to analyze your PDF</h3>
            <p style="color: #6b7280; font-size: 1.1rem;">
                Upload a document on the left to get started with intelligent PDF analysis and Q&A.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.spinner("📖 Reading your PDF..."):
            full_text = extract_text_from_pdf(uploaded_file)

        if not full_text.strip():
            st.error("❌ No text found in the PDF. This might be a scanned document that requires OCR processing.")
        else:
            st.markdown('<div class="section-header">📄 Document Viewer</div>', unsafe_allow_html=True)
            uploaded_file.seek(0)
            file_bytes = uploaded_file.read()
            base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" style="border: 1px solid #e5e7eb; border-radius: 12px;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="display:flex; gap:1rem; margin:1rem 0; font-size:0.9rem; color:#6b7280;">
                <span>📊 <b>{len(full_text.split()):,} words</b> extracted for analysis</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="section-header">💬 Ask StudyPDF</div>', unsafe_allow_html=True)
            query = st.text_input(
                "What would you like to know about this document?",
                placeholder="e.g., What are the main findings? Can you explain the methodology?",
                help="Ask specific questions about the content, request summaries, or use the quick actions above"
            )

            user_query = ""
            if st.session_state.quick_action:
                user_query = st.session_state.quick_action
            elif query:
                user_query = query.strip()

            if st.button("🚀 Get Answer", type="primary", use_container_width=True) or (st.session_state.quick_action and user_query):
                if not user_query:
                    st.warning("💭 Please enter a question or use one of the quick actions.")
                else:
                    with st.spinner("🤖 Analyzing document and generating answer..."):
                        prompt = build_academic_prompt(mode, full_text, user_query)
                        try:
                            result = call_groq(prompt)
                            
                            # ✅ UPDATED: This section now uses the new CSS class to ensure visibility.
                            st.markdown('<div class="section-header">✨ Analysis Result</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="result-box">{result}</div>', unsafe_allow_html=True)
                            
                            st.download_button(
                                "💾 Download Answer",
                                data=f"Question: {user_query}\n\nAnswer:\n{result}",
                                file_name=f"studypdf_answer.txt",
                                mime="text/plain",
                                help="Save the answer as a text file"
                            )
                        except Exception as e:
                            st.error(f"❌ Error generating answer: {e}")
                        
                        st.session_state.quick_action = None
                    gc.collect()

st.markdown("""
<div style="text-align:center; margin-top:3rem; padding:2rem; color:#6b7280; font-size:0.875rem;">
    Built for students and researchers • Powered by Groq AI
</div>
""", unsafe_allow_html=True)
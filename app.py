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
        uploaded_file.seek(0)
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        st.error(f"Could not extract text from PDF: {e}")
    return text

def estimate_tokens(text):
    """Rough estimate of tokens in text (1 token ≈ 4 characters for English)."""
    return len(text) // 4

def chunk_text(text, max_tokens=3500):
    """Split text into chunks that fit within token limits."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    max_chars = max_tokens * 4
    
    for word in words:
        word_length = len(word) + 1
        if current_length + word_length > max_chars and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def find_relevant_context(text, query, max_tokens=3500):
    """Find the most relevant sections of text based on the query."""
    import re
    
    query_words = re.findall(r'\b\w+\b', query.lower())
    query_words = [w for w in query_words if len(w) > 3]
    
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    scored_paragraphs = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(para_lower.count(word) for word in query_words)
        if score > 0:
            scored_paragraphs.append((score, para))
    
    scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    max_chars = max_tokens * 4
    
    for score, para in scored_paragraphs:
        if len(context) + len(para) + 2 < max_chars:
            context += para + "\n\n"
        else:
            break
    
    if not context.strip():
        chunks = chunk_text(text, max_tokens)
        context = chunks[0] if chunks else text[:max_chars]
    
    return context.strip()

def progressive_summarize(text_chunks, mode):
    """Summarize large documents by processing chunks and combining results."""
    summaries = []
    
    for i, chunk in enumerate(text_chunks):
        prompt = f"""Summarize this section concisely. Focus on key points.

{chunk}

Summary:"""
        
        try:
            summary = call_groq(prompt)
            summaries.append(f"**Section {i+1}:**\n{summary}")
        except Exception as e:
            summaries.append(f"**Section {i+1}:** Error - {str(e)}")
    
    return "\n\n".join(summaries)

def build_academic_prompt(mode, context, query, is_summary=False):
    """Build optimized prompt using fewer tokens."""
    mode_instructions = {
        "Homework / Problem": "Explain step-by-step. Give clear answers.",
        "Research Paper": "Summarize methods, results, limitations precisely.",
        "Lecture / Notes": "Extract key points. Explain simply with examples.",
        "Flashcards": "Generate short Q&A flashcards."
    }
    
    instruction = mode_instructions.get(mode, "")
    context_note = "\n[Note: Excerpt from larger document]" if is_summary else ""
    
    return f"""You are StudyPDF. {instruction}

Context: {context}{context_note}

Question: {query}

Answer:"""

def call_groq(prompt):
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(str(e))

def process_large_document(full_text, query, mode):
    """Handle large documents intelligently."""
    estimated_tokens = estimate_tokens(full_text)
    
    # If small enough, use full text
    if estimated_tokens <= 3500:
        prompt = build_academic_prompt(mode, full_text, query)
        return call_groq(prompt), False
    
    # For summaries, use progressive approach
    if any(keyword in query.lower() for keyword in ['summarize', 'summary', 'overview', 'flashcard']):
        chunks = chunk_text(full_text, max_tokens=3500)
        if len(chunks) > 5:
            chunks = chunks[:5]
            st.info(f"📄 Processing first 5 sections ({estimated_tokens:,} tokens)")
        
        summary = progressive_summarize(chunks, mode)
        prompt = build_academic_prompt(mode, summary, query, is_summary=True)
        return call_groq(prompt), True
    
    # For specific questions, find relevant context
    else:
        relevant_context = find_relevant_context(full_text, query, max_tokens=3500)
        prompt = build_academic_prompt(mode, relevant_context, query, is_summary=True)
        return call_groq(prompt), True

# ----------------- Page Config -----------------
st.set_page_config(
    page_title="StudyPDF — AI PDF Assistant",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- Modern UI -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Reset & Base */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background: #fafbfc !important;
        color: #1f2937 !important;
    }

    .stApp { 
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
    }
    
    header[data-testid="stHeader"], footer, .stDeployButton, div[data-testid="stToolbar"] { 
        display: none !important; 
    }
    
    section.main > div:first-child { 
        padding-top: 1rem !important; 
    }

    /* Main Container */
    .main-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }

    /* Hero Section */
    .hero {
        text-align: center;
        background: white;
        border-radius: 20px;
        padding: 3rem 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.05);
    }

    .logo {
        width: 70px;
        height: 70px;
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1.5rem auto;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
    }

    .logo-text {
        color: white;
        font-size: 1.75rem;
        font-weight: 700;
    }

    .app-title {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        color: #1f2937 !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: -0.02em;
    }

    .app-subtitle {
        font-size: 1.2rem !important;
        color: #374151 !important;
        font-weight: 500 !important;
        line-height: 1.6;
        max-width: 500px;
        margin: 0 auto;
        text-align: center !important;
    }

    /* Cards */
    .card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        overflow: visible !important;
        position: relative !important;
        z-index: 1 !important;
    }

    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
    }

    .card-title {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: #1f2937 !important;
        margin-bottom: 1.5rem !important;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .card-icon {
        width: 28px;
        height: 28px;
        background: #f3f4f6;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.9rem;
    }

    /* File Upload */
    .stFileUploader {
        background: #374151 !important;
        border: 2px dashed #9ca3af !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        text-align: center !important;
        transition: all 0.3s ease !important;
    }

    .stFileUploader:hover {
        border-color: #60a5fa !important;
        background: #4b5563 !important;
    }

    .stFileUploader label {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    .stFileUploader > div > div > div {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    .stFileUploader small {
        color: #e5e7eb !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }

    /* Fix drag and drop text visibility */
    .stFileUploader div {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    .stFileUploader span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    .stFileUploader p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Specific drag and drop text styling */
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        color: #ffffff !important;
    }

    .stFileUploader [data-testid="stFileUploaderDropzone"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* File uploader instructions text */
    .stFileUploader [data-testid="stFileUploaderInstructions"] {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    .stFileUploader [data-testid="stFileUploaderInstructions"] div {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    .stFileUploader [data-testid="stFileUploaderInstructions"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Additional file uploader text fixes */
    .stFileUploader * {
        color: #ffffff !important;
    }

    .stFileUploader button {
        color: white !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        border: 2px solid #60a5fa !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.3s ease !important;
        min-width: 120px !important;
    }

    .stFileUploader button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        border-color: #93c5fd !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5) !important;
    }

    /* Upload icon styling */
    .stFileUploader svg {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    /* Force all file uploader text to be white */
    .stFileUploader,
    .stFileUploader div,
    .stFileUploader span,
    .stFileUploader p,
    .stFileUploader label,
    .stFileUploader small {
        color: #ffffff !important;
    }

    /* File name styling */
    .stFileUploader div[data-testid="stFileUploaderFileName"] {
        color: #111827 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        background: #f3f4f6 !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
        border: 1px solid #d1d5db !important;
    }

    /* Upload section styling */
    .stFileUploader > div {
        color: #111827 !important;
        font-weight: 600 !important;
    }

    .stFileUploader span {
        color: #111827 !important;
        font-weight: 600 !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important;
        min-height: 44px !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4) !important;
    }

    /* Inputs */
    .stSelectbox {
        z-index: 999 !important;
        position: relative !important;
    }

    .stSelectbox > div > div {
        background: white !important;
        border: 1px solid #d1d5db !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        color: #111827 !important;
        padding: 0.75rem 1rem !important;
        min-height: 60px !important;
        overflow: visible !important;
        line-height: 1.5 !important;
    }

    .stSelectbox > div > div > div {
        color: #111827 !important;
        font-weight: 500 !important;
        line-height: 1.5 !important;
        padding: 0.25rem 0 !important;
    }

    /* Dropdown options */
    .stSelectbox ul {
        background: white !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        z-index: 9999 !important;
        position: relative !important;
    }

    .stSelectbox li {
        color: #111827 !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1rem !important;
    }

    .stSelectbox li:hover {
        background: #f3f4f6 !important;
        color: #111827 !important;
    }

    /* Fix dropdown container overflow */
    div[data-baseweb="select"] {
        z-index: 9999 !important;
        overflow: visible !important;
    }

    ul[role="listbox"] {
        z-index: 9999 !important;
        max-height: 300px !important;
        overflow-y: auto !important;
    }

    /* Card helper text */
    .card p {
        color: #374151 !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
    }

    .stTextInput > div > div > input {
        background: white !important;
        border: 1px solid #d1d5db !important;
        border-radius: 12px !important;
        padding: 0.875rem 1rem !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        color: #111827 !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #6b7280 !important;
        font-weight: 400 !important;
    }

    /* Status */
    .status-bar {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
        flex-wrap: wrap;
    }

    .status-item {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        font-size: 0.85rem;
        font-weight: 500;
        color: #475569;
    }

    .status-success { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
    .status-warning { background: #fffbeb; border-color: #fed7aa; color: #ea580c; }
    .status-info { background: #eff6ff; border-color: #bfdbfe; color: #1d4ed8; }

    /* Info Cards */
    .info-card {
        background: #eff6ff !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
        margin: 1rem 0 !important;
        color: #1e40af !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }

    .warning-card {
        background: #fef3c7 !important;
        border: 1px solid #f59e0b !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
        margin: 1rem 0 !important;
        color: #92400e !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }

    /* Results */
    .result-container {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        margin-top: 1.5rem !important;
        color: #1f2937 !important;
        line-height: 1.7 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04) !important;
    }

    .result-container h1, .result-container h2, .result-container h3 {
        color: #1f2937 !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
    }

    .result-container p, .result-container li {
        color: #374151 !important;
        margin-bottom: 0.75rem !important;
        font-size: 0.95rem !important;
    }

    .result-container strong {
        color: #1f2937 !important;
        font-weight: 600 !important;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .main-container { padding: 1rem 0.5rem; }
        .hero { padding: 2rem 1rem; }
        .app-title { font-size: 2rem !important; }
        .card { padding: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "quick_action" not in st.session_state:
    st.session_state.quick_action = None

# ----------------- Header -----------------
st.markdown("""
<div class="main-container">
    <div class="hero">
        <div class="logo">
            <div class="logo-text">📚</div>
        </div>
        <h1 class="app-title">StudyPDF</h1>
        <p class="app-subtitle">
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- Main Content -----------------
with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Upload Section
    st.markdown("""
    <div class="card">
        <div class="card-title">
            <div class="card-icon">📤</div>
            Upload Document
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose your PDF file", 
        type=["pdf"], 
        help="Upload a text-based PDF for best results"
    )
    
    if uploaded_file:\
        st.markdown("""
        <div class="info-card">
            <strong>✅ Document uploaded successfully!</strong> Ready for analysis.
        </div>
        """, unsafe_allow_html=True)
    
    # Analysis Mode
    st.markdown("""
    <div class="card">
        <div class="card-title">
            <div class="card-icon">🎯</div>
            Analysis Mode
        </div>
        <p style="margin-bottom: 1rem; color: #6b7280; font-size: 0.9rem;">
            Select the type of document you're analyzing to get tailored responses:
        </p>
    """, unsafe_allow_html=True)
    
    mode = st.selectbox(
        "What type of document are you analyzing?",
        ["Homework / Problem", "Research Paper", "Lecture / Notes", "Flashcards"],
        label_visibility="collapsed"
    )
    
    st.markdown("</div>", unsafe_allow_html=True)

    # Quick Actions
    st.markdown("""
    <div class="card">
        <div class="card-title">
            <div class="card-icon">⚡</div>
            Quick Actions
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("📋 Summarize", key="summarize", use_container_width=True):
            st.session_state.quick_action = "Summarize the document, focusing on key contributions, methods, results, and limitations."
    with col_b:
        if st.button("🎴 Flashcards", key="flashcards", use_container_width=True):
            st.session_state.quick_action = "Generate 10 concise Q&A flashcards from this document."
    with col_c:
        if st.button("📝 Quiz Me", key="quiz", use_container_width=True):
            st.session_state.quick_action = "Create a 5-question multiple-choice quiz based on the document."

    # Document Analysis
    if not uploaded_file:
        st.markdown("""
        <div class="card" style="text-align: center; padding: 3rem 2rem !important;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
            <h3 style="color: #1f2937; margin-bottom: 1rem; font-weight: 600;">Ready to analyze your PDF</h3>
            <p style="color: #6b7280; font-size: 1rem;">
                Upload a document above to get started with intelligent analysis.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.spinner("📖 Processing PDF..."):
            full_text = extract_text_from_pdf(uploaded_file)

        if not full_text.strip():
            st.markdown("""
            <div class="warning-card">
                <strong>⚠️ No text found</strong><br>
                This might be a scanned document requiring OCR processing.
            </div>
            """, unsafe_allow_html=True)
        else:
            # Document Info
            estimated_tokens = estimate_tokens(full_text)
            word_count = len(full_text.split())
            
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    <div class="card-icon">📄</div>
                    Document Analysis
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button(
                label="📂 View or Download PDF",
                data=uploaded_file,
                file_name=uploaded_file.name,
                mime="application/pdf",
                use_container_width=True
            )

            # Status indicators
            size_status = "small" if estimated_tokens <= 3000 else "medium" if estimated_tokens <= 5000 else "large"
            status_class = "status-success" if size_status == "small" else "status-info" if size_status == "medium" else "status-warning"
            status_text = "Perfect for analysis" if size_status == "small" else "Good for analysis" if size_status == "medium" else "Smart processing enabled"
            
            st.markdown(f"""
            <div class="status-bar">
                <div class="status-item">📊 {word_count:,} words</div>
                <div class="status-item">🔢 {estimated_tokens:,} tokens</div>
                <div class="status-item {status_class}">✨ {status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if estimated_tokens > 5000:
                st.markdown("""
                <div class="info-card">
                    <strong>💡 Smart Processing</strong><br>
                    Large document detected. Using intelligent section analysis for optimal results.
                </div>
                """, unsafe_allow_html=True)

            # Question Input
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    <div class="card-icon">💬</div>
                    Ask StudyPDF
                </div>
                <p style="margin-bottom: 1rem; color: #6b7280; font-size: 0.9rem;">
                    Ask specific questions about your document or use the quick actions above:
                </p>
            """, unsafe_allow_html=True)
            
            query = st.text_input(
                "What would you like to know?",
                placeholder="e.g., What are the main findings? Explain the methodology...",
                label_visibility="collapsed"
            )
            
            st.markdown("</div>", unsafe_allow_html=True)

            # Get user query from either text input or quick action
            user_query = ""
            if st.session_state.quick_action:
                user_query = st.session_state.quick_action
            elif query and query.strip():
                user_query = query.strip()

            # Add analyze button
            analyze_clicked = st.button("🚀 Analyze Document", type="primary", use_container_width=True)
            
            if analyze_clicked or (st.session_state.quick_action and user_query):
                if not user_query:
                    st.markdown("""
                    <div class="warning-card">
                        💭 <strong>Please enter a question</strong> or use a quick action above.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    with st.spinner("🤖 Analyzing document..."):
                        try:
                            result, was_processed_intelligently = process_large_document(full_text, user_query, mode)
                            
                            st.markdown("""
                            <div class="card">
                                <div class="card-title">
                                    <div class="card-icon">✨</div>
                                    Analysis Result
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if was_processed_intelligently:
                                if any(keyword in user_query.lower() for keyword in ['summarize', 'summary', 'flashcard']):
                                    st.markdown("""
                                    <div class="info-card">
                                        <strong>📑 Comprehensive Analysis</strong><br>
                                        Processed document sections for thorough coverage.
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown("""
                                    <div class="info-card">
                                        <strong>🎯 Targeted Analysis</strong><br>
                                        Found and analyzed relevant sections for your question.
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            st.markdown(f'<div class="result-container">{result}</div>', unsafe_allow_html=True)
                            
                            st.download_button(
                                "💾 Download Answer",
                                data=f"Question: {user_query}\n\nAnswer:\n{result}",
                                file_name="studypdf_answer.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        except Exception as e:
                            error_msg = str(e)
                            if "rate_limit_exceeded" in error_msg or "Request too large" in error_msg:
                                st.markdown("""
                                <div class="warning-card">
                                    <strong>❌ Document too large</strong><br>
                                    Try more specific questions or upload smaller sections.
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div class="warning-card">
                                    <strong>❌ Error:</strong> {error_msg}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        st.session_state.quick_action = None
                    gc.collect()

    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="main-container" style="text-align:center; margin-top:3rem; padding:2rem; color:#9ca3af; font-size:0.85rem;">
    Built for students and researchers • Powered by Groq AI
</div>
""", unsafe_allow_html=True)
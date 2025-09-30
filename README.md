# StudyPDF - AI PDF Assistant

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://studypdf.streamlit.app/)

An intelligent AI-powered PDF analysis tool built with Streamlit and Groq API. Upload your academic documents and get instant answers, summaries, and insights powered by advanced language models.

## 🌟 Live Demo

🚀 **[Try StudyPDF Now](https://studypdf.streamlit.app/)** - Experience the AI PDF assistant in your browser!

## ✨ Features

- **📄 Smart PDF Processing**: Handles large documents with intelligent chunking and context selection
- **🎯 Multiple Analysis Modes**:
  - Homework/Problem Sets
  - Research Papers
  - Lecture Notes
  - Flashcards
- **⚡ Quick Actions**: One-click summarization, quiz generation, and flashcard creation
- **🎨 Modern UI**: Apple-inspired design with dark mode and responsive layout
- **🔒 Secure**: Local processing with API key protection
- **📊 Token Optimization**: Efficient processing for documents up to 200MB

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Groq API Key ([Get one here](https://console.groq.com/))

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/maazin/StudyPDF.git
   cd StudyPDF
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```
   GROQ_API_KEY=your_api_key_here
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

6. **Open your browser** to `http://localhost:8501`

## 📖 Usage

1. **Upload a PDF**: Drag and drop or browse to select your document (up to 200MB)
2. **Select Analysis Mode**: Choose the type of document you're analyzing
3. **Ask Questions**: Type specific questions or use quick actions
4. **Get AI-Powered Responses**: Receive intelligent answers based on your document content

### Quick Actions Available:
- **📋 Summarize**: Get a comprehensive overview of the document
- **🎴 Flashcards**: Generate Q&A flashcards for studying
- **📝 Quiz Me**: Create multiple-choice questions from the content

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **AI Engine**: Groq API (Llama-3.1-8b-instant)
- **PDF Processing**: pdfplumber
- **Styling**: Custom CSS with Inter font
- **Deployment**: Streamlit Cloud

## 📋 Requirements

- streamlit
- groq
- pdfplumber
- python-dotenv
- textwrap3

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Groq](https://groq.com/)
- PDF processing by [pdfplumber](https://github.com/jsvine/pdfplumber)

## 📞 Support

If you have any questions or issues, please open an issue on GitHub or contact the maintainers.

---

**Made with ❤️ for students and researchers worldwide**
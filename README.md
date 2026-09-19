# ⚖️ LegalLens - AI Legal Document Assistant

> **🌐 Live Demo on Google Cloud Run**: **[https://legallens-615970426353.us-central1.run.app](https://legallens-615970426353.us-central1.run.app)**

LegalLens is an AI-powered assistant that helps everyday people understand contracts and legal agreements in plain, simple English.

Upload a contract (`.pdf`, `.docx`, or `.txt`) or click **"Load sample contract"** to instantly analyze it.

---

## ✨ Features

- 📄 **Simplify**: Translates dense legal jargon into a clear, 1-paragraph summary, bullet points, and an easy-to-read jargon glossary.
- ⚠️ **Risk Analysis**: Calculates an overall risk score (0–100), identifies high/medium/low risk clauses, and verifies that quotes are genuine.
- 💬 **Ask Q&A**: Interactive chat grounded strictly in your document text with supporting quotes.
- ⚖️ **Compare Versions**: Compare two drafts of a contract to see differences, missing clauses, and which version favors you.
- 📋 **Action Plan**: Generates a pre-signing checklist, key deadlines, tailored questions to ask a lawyer, and an exportable Word (`.docx`) report.

---

## 🌐 Live Deployment

The application is deployed on **Google Cloud Run**:
- **URL**: [https://legallens-615970426353.us-central1.run.app](https://legallens-615970426353.us-central1.run.app)
- **Infrastructure**: Serverless container on Google Cloud Platform with automatic scaling and session affinity for Streamlit WebSockets.
- **Model Layer**: Powered by Google Gemini (`gemini-3.6-flash` and `gemini-3.5-flash-lite`) with multi-model fallback chains, rate limiting, and circuit breaking.

---

## 🚀 How to Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/Ayushbms05/LegalLens_AI_Legal_Document_Assistant.git
cd LegalLens_AI_Legal_Document_Assistant
```

### 2. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Add your Gemini API Key
Create a `.env` file in the project folder:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Get a free API key from [Google AI Studio](https://aistudio.google.com/))*

### 4. Start the App
```bash
streamlit run app.py
```
Open **http://localhost:8501** in your browser.

---

## 🧪 Running Tests

To verify that all services, security boundaries, and API fallbacks are working properly:
```bash
pytest -v
```

---

## ⚖️ Legal Disclaimer

LegalLens provides general legal **information**, not legal advice. It is designed for educational and review purposes. Always consult a qualified lawyer for specific legal advice.

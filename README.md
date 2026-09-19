# ⚖️ LegalLens - AI Legal Document Assistant

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

## 🌐 How to Deploy to Streamlit Cloud (Free & Easy)

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and connect your GitHub account.
2. Select your repository: `Ayushbms05/LegalLens_AI_Legal_Document_Assistant`.
3. Set the Main file path to: `app.py`.
4. Click **Advanced Settings** $\rightarrow$ **Secrets**, and paste:
   ```toml
   GEMINI_API_KEY = "your_actual_gemini_api_key_here"
   GEMINI_MODEL_CHAIN_HEAVY = "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-flash-lite-latest"
   GEMINI_MODEL_CHAIN_LIGHT = "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.6-flash,gemini-flash-lite-latest"
   ```
5. Click **Deploy**! Your app will be live with a public URL in less than 2 minutes.

---

## 🧪 Running Tests

To verify that all services and API fallbacks are working properly:
```bash
pytest -v
```

---

## ⚖️ Legal Disclaimer

LegalLens provides general legal **information**, not legal advice. It is designed for educational and review purposes. Always consult a qualified lawyer for specific legal advice.

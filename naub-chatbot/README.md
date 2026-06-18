# 🎓 NAUB Enquiry Chatbot

> **AI-Powered Student Enquiry Assistant for Nigerian Army University Biu**

An intelligent, web-based chatbot that provides instant, accurate answers to student enquiries 24/7 — no human intervention required. Built with Python, Flask, and a custom TF-IDF + Cosine Similarity NLP engine.

---

## 📸 Features

- 🤖 **AI-Powered NLP Engine** — Custom TF-IDF vectorization + Cosine Similarity algorithm
- 💬 **Rich Chat Interface** — Animated, mobile-friendly UI with markdown rendering
- 🧠 **25+ Trained Intents** — Covers admissions, fees, programmes, hostel, calendar, contacts, and more
- 📊 **Admin Dashboard** — Manage the knowledge base, view conversation logs, and monitor analytics
- 🔄 **Live Retraining** — Add/delete intents and the AI engine retrains instantly
- 📱 **Fully Responsive** — Works beautifully on mobile, tablet, and desktop
- 🔒 **Privacy First** — All conversations are anonymized; no PII stored
- ⚡ **Fast** — Responds in under 2 seconds

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Onyedika1801/Enquiry-Chatbot-NAUB.git
cd Enquiry-Chatbot-NAUB

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# OR
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

Open your browser and navigate to: **http://localhost:5000**

Admin dashboard: **http://localhost:5000/admin**

---

## 🏗️ Project Structure

```
naub-chatbot/
├── run.py                     # Application entry point
├── requirements.txt           # Python dependencies
├── README.md
│
├── app/
│   ├── __init__.py            # Flask app, NLP engine, routes, database
│   │
│   ├── templates/
│   │   ├── index.html         # Main chat interface
│   │   └── admin.html         # Admin dashboard
│   │
│   └── static/
│       ├── css/               # (Optional additional styles)
│       └── js/                # (Optional additional scripts)
│
├── data/
│   └── knowledge_base.json    # NAUB FAQ dataset (25+ intents)
│
└── instance/
    └── naub_chatbot.db        # SQLite database (auto-created)
```

---

## 🧠 How the AI Works

The chatbot uses a **pure Python TF-IDF + Cosine Similarity** pipeline:

```
User Query
    │
    ▼
Text Preprocessing
(lowercase → tokenize → remove stopwords)
    │
    ▼
TF-IDF Vectorization
(convert query to weighted numerical vector)
    │
    ▼
Cosine Similarity
(compare query vector against all stored intent vectors)
    │
    ▼
Best Match (≥ 0.15 threshold)
    │
    ├─── YES → Return stored response
    └─── NO  → Fallback message + contact info
```

**No external AI API required** — runs entirely on your own server.

---

## 📚 Knowledge Base Topics

| Topic | Coverage |
|-------|----------|
| Admissions | JAMB cut-off, Post-UTME, admission list, process |
| School Fees | Fresh/returning student fees, payment methods |
| Programmes | All faculties, undergraduate & postgraduate courses |
| Hostel | Availability, fees, allocation procedure |
| Academic Calendar | Resumption, semesters, exam periods |
| Course Registration | Process, deadlines, course forms |
| GST Courses | Compulsory courses, course codes |
| Change of Course | Eligibility, process, requirements |
| Results | How to check, result query, CGPA grading |
| Locations | Campus address, building locations, directions |
| Contacts | Admissions, Registry, Bursary, ICT, Student Affairs |
| Scholarships | Federal, state, PTDF, NDDC scholarships |
| NYSC | Post-graduation service process |
| Transcripts | Request process, fees, timeline |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3, Flask |
| **NLP Engine** | Custom TF-IDF + Cosine Similarity (stdlib + math) |
| **Database** | SQLite (dev) / PostgreSQL (production) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Fonts** | Space Grotesk (display), Inter (body) |
| **Icons** | Font Awesome 6 |
| **Deployment** | Gunicorn + any WSGI server |

---

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message and get a bot response |
| `GET`  | `/api/stats` | Get chatbot usage statistics |
| `GET`  | `/api/admin/knowledge` | List all trained intents |
| `POST` | `/api/admin/knowledge` | Add a new intent (auto-retrains) |
| `DELETE` | `/api/admin/knowledge/<intent>` | Delete an intent (auto-retrains) |
| `GET`  | `/api/admin/logs` | Get last 100 conversation logs |

---

## 🌐 Production Deployment

```bash
# Set environment variables
export SECRET_KEY="your-secure-secret-key-here"
export FLASK_ENV="production"

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

For production, configure:
- A reverse proxy (Nginx or Apache)
- SSL certificate (Let's Encrypt)
- PostgreSQL instead of SQLite
- A process manager (systemd or supervisor)

---

## 📖 Expanding the Knowledge Base

**Via the Admin Dashboard:**
1. Visit `/admin`
2. Click **"Add Intent"** in the sidebar
3. Fill in the intent name, sample questions, and response
4. Click **"Save & Retrain Engine"** — done!

**Via the JSON file directly:**
Edit `data/knowledge_base.json` and add a new object:
```json
{
  "intent": "your_intent_name",
  "questions": [
    "Sample question 1?",
    "Another way to ask it?",
    "Yet another variation"
  ],
  "response": "Your formatted response with **markdown** support."
}
```
Then restart the application (or hit `/api/admin/knowledge` POST endpoint).

---

## 👨‍💻 Development

```bash
# Run in debug mode
FLASK_DEBUG=1 python run.py

# The app auto-reloads on file changes
```

---

## 📄 License

This project was developed as an academic final-year project for **Nigerian Army University Biu (NAUB)**.

---

## 🙏 Acknowledgements

- Nigerian Army University Biu (NAUB) — for the institutional context
- The NLP research community for TF-IDF and Cosine Similarity techniques
- Flask and scikit-learn open-source communities

---

*Built with ❤️ for the students of Nigerian Army University Biu*

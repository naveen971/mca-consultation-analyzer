# eConsultation Sentiment Analysis System

AI-powered analysis of stakeholder comments from India's Ministry of Corporate Affairs (MCA) eConsultation portal.

## Features

- **Sentiment Classification** — Classify comments as Positive, Negative, or Neutral using Google Gemini AI
- **Smart Summarization** — Generate per-comment and executive summaries
- **Word Cloud Visualization** — TF-IDF weighted word clouds with per-sentiment views
- **File Upload** — Drag-and-drop CSV/Excel with auto-column detection
- **Interactive Dashboard** — Charts, searchable tables, keyword analysis

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI + Uvicorn |
| AI Engine | Google Gemini 1.5 Flash |
| Frontend | HTML + CSS + Vanilla JavaScript |
| Charts | Chart.js |
| NLP | NLTK, scikit-learn (TF-IDF) |
| Word Cloud | Python wordcloud + matplotlib |
| File Handling | pandas (CSV/Excel) |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Download NLTK Data

```bash
python -m nltk.downloader stopwords punkt punkt_tab wordnet
```

### 3. Configure API Key

Edit `.env` and add your Google Gemini API key:

```
GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Run the Server

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open the App

Navigate to [http://localhost:8000](http://localhost:8000)

### 6. Test with Sample Data

Upload `sample_data/sample_comments.csv` to test the full pipeline.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload CSV/Excel file |
| POST | `/api/sentiment/single` | Analyze one comment |
| POST | `/api/sentiment/batch` | Analyze multiple comments |
| POST | `/api/summary/single` | Summarize one comment |
| POST | `/api/summary/batch` | Summarize multiple + executive summary |
| POST | `/api/wordcloud/generate` | Generate word cloud |
| POST | `/api/wordcloud/by-sentiment` | Per-sentiment word clouds |

## Project Structure

```
econsultation-sentiment/
├── backend/
│   ├── models/schemas.py          # Pydantic data models
│   ├── routes/                    # API endpoint handlers
│   │   ├── sentiment.py
│   │   ├── summary.py
│   │   └── wordcloud.py
│   ├── services/                  # Business logic
│   │   ├── sentiment_service.py
│   │   ├── summary_service.py
│   │   └── wordcloud_service.py
│   ├── utils/                     # Utilities
│   │   ├── preprocessor.py
│   │   └── file_handler.py
│   ├── main.py                    # FastAPI app entry
│   └── requirements.txt
├── frontend/
│   ├── index.html                 # Landing page
│   ├── upload.html                # File upload
│   ├── results.html               # Dashboard
│   └── assets/
│       ├── css/style.css
│       └── js/
│           ├── upload.js
│           ├── dashboard.js
│           └── wordcloud.js
├── sample_data/
│   └── sample_comments.csv
├── .env
└── README.md
```

## License

MIT

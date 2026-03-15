# 🛡️ Video Analysis and Summary System (The Defender)

A full-stack, Flask-based application built to analyze YouTube videos and local video file uploads. The system extracts structured chapters, subtitles, audio transcripts, extracts visual text natively via OCR, and produces AI summaries.

---

## 🚀 Features

* **Multi-Format Support:** Provide a YouTube link or directly upload local video files for processing.
* **YouTube Metadata & Chapters:** Direct extraction of structured chapters and metadata from YouTube descriptions.
* **Caption Extraction:** Automatically downloads available subtitles to generate timestamps.
* **Audio-to-Text Fallback:** When captions are unavailable, dynamically extracts audio using `yt-dlp` and `ffmpeg`, and converts it to text using the **Deepgram API**.
* **Visual OCR Scans:** State-of-the-art **EasyOCR** and **OpenCV** pipeline that scans video frames periodically to extract texts visible on the screen itself.
* **AI-Powered Topics & Summaries:** Uses the **Groq API** (running bleeding-edge models like LLaMA 3 70B and Mixtral) to structure raw transcripts into intelligent, Hinglish chapters and on-demand summaries.
* **Persistent Storage:** Requests, usage stats, and past processed transcripts are stored securely onto **MongoDB Atlas**.
* **Sleek UI/UX:** Clean, dynamically updated Frontend featuring live progress tracking via chunked status polling.

---

## 📂 Project Structure

```text
The-Defender/
├── .env                  # Environment variables (API Keys, MongoDB URI)
├── .gitignore            # Files ignored by Git
├── app.py                # Main Flask Backend Logic (Routes, ML pipelines, API)
├── requirements.txt      # Python dependencies and libraries
├── static/               # Publicly served static assets
│   ├── css/              # Stylesheets
│   ├── js/               # Frontend logic and API integration files
│   └── thumbnails/       # Auto-generated video thumbnails and image previews
├── templates/            
│   └── index.html        # Main front-facing UI
└── uploads/              # Temporary folder to safely process files locally
```

---

## 🛠 Prerequisites & Requirements

Ensure that you have the following system tools configured before starting:

1. **Python 3.8+** (`python --version`)
2. **FFmpeg** (Required for audio/video conversion and extraction)
   * **Windows:** `winget install ffmpeg` _(or download via the official website)_
   * **Linux:** `sudo apt update && sudo apt install ffmpeg`
   * **MacOS:** `brew install ffmpeg`
3. **yt-dlp** (For fetching media content)
   * Can be installed system-wide: `pip install yt-dlp`

---

## 📦 How to Clone and Setup

### 1. Clone the Repository
Open your preferred terminal / command line and run:

```bash
git clone https://github.com/tech-ninja-108/The-Defender.git
cd The-Defender
```

### 2. Configure a Virtual Environment (Recommended)
This keeps the project's dependencies isolated:

**Windows Command Prompt:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / MacOS / Git Bash:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies
The `requirements.txt` file holds all necessary libraries (Flask, EasyOCR, Groq, PyMongo, etc.). Install them via:

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a file named `.env` in the root directory and define the following variables:

```env
MONGO_URI=your_mongodb_atlas_connection_string
GROQ_API_KEY=your_groq_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
```
*(Note: If these are already set via your hosting provider, you may skip this step.)*

---

## 🚦 Running the Application

Once your setup is correct, launch the application:

```bash
python app.py
```

Wait for the "✅ OCR Model Ready" message inside your console output.
Open your browser and visit:

👉 **http://localhost:3000**

---

## ⚡ Important Notes
* **First-run Delay (EasyOCR):** The EasyOCR engine downloads its neural net models dynamically during the very first run, meaning the first OCR request may take significantly longer.
* **Storage limits:** Files stored in `uploads/` and `static/thumbnails/` are automatically flushed before new analyses run in order to save disk space.

---

## 👨‍💻 Core Tech Stack

* **Backend Framework:** Flask structure with Python
* **Database:** MongoDB Atlas (NoSQL)
* **Computer Vision:** EasyOCR, Python-OpenCV (`cv2`)
* **AI & LLM Services:** Groq Cloud API, Deepgram API
* **CLI Extractor:** `yt-dlp`, `FFmpeg`
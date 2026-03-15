Video Analysis and Summary System

A Flask-based application for analyzing YouTube videos and local video files. It extracts subtitles, audio transcripts, screen text (OCR), chapters, and generates AI summaries.

---

🚀 Features

- Fetch YouTube video chapters
- Extract subtitles / captions
- Convert audio to text using Deepgram
- OCR text extraction using EasyOCR
- Generate AI summaries using Groq
- Store transcript queries and stats in MongoDB Atlas

---

🛠 Prerequisites

Install the following before running the project:

Python 3.8+

python --version

FFmpeg

Windows

winget install ffmpeg

Linux

sudo apt update
sudo apt install ffmpeg

Mac

brew install ffmpeg

Check installation:

ffmpeg -version

yt-dlp

pip install yt-dlp

Check:

yt-dlp --version

---

📦 Installation

Clone repository:

git clone https://github.com/tech-ninja-108/The-Defender
cd The-Defender

Create virtual environment:

Windows

python -m venv venv
venv\Scripts\activate

Linux / Mac

python3 -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

---

🔐 Environment Variables

Environment variables are already configured in the project.

---

🚦 Run Project

python app.py

Open in browser:

http://localhost:3000

---

⚡ Note

EasyOCR downloads model files automatically on first run, so the first OCR request may take extra time.

---

👨‍💻 Tech Stack

- Flask
- MongoDB Atlas
- EasyOCR
- Deepgram API
- Groq API
- yt-dlp
- FFmpeg
# Video Analysis and Summary System

This project is a Flask-based application that analyzes YouTube videos and local video files. It can extract topics, chapters, screen texts (OCR), and audio transcripts using AI (Groq), Deepgram, EasyOCR, and the YouTube Transcript API. 

## 🚀 Features
- **Fetch video chapters** from YouTube metadata
- **Extract sub-titles/captions** from YouTube videos
- **Audio to Text conversion** using Deepgram for offline videos or when captions are missing
- **OCR Engine** using EasyOCR to extract texts explicitly from video frames
- **AI Summary** generated via Groq (Llama3/Mixtral models)
- **MongoDB** integration for saving transcript queries and API hit statistics

## 🛠 Prerequisites

Before running this application, make sure you have the following system-level tools installed:
1. **Python 3.8+**
2. **FFmpeg** (Required for audio processing)
   - *Windows:* Download from https://ffmpeg.org/ or use `winget install ffmpeg`
   - *Mac:* `brew install ffmpeg`
   - *Linux:* `sudo apt install ffmpeg`
3. **yt-dlp** (Command line video downloader)
   - *Global Install:* `pip install yt-dlp` or `sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp`
4. **MongoDB**
   - You can install it locally on your system (`127.0.0.1:27017`) OR setup a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).

## 📦 Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <your-repo-link>
   cd <repository-folder>
   ```

2. **Create a Virtual Environment (Optional but recommended):**
   ```bash
   python -m venv venv
   # Activate it:
   # On Windows: venv\Scripts\activate
   # On Mac/Linux: source venv/bin/activate
   ```

3. **Install the required Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables (.env)**
   Create a `.env` file in the root directory (same folder as `app.py`) and add your API credentials:
   ```ini
   GROQ_API_KEY=your_groq_api_key_here
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   MONGO_URI=mongodb://127.0.0.1:27017/  # Or your MongoDB Atlas URL
   ```

## 🚦 Running the Application

Once everything is set up, start the server:

```bash
python app.py
```

The app will run at `http://localhost:3000`. You can test it by uploading a video or providing a YouTube link via the web interface.

> Note: The first time you run an OCR request, EasyOCR will automatically download its model weights for English/Hindi.

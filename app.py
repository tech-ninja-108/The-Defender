import os
import re
import time
import json
import subprocess
import cv2
import easyocr
import requests as req
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from groq import Groq
from werkzeug.utils import secure_filename
from youtube_transcript_api import YouTubeTranscriptApi

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

UPLOAD_FOLDER = 'uploads'
THUMBNAIL_FOLDER = 'static/thumbnails'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

# 🚀 GLOBAL STATUS TRACKER
PROCESS_STATUS = {}

try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client['videoSearch']
    Transcript = db['transcripts']
    Stats = db['stats'] # Collection for request counts
except Exception as e:
    print("❌ MongoDB Error:", e)

# Keys setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

print("⏳ Loading OCR Model...")
# GPU mode ON rakha hai, agar system me GPU hai to bahut fast chalega, warna CPU use karega
ocr_reader = easyocr.Reader(['en', 'hi'], gpu=True)
print("✅ OCR Model Ready")

def generate_with_fallback(prompt):
    models_to_try = ['llama-3.3-70b-versatile', 'llama3-70b-8192', 'mixtral-8x7b-32768']
    last_error = None
    
    for model_name in models_to_try:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=0.3, # Keep JSON formatting strict
            )
            return res.choices[0].message.content
        except Exception as e:
            print(f"Groq {model_name} failed: {e}")
            last_error = e
            continue
            
    raise Exception(f"All Groq models failed. Last error: {last_error}")

def extract_video_id(url):
    match = re.search(r'^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*', url)
    return match.group(2) if match and len(match.group(2)) == 11 else None

def get_yt_metadata(url):
    try:
        result = subprocess.run(['yt-dlp', '--dump-json', url], capture_output=True, text=True)
        if result.returncode == 0: return json.loads(result.stdout)
        return None
    except: return None

def generate_ai_chapters(transcript_text, default_thumb, video_id_v, is_local_video=False):
    prompt = (
        "You are an expert content structurer. I am providing you with a video transcript that includes timestamps in seconds. "
        "Please group the content into logical topics/chapters (around 5 to 10 chapters depending on length). "
        "Return ONLY a valid JSON array of objects, with no markdown formatting. "
        "Each object must have exactly two keys:\n"
        "- 'topicTitle': A short, descriptive title for the chapter in Hinglish/Hindi or English (max 60 chars)\n"
        "- 'startTime': The integer start time in seconds where this topic begins.\n"
        "Transcript:\n" + transcript_text
    )
    raw_text = generate_with_fallback(prompt).strip()
    if raw_text.startswith("```json"): raw_text = raw_text[7:-3].strip()
    elif raw_text.startswith("```"): raw_text = raw_text[3:-3].strip()
    
    ai_topics = json.loads(raw_text)
    final_data = []
    for topic in ai_topics:
        st = int(topic.get('startTime', 0))
        title = topic.get('topicTitle', 'Topic')
        final_data.append({
            "topicTitle": title, "startTime": st,
            "thumbnail": default_thumb, "previousContext": f"Chapter: {title}",
            "playLink": "#" if is_local_video else f"https://youtu.be/{video_id_v}?t={st}"
        })
        
    # Generate an overall AI title for the video based on the topics
    main_title = "Video Analysis"
    try:
        title_prompt = "Generate a short, catchy main title (max 50 chars) in Hinglish based on these chapters: " + str([t['topicTitle'] for t in final_data])
        title_res_text = generate_with_fallback(title_prompt)
        if title_res_text: main_title = title_res_text.strip().replace('"', '')
    except: pass
        
    return final_data, main_title

# 🚀 REAL-TIME DOWNLOAD TRACKER
def download_with_progress(url, path, task_id):
    PROCESS_STATUS[task_id] = {"status": "Starting Download...", "percent": 0, "details": "Connecting to YouTube..."}
    cmd = ['yt-dlp', '-N', '4', '--newline', '-f', 'bestvideo[height<=480][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', '--merge-output-format', 'mp4', '-o', path, url]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for line in process.stdout:
        if "[download]" in line and "%" in line:
            try:
                pct_match = re.search(r'([\d\.]+)%', line)
                if pct_match:
                    pct = float(pct_match.group(1))
                    PROCESS_STATUS[task_id]["percent"] = pct
                    PROCESS_STATUS[task_id]["details"] = line.replace("[download]", "").strip()
            except: pass
    process.wait()

# 🚀 OCR ENGINE (Max 10 Mins, Every 4 Sec)
def run_ocr_engine(video_path, video_id_str, task_id):
    PROCESS_STATUS[task_id] = {"status": "Extracting Visuals & OCR", "percent": 0, "details": "Initializing OpenCV..."}
    cap = cv2.VideoCapture(video_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    if fps <= 0: fps = 30
    interval_sec = 10 # Har 10 second me ek frame (Time bachaane ke liye 4 se 10 kar diya)
    max_seconds = 600 # 10 Minutes limit
    
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration_sec = total_frames / fps if total_frames > 0 else 0
    if duration_sec <= 0 or duration_sec > max_seconds:
        duration_sec = max_seconds
        
    results = []
    main_thumb_url = ""

    current_sec = 0
    while cap.isOpened() and current_sec <= duration_sec:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_sec * 1000)
        ret, frame = cap.read()
        if not ret: break
        
        if current_sec == 0:
            t_name = f"main_thumb_{video_id_str}.jpg"
            thumb_path = os.path.join(THUMBNAIL_FOLDER, t_name)
            small_frame = cv2.resize(frame, (800, 450))
            cv2.imwrite(thumb_path, small_frame)
            main_thumb_url = f"http://localhost:3000/static/thumbnails/{t_name}"

        small_frame = cv2.resize(frame, (800, 450))
        
        txt_list = ocr_reader.readtext(small_frame, detail=0)
        screen_text = " ".join(txt_list)
        
        if len(screen_text.strip()) > 5:
            results.append({
                "topicTitle": screen_text[:45] + "...",
                "startTime": current_sec,
                "thumbnail": main_thumb_url,
                "previousContext": screen_text,
            })
        
        pct = min(100, int((current_sec / duration_sec) * 100))
        PROCESS_STATUS[task_id]["percent"] = pct
        PROCESS_STATUS[task_id]["status"] = "Running AI OCR Scan"
        PROCESS_STATUS[task_id]["details"] = f"Scanned {current_sec}s / {int(duration_sec)}s (Max 10 Mins limit)"
            
        current_sec += interval_sec

    cap.release()
    return results, main_thumb_url

def cleanup_old_data():
    try:
        for folder in [UPLOAD_FOLDER, THUMBNAIL_FOLDER]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) and not filename.startswith('.'):
                    os.remove(file_path)
        PROCESS_STATUS.clear()
    except Exception as e:
        print("Cleanup error:", e)

# ==========================================
# ROUTES
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    return jsonify(PROCESS_STATUS.get(task_id, {"status": "Waiting...", "percent": 0, "details": ""}))

@app.route('/api/video/analyze', methods=['POST'])
def analyze_video():
    cleanup_old_data()
    
    # Track the request count
    try:
        Stats.update_one({"_id": "api_stats"}, {"$inc": {"total_requests": 1}}, upsert=True)
    except Exception as e:
        print("Failed to update stats:", e)

    mode = request.form.get('mode', 'normal') 
    video_url = request.form.get('videoUrl')
    task_id = request.form.get('taskId') 
    if not task_id:
        task_id = str(int(time.time()))
        
    video_id_v = extract_video_id(video_url) if video_url else str(int(time.time()))
    default_thumb = f"https://img.youtube.com/vi/{video_id_v}/hqdefault.jpg" if video_url else ""

    PROCESS_STATUS[task_id] = {"status": "Initializing...", "percent": 0, "details": "Checking priorities..."}
    
    # Check if local video was uploaded first
    v_path = ""
    is_local_video = False
    if 'videoFile' in request.files and request.files['videoFile'].filename != '':
        video_file = request.files['videoFile']
        v_path = os.path.join(UPLOAD_FOLDER, secure_filename(video_file.filename))
        video_file.save(v_path)
        is_local_video = True
        
    audio_needed = False

    # TIER 1: YouTube Description / Chapters
    if video_url and not is_local_video and mode != 'ocr':
        PROCESS_STATUS[task_id] = {"status": "Checking Meta", "percent": 15, "details": "Searching video descriptions..."}
        meta = get_yt_metadata(video_url)
        if meta:
            chapters = []
            if 'chapters' in meta and meta['chapters']:
                for ch in meta['chapters']:
                    start_sec = int(ch['start_time'])
                    chapters.append({
                        "topicTitle": ch['title'], "startTime": start_sec, "thumbnail": default_thumb, 
                        "previousContext": f"Chapter Name: {ch['title']}", "playLink": f"https://youtu.be/{video_id_v}?t={start_sec}"
                    })
            elif 'description' in meta and meta['description']:
                # Manually parse description for timestamps (e.g. 00:00 - Intro or 1:05:22 Conclusion)
                desc_lines = meta['description'].split('\n')
                for line in desc_lines:
                    match = re.search(r'^(?:\[)?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\])?\s*[-|:]?\s*(.+)', line.strip())
                    if match:
                        hours = int(match.group(1)) if match.group(1) else 0
                        mins = int(match.group(2))
                        secs = int(match.group(3))
                        title = match.group(4).strip()
                        start_sec = (hours * 3600) + (mins * 60) + secs
                        
                        # Avoid duplicate tiny chapters or overly long titles
                        if len(title) > 2 and len(title) < 100:
                            chapters.append({
                                "topicTitle": title, "startTime": start_sec, "thumbnail": default_thumb, 
                                "previousContext": f"Parsed from Description: {title}", "playLink": f"https://youtu.be/{video_id_v}?t={start_sec}"
                            })
                            
            if len(chapters) > 0:
                PROCESS_STATUS[task_id] = {"status": "Complete", "percent": 100, "details": "Chapters found from description!"}
                
                # Fetch a smart title using AI for these chapters
                main_title = meta.get('title', 'YouTube Video')
                try:
                    title_prompt = "Generate a short, catchy main title (max 50 chars) in Hinglish based on these chapters: " + str([t['topicTitle'] for t in chapters])
                    title_res_text = generate_with_fallback(title_prompt)
                    if title_res_text: main_title = title_res_text.strip().replace('"', '')
                except: pass
                    
                # Save to MongoDB
                try:
                    Transcript.insert_many([{"task_id": task_id, "mainTitle": main_title, **ch} for ch in chapters])
                except Exception as e:
                    print("Failed to save to MongoDB:", e)

                return jsonify({"success": True, "source": "YouTube Chapters", "mainTitle": main_title, "results": chapters}), 200

    # TIER 2: YouTube Captions (If no chapters in description)
    if video_url and not is_local_video and mode != 'ocr':
        PROCESS_STATUS[task_id] = {"status": "Checking Captions", "percent": 25, "details": "Searching for subtitles..."}
        transcript_with_time = ""
        try:
            ytt_api = YouTubeTranscriptApi()
            t_list = ytt_api.list(video_id_v)
            transcript = t_list.find_transcript(['en', 'hi', 'hi-IN'])
            fetched_data = transcript.fetch()
            
            current_chunk_start = 0
            chunk_text = ""
            for item in fetched_data:
                w_start = int(item.start)
                if w_start - current_chunk_start >= 15:
                    transcript_with_time += f"[{current_chunk_start}s] {chunk_text}\n"
                    current_chunk_start = w_start
                    chunk_text = ""
                chunk_text += item.text + " "
            if chunk_text:
                transcript_with_time += f"[{current_chunk_start}s] {chunk_text}\n"
        except Exception as e:
            print("Captions not found:", e)
            audio_needed = True

        if transcript_with_time:
            PROCESS_STATUS[task_id] = {"status": "Running AI processing", "percent": 50, "details": "Captions found! Creating topics with AI..."}
            try:
                final_data, main_title = generate_ai_chapters(transcript_with_time, default_thumb, video_id_v, is_local_video=is_local_video)
                if final_data:
                    PROCESS_STATUS[task_id] = {"status": "Complete", "percent": 100, "details": "Topics generated from captions!"}
                    
                    # Save to MongoDB
                    try:
                        Transcript.insert_many([{"task_id": task_id, "mainTitle": main_title, **topic} for topic in final_data])
                    except Exception as e:
                        print("Failed to save to MongoDB:", e)

                    return jsonify({"success": True, "source": "YouTube Captions", "mainTitle": main_title, "results": final_data}), 200
            except Exception as e:
                print("Gemini processing failed on captions:", e)
                audio_needed = True
    
    # If no URL given, but local video uploaded and mode isn't manual OCR, try audio STT automatically
    if is_local_video and mode != 'ocr':
        audio_needed = True
        
    # TIER 3: Audio STT Fallback (No Chapters & No Captions found OR Local Video)
    if audio_needed:
        PROCESS_STATUS[task_id] = {"status": "Audio Fallback", "percent": 35, "details": "Extracting audio (Max 30 mins)..."}
        a_path = os.path.join(UPLOAD_FOLDER, f"a_{task_id}.mp3")
        
        if is_local_video:
            # Generate a local thumbnail
            t_name = f"main_thumb_{task_id}.jpg"
            thumb_path = os.path.join(THUMBNAIL_FOLDER, t_name)
            cap = cv2.VideoCapture(v_path)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(thumb_path, cv2.resize(frame, (800, 450)))
                default_thumb = f"http://localhost:3000/{THUMBNAIL_FOLDER}/{t_name}"
            cap.release()

            # Extract audio from local video using ffmpeg (max 30 mins: -t 1800)
            subprocess.run(['ffmpeg', '-y', '-i', v_path, '-t', '1800', '-b:a', '32k', '-ac', '1', '-map', 'a', a_path], capture_output=True)
        else:
            # yt-dlp download audio (max 30 mins: --download-sections "*00:00:00-00:30:00")
            subprocess.run(['yt-dlp', '-N', '4', '-x', '--audio-format', 'mp3', '--audio-quality', '7', '--download-sections', '*00:00:00-00:30:00', '-o', a_path, video_url])
        
        if os.path.exists(a_path):
            PROCESS_STATUS[task_id] = {"status": "Running AI Speech", "percent": 60, "details": "Converting speech to text..."}
            with open(a_path, 'rb') as audio_file:
                headers = {'Authorization': f'Token {DEEPGRAM_API_KEY}', 'Content-Type': 'audio/mp3'}
                url_dg = 'https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&language=hi&punctuate=true'
                response = req.post(url_dg, headers=headers, data=audio_file)
            os.remove(a_path)
            
            res_json = response.json()
            if 'results' in res_json:
                PROCESS_STATUS[task_id] = {"status": "Finalizing", "percent": 90, "details": "Creating topics from speech with AI..."}
                words = res_json['results']['channels'][0]['alternatives'][0]['words']
                
                transcript_with_time = ""
                current_chunk_start = 0
                chunk_text = ""
                for w in words:
                    w_start = int(w['start'])
                    if w_start - current_chunk_start >= 15:
                        transcript_with_time += f"[{current_chunk_start}s] {chunk_text}\n"
                        current_chunk_start = w_start
                        chunk_text = ""
                    chunk_text += w.get('punctuated_word', w.get('word', '')) + " "
                if chunk_text:
                    transcript_with_time += f"[{current_chunk_start}s] {chunk_text}\n"
                
                final_data, main_title = [], "Analyzed Video"
                try:
                    final_data, main_title = generate_ai_chapters(transcript_with_time, default_thumb, video_id_v, is_local_video=is_local_video)
                except Exception as e:
                    print("AI fallback failed:", e)
                    
                if not final_data:
                    main_title = "Local Video Processing"
                    if not words:
                        final_data.append({
                            "topicTitle": "Audio Unrecognized", "startTime": 0,
                            "thumbnail": default_thumb, "previousContext": "No speech detected",
                            "playLink": f"https://youtu.be/{video_id_v}?t=0"
                        })
                    else:
                        temp_text, start_time = "", words[0]['start']
                        for i, w in enumerate(words):
                            temp_text += w.get('punctuated_word', w.get('word', '')) + " "
                            if (i + 1) % 20 == 0 or i == len(words) - 1:
                                final_data.append({
                                    "topicTitle": temp_text.strip()[:60] + "...", "startTime": int(start_time),
                                    "thumbnail": default_thumb, "previousContext": temp_text.strip(),
                                    "playLink": "#" if is_local_video else f"https://youtu.be/{video_id_v}?t={int(start_time)}"
                                })
                                temp_text = ""
                                if i + 1 < len(words): start_time = words[i + 1]['start']
                
                PROCESS_STATUS[task_id] = {"status": "Complete", "percent": 100, "details": "Audio transcribed successfully!"}
                
                # Save to MongoDB
                try:
                    if final_data:
                        Transcript.insert_many([{"task_id": task_id, "mainTitle": main_title, **data} for data in final_data])
                except Exception as e:
                    print("Failed to save to MongoDB:", e)

                return jsonify({"success": True, "source": "Audio Transcript", "mainTitle": main_title, "results": final_data}), 200

    # TIER 4: OCR Mode (Forced via UI or Local File overrides above tiers)
    if not is_local_video and mode == 'ocr':
        v_path = os.path.join(UPLOAD_FOLDER, f"v_{task_id}.mp4")
        if video_url: download_with_progress(video_url, v_path, task_id)

    if mode == 'ocr' and os.path.exists(v_path):
        ocr_results, main_thumb_url = run_ocr_engine(v_path, video_id_v, task_id)
        os.remove(v_path) 
        
        if not ocr_results:
            ocr_results = [{
                "topicTitle": "Video Processed (No Text)",
                "startTime": 0,
                "thumbnail": main_thumb_url or default_thumb,
                "previousContext": "System scanned visuals but found no text.",
                "playLink": f"https://youtu.be/{video_id_v}?t=0" if video_url else "#"
            }]

        for r in ocr_results:
            r['playLink'] = f"https://youtu.be/{video_id_v}?t={r['startTime']}" if video_url else "#"

        # Generate AI title based on OCR results
        main_title = "OCR Extracted Video"
        try:
            title_prompt = "Generate a short, catchy main title (max 50 chars) in Hinglish based on these text snippets read from a video screen: " + str([t['topicTitle'] for t in ocr_results])
            title_res_text = generate_with_fallback(title_prompt)
            if title_res_text: main_title = title_res_text.strip().replace('"', '')
        except: pass

        PROCESS_STATUS[task_id] = {"status": "Complete", "percent": 100, "details": "Analysis Finished!"}
        
        # Save to MongoDB
        try:
            if ocr_results:
                Transcript.insert_many([{"task_id": task_id, "mainTitle": main_title, **res} for res in ocr_results])
        except Exception as e:
            print("Failed to save to MongoDB:", e)

        return jsonify({"success": True, "source": "OCR Screen Scan", "mainTitle": main_title, "results": ocr_results}), 200

    if os.path.exists(v_path): os.remove(v_path)
    return jsonify({"error": "Failed to process video."}), 400

@app.route('/api/video/summary', methods=['POST'])
def get_ai_summary():
    data = request.json
    topic = data.get('topicTitle', '')
    history_list = data.get('previousContext', []) 
    history_text = ", ".join(history_list[-5:]) if isinstance(history_list, list) else history_list
    
    try:
        prompt = f"Current Topic: '{topic}'\nPichle topics: [{history_text}]\nAap ek expert teacher hain. Strictly 2-3 line mein Hinglish mein batayein ki 'User ab tak kya sikh chuka hai aur ab kya padhne wala hai.'"
        res_text = generate_with_fallback(prompt)
        return jsonify({"summary": res_text.strip()}), 200
    except Exception as e:
        return jsonify({"error": f"Gemini Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=3000, debug=True)

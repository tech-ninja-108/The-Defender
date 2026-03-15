const API_BASE_URL = window.location.origin; 
let allResults = [];
let simulationInterval;
let uploadStartTime; // Time track karne ke liye

// Network Animation Code (From user snippet)
function initBackgroundCanvas() {
    const canvas = document.getElementById('network-canvas');
    const ctx = canvas.getContext('2d');
    let points = [];
    const numPoints = innerWidth < 800 ? 50 : 100;
    const maxDist = 180;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        points = [];
        for (let i = 0; i < numPoints; i++) {
            points.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                r: Math.random() * 2 + 1
            });
        }
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (let i = 0; i < points.length; i++) {
            const p = points[i];
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 242, 254, 0.4)';
            ctx.fill();
            for (let j = i + 1; j < points.length; j++) {
                const p2 = points[j];
                const d = Math.sqrt((p.x - p2.x)**2 + (p.y - p2.y)**2);
                if (d < maxDist) {
                    ctx.beginPath();
                    ctx.lineWidth = 1 - d / maxDist;
                    ctx.strokeStyle = `rgba(155, 81, 224, ${0.1 * (1 - d / maxDist)})`;
                    ctx.moveTo(p.x, p.y); ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(draw);
    }
    window.addEventListener('resize', resize);
    resize(); draw();
}

document.addEventListener('DOMContentLoaded', () => {
    initBackgroundCanvas();
    const savedUrl = localStorage.getItem('visionary_saved_url');
    if (savedUrl) {
        document.getElementById('videoUrl').value = savedUrl;
        handleUrlInput();
    }
});

function handleUrlInput() {
    const urlInput = document.getElementById('videoUrl');
    const fileWrapper = document.getElementById('file-upload-wrapper');
    const fileInput = document.getElementById('videoFile');
    
    localStorage.setItem('visionary_saved_url', urlInput.value);
    
    if (urlInput.value.trim() !== "") {
        fileWrapper.style.opacity = '0.4';
        fileWrapper.style.pointerEvents = 'none';
        fileInput.disabled = true;
    } else {
        fileWrapper.style.opacity = '1';
        fileWrapper.style.pointerEvents = 'auto';
        fileInput.disabled = false;
    }
}

function updateFileName(input) {
    const display = document.getElementById('file-name-display');
    const urlInput = document.getElementById('videoUrl');
    if (input.files && input.files[0]) {
        const sizeMB = (input.files[0].size / (1024 * 1024)).toFixed(1);
        display.innerText = `📄 ${input.files[0].name} (${sizeMB} MB)`;
        display.style.color = "var(--accent-blue)"; // Color update for file name readability
        display.style.textShadow = "0 0 10px rgba(0, 242, 254, 0.4)";
        urlInput.disabled = true;
        urlInput.style.opacity = '0.5';
        
        // Auto-submit when file is selected
        setTimeout(() => {
            analyzeVideo();
        }, 500);
    } else {
        display.innerText = "Upload Video from Browser";
        display.style.color = "var(--text-muted)";
        display.style.textShadow = "none";
        urlInput.disabled = false;
        urlInput.style.opacity = '1';
        handleUrlInput();
    }
}

function setStepActive(stepNum) {
    for(let i=1; i<=4; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if(i < stepNum) {
            stepEl.className = "step done";
            stepEl.innerHTML = "✅ " + stepEl.innerText.replace('✅ ', '').replace('⏳ ', '');
        } else if (i === stepNum) {
            stepEl.className = "step active";
            stepEl.innerHTML = `<div class="step-spinner"></div> ` + stepEl.innerText.replace('✅ ', '').replace('⏳ ', '');
        } else {
            stepEl.className = "step";
        }
    }
}

// Simulate progress for YouTube links (since server does the downloading)
function simulateServerProgress() {
    let progress = 0;
    const bar = document.getElementById('progress-bar');
    const percent = document.getElementById('progress-percent');
    const size = document.getElementById('progress-size');
    
    size.innerText = "Server Processing (YouTube) | ETA: Depending on video length";
    
    simulationInterval = setInterval(() => {
        if (progress < 40) {
            progress += Math.random() * 2;
            setStepActive(1);
        } else if (progress < 70) {
            progress += Math.random() * 1.5;
            setStepActive(2);
            document.getElementById('main-status').innerText = "Processing Video";
            document.getElementById('sub-status').innerText = "Running audio/visual extraction...";
        } else if (progress < 95) {
            progress += Math.random() * 0.5;
            setStepActive(3);
            document.getElementById('main-status').innerText = "AI Analysis";
            document.getElementById('sub-status').innerText = "Processing OCR & Speech to Text...";
        }
        
        if (progress > 98) progress = 98; // Hold at 98% until API responds
        
        bar.style.width = `${progress}%`;
        percent.innerText = `${Math.floor(progress)}%`;
    }, 500);
}

function analyzeVideo() {
    const url = document.getElementById('videoUrl').value;
    const fileInput = document.getElementById('videoFile').files[0];
    const isOcr = document.getElementById('ocrMode').checked;

    if(!url && !fileInput) return alert("Please provide a YouTube Link OR upload a video!");

    // Show UI
    document.getElementById('state-setup').style.display = 'none';
    document.getElementById('state-process').style.display = 'block';
    
    const formData = new FormData();
    formData.append('mode', isOcr ? 'ocr' : 'normal');
    
    if(url) {
        formData.append('videoUrl', url);
        document.getElementById('main-status').innerText = "Fetching from YouTube";
        simulateServerProgress();
    }
    if(fileInput) {
        formData.append('videoFile', fileInput);
        document.getElementById('main-status').innerText = "Uploading File";
        uploadStartTime = Date.now(); // Record start time for ETA
    }

    // Using XMLHttpRequest to track actual file upload progress
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/video/analyze`, true);

    // TRACK UPLOAD PROGRESS & ETA
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable && fileInput) {
            const percentComplete = (e.loaded / e.total) * 100;
            const loadedMB = (e.loaded / (1024 * 1024)).toFixed(2);
            const totalMB = (e.total / (1024 * 1024)).toFixed(2);
            
            // --- ETA Logic Start ---
            const elapsedTimeInSeconds = (Date.now() - uploadStartTime) / 1000;
            let etaText = "Calculating...";
            
            if (elapsedTimeInSeconds > 1 && e.loaded > 0) {
                const bytesPerSecond = e.loaded / elapsedTimeInSeconds;
                const remainingBytes = e.total - e.loaded;
                const etaSeconds = remainingBytes / bytesPerSecond;
                
                if (etaSeconds < 60) {
                    etaText = `ETA: ~${Math.ceil(etaSeconds)}s`;
                } else {
                    const mins = Math.floor(etaSeconds / 60);
                    const secs = Math.ceil(etaSeconds % 60);
                    etaText = `ETA: ~${mins}m ${secs}s`;
                }
            }
            // --- ETA Logic End ---

            document.getElementById('progress-bar').style.width = percentComplete + '%';
            document.getElementById('progress-percent').innerText = Math.floor(percentComplete) + '%';
            
            document.getElementById('progress-size').innerText = `${loadedMB} MB / ${totalMB} MB | ${etaText}`;

            if (percentComplete === 100) {
                document.getElementById('main-status').innerText = "UPLOAD COMPLETE";
                document.getElementById('sub-status').innerText = "Server is now running AI Engine (OCR)... Please wait.";
                document.getElementById('progress-size').innerText = `${totalMB} MB / ${totalMB} MB | Processing on Server...`;
                setStepActive(2);
                
                // Switch to AI processing steps while waiting for response
                setTimeout(() => { setStepActive(3); }, 2000);
            }
        }
    };

    // HANDLE RESPONSE
    xhr.onload = function() {
        clearInterval(simulationInterval);
        
        if (xhr.status >= 200 && xhr.status < 300) {
            setStepActive(4);
            document.getElementById('progress-bar').style.width = '100%';
            document.getElementById('progress-percent').innerText = '100%';
            document.getElementById('main-status').innerText = "ANALYSIS COMPLETE!";
            document.getElementById('main-icon-spinner').style.display = "none";
            document.getElementById('main-icon').style.display = "block";
            document.getElementById('progress-size').innerText = "Ready!";
            
            try {
                const data = JSON.parse(xhr.responseText);
                if(data.success || data.results) {
                    allResults = data.results || [];
                    if(data.mainTitle) {
                        document.getElementById('playing-title').innerText = data.mainTitle;
                    }
                    setTimeout(displayResults, 800); 
                } else {
                    alert("Analysis Failed: " + (data.error || "Unknown Error"));
                    location.reload();
                }
            } catch(err) {
                alert("Invalid response from server.");
                location.reload();
            }
        } else {
            alert(`Server Error (${xhr.status}). Check your backend logs.`);
            location.reload();
        }
    };

    xhr.onerror = function() {
        clearInterval(simulationInterval);
        alert("Connection Error. Is your Python backend running?");
        location.reload();
    };

    xhr.send(formData);
}

// --- Rest of the rendering functions remain same ---
function displayResults() {
    document.getElementById('state-process').style.display = 'none';
    document.getElementById('state-results').style.display = 'flex'; 

    const list = document.getElementById('topicsList');
    list.innerHTML = "";

    if(!allResults || allResults.length === 0) {
        list.innerHTML = "<p style='color:#aaa;'>No chapters found.</p>";
        return;
    }

    allResults.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = "topic-card";
        card.id = `card-${index}`;
        
        let timeText = item.startTime;
        if (!isNaN(timeText)) {
            let mins = Math.floor(timeText / 60);
            let secs = Math.floor(timeText % 60);
            timeText = `${mins}:${secs < 10 ? '0'+secs : secs}`;
        }

        card.innerHTML = `
            <div class="thumb-box">
                <img src="${item.thumbnail || 'https://via.placeholder.com/150x84/121212/ff0000?text=Video'}" alt="Thumb">
                <div class="time-badge">${timeText}</div>
            </div>
            <div class="topic-details">
                <h4 class="topic-title">${item.topicTitle}</h4>
                <span class="topic-time">Chapter ${index + 1}</span>
            </div>
        `;
        card.onclick = () => selectTopic(index);
        list.appendChild(card);
    });

    selectTopic(0);
}

function getEmbedUrl(playLink) {
    if (!playLink || playLink === '#') return null;
    try {
        const url = new URL(playLink);
        let videoId = url.pathname.slice(1);
        if(url.hostname.includes('youtube.com')) {
            videoId = url.searchParams.get('v');
        }
        let t = url.searchParams.get('t') || 0;
        t = t.toString().replace('s', '');
        return `https://www.youtube.com/embed/${videoId}?start=${t}&autoplay=1`;
    } catch(e) { return null; }
}

async function selectTopic(index) {
    if(allResults.length === 0) return;
    const item = allResults[index];
    
    document.querySelectorAll('.topic-card').forEach(c => c.classList.remove('active'));
    const activeCard = document.getElementById(`card-${index}`);
    if(activeCard) activeCard.classList.add('active');

    if (window.innerWidth <= 1024) window.scrollTo({ top: 0, behavior: 'smooth' });

    let timeText = isNaN(item.startTime) ? item.startTime : `${Math.floor(item.startTime / 60)}m ${Math.floor(item.startTime % 60)}s`;
    document.getElementById('playing-meta').innerText = `Current Topic: ${item.topicTitle} | Starts at: ${timeText}`;
    
    const embedUrl = getEmbedUrl(item.playLink);
    const ytPlayer = document.getElementById('yt-player');
    const localPlayer = document.getElementById('local-player');

    if(embedUrl) {
        localPlayer.style.display = 'none';
        localPlayer.pause();
        ytPlayer.style.display = 'block';
        ytPlayer.src = embedUrl; 
    } else {
        ytPlayer.style.display = 'none';
        ytPlayer.src = '';
        localPlayer.style.display = 'block';
        
        // Add Local File Badge - Updated heavily for beautiful colors
        document.getElementById('playing-meta').innerHTML += ` <span style="background: linear-gradient(135deg, var(--accent-red) 0%, var(--accent-purple) 100%); color: white; padding: 4px 10px; border-radius: 8px; font-size: 0.85rem; margin-left: 10px; font-weight: bold; box-shadow: 0 0 10px rgba(255, 51, 102, 0.4);">💾 Local File</span>`;
        
        // Set and play local video
        const fileInput = document.getElementById('videoFile').files[0];
        if (fileInput) {
            const localUrl = URL.createObjectURL(fileInput);
            // Only update src if it's different to prevent full reload on same video
            if (localPlayer.src !== localUrl) {
                localPlayer.src = localUrl;
            }
            localPlayer.currentTime = item.startTime || 0;
            localPlayer.play().catch(e => console.log("Auto-play blocked:", e));
        } else {
            document.getElementById('playing-meta').innerText += " (Video source not found)";
        }
    }

    const summaryText = document.getElementById('summary-text');
    summaryText.innerHTML = "<span style='color: var(--secondary);'>⏳ Loading...</span> fetching AI context...";
    
    const previousHistory = allResults.slice(0, index).map(r => r.topicTitle);
    
    try {
        const res = await fetch(`${API_BASE_URL}/api/video/summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topicTitle: item.topicTitle, previousContext: previousHistory })
        });
        
        if(!res.ok) throw new Error("Summary API Failed");
        const data = await res.json();
        
        summaryText.innerText = data.summary ? data.summary : "No context summary available.";
        
    } catch (err) {
        summaryText.innerHTML = "<span style='color: #ff4d4d;'>Failed to load summary.</span>";
    }
}

# app.py - TikTok downloader with watermark removal for photos and videos
from flask import Flask, request, jsonify, render_template_string
import yt_dlp
import json
import re

app = Flask(__name__)

# HTML template with support for photos and videos
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Saver Pro</title>
    <style>
        body { font-family: sans-serif; background: #000; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
        .card { background: #111; padding: 25px; border-radius: 15px; width: 90%; max-width: 400px; text-align: center; border: 1px solid #fe2c55; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px; border: none; box-sizing: border-box; }
        button { background: #fe2c55; color: white; border: none; padding: 12px; width: 100%; border-radius: 8px; font-weight: bold; cursor: pointer; }
        #result { display: none; margin-top: 20px; }
        .media-container { margin-top: 15px; }
        .media-container img, .media-container video { width: 100%; max-height: 400px; border-radius: 10px; object-fit: contain; background: #222; }
        .download-link { display: inline-block; background: #25f4ee; color: black; padding: 10px 20px; margin-top: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; }
        .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; margin-top: 10px; }
        .photo-grid img { width: 100%; border-radius: 6px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2>TikTok <span style="color:#fe2c55">Saver</span></h2>
        <input type="text" id="url" placeholder="Pega el link de TikTok (video o foto)">
        <button onclick="descargar()">Obtener Contenido</button>
        <div id="loading" style="display:none; margin-top:10px;">⚡ Procesando...</div>
        <div id="result">
            <div id="mediaContainer" class="media-container"></div>
            <a id="downloadBtn" class="download-link" href="" target="_blank">Descargar Sin Marca</a>
            <div id="photoGrid" class="photo-grid"></div>
        </div>
    </div>
    <script>
        async function descargar() {
            const url = document.getElementById('url').value;
            if(!url) return alert("Pega un link");
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            try {
                const res = await fetch('/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();
                if(data.error) throw new Error(data.error);
                const container = document.getElementById('mediaContainer');
                const grid = document.getElementById('photoGrid');
                const downloadBtn = document.getElementById('downloadBtn');
                container.innerHTML = '';
                grid.innerHTML = '';
                if(data.type === 'photo') {
                    // Single photo or multiple photos (carousel)
                    if(data.photos && data.photos.length > 0) {
                        data.photos.forEach((p, i) => {
                            const img = document.createElement('img');
                            img.src = p;
                            img.alt = 'Foto ' + (i+1);
                            grid.appendChild(img);
                        });
                        // Set first photo as main preview
                        const mainImg = document.createElement('img');
                        mainImg.src = data.photos[0];
                        container.appendChild(mainImg);
                        // For carousel, download first photo or all? We provide first.
                        downloadBtn.href = data.photos[0];
                    } else {
                        const img = document.createElement('img');
                        img.src = data.url;
                        container.appendChild(img);
                        downloadBtn.href = data.url;
                    }
                } else {
                    // Video
                    const video = document.createElement('video');
                    video.src = data.url;
                    video.controls = true;
                    video.autoplay = false;
                    video.style.width = '100%';
                    container.appendChild(video);
                    downloadBtn.href = data.url;
                }
                document.getElementById('loading').style.display = 'none';
                document.getElementById('result').style.display = 'block';
            } catch(e) {
                alert("Error: " + e.message);
                document.getElementById('loading').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL requerida"}), 400

    # Enhanced yt-dlp options for watermark removal and photo extraction
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Referer': 'https://www.tiktok.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'extractor_args': {
            'tiktok': {
                'embed': ['false'],  # Avoid embedded metadata that may include watermark
                'no_watermark': ['true'],  # Attempt to get no-watermark
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Detect if it's a photo or video
            # TikTok photos have 'entries' for carousel or 'extractor_key' == 'TikTok' and no video formats
            is_photo = False
            photos = []
            video_url = None
            thumbnail = info.get('thumbnail')
            
            # Check for carousel (multiple photos)
            if 'entries' in info and info['entries']:
                entries = info['entries']
                if entries and 'thumbnails' in entries[0]:
                    # It's a photo carousel
                    is_photo = True
                    for entry in entries:
                        # Get highest quality thumbnail/photo
                        if 'thumbnails' in entry and entry['thumbnails']:
                            # Sort by resolution and take last (highest)
                            thumbs = sorted(entry['thumbnails'], key=lambda x: x.get('width', 0) * x.get('height', 0))
                            if thumbs:
                                photos.append(thumbs[-1]['url'])
                        elif 'url' in entry:
                            photos.append(entry['url'])
            # Check if it's a single photo (no video formats, but has thumbnails)
            elif 'formats' not in info or len(info.get('formats', [])) == 0:
                # It's likely a photo
                is_photo = True
                if 'thumbnails' in info and info['thumbnails']:
                    # Get highest quality thumbnail (this often is the actual photo)
                    thumbs = sorted(info['thumbnails'], key=lambda x: x.get('width', 0) * x.get('height', 0))
                    if thumbs:
                        photos.append(thumbs[-1]['url'])
                elif 'url' in info:
                    photos.append(info['url'])
            else:
                # It's a video - find the best format without watermark
                # yt-dlp often provides 'download_addr' or 'download_addr-0' for no-watermark
                formats = info.get('formats', [])
                # Filter for formats that likely have no watermark (often 'download_addr' or 'https://...')
                no_wm_formats = [f for f in formats if 'download_addr' in f.get('format_id', '') or 'http' in f.get('url', '')]
                if no_wm_formats:
                    # Prefer the one with highest quality
                    best = max(no_wm_formats, key=lambda f: f.get('height', 0) * f.get('width', 0) if f.get('height') and f.get('width') else 0)
                    video_url = best.get('url')
                else:
                    # Fallback to first format
                    video_url = formats[0].get('url') if formats else None
                
                # If no video_url, try extract via info['url']
                if not video_url:
                    video_url = info.get('url')
            
            # If it's a photo and we have photos, return them
            if is_photo and photos:
                return jsonify({
                    "type": "photo",
                    "photos": photos,
                    "thumbnail": thumbnail,
                    "title": info.get('title', '')
                })
            elif video_url:
                return jsonify({
                    "type": "video",
                    "url": video_url,
                    "thumbnail": thumbnail,
                    "title": info.get('title', '')
                })
            else:
                # Fallback: try to get any media URL
                if 'url' in info:
                    return jsonify({
                        "type": "unknown",
                        "url": info['url'],
                        "thumbnail": thumbnail,
                        "title": info.get('title', '')
                    })
                else:
                    return jsonify({"error": "No se pudo extraer el contenido"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

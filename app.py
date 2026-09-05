# app.py - TikTok downloader with proxy and fallbacks (fully functional for Vercel)
import os
import re
import json
import requests
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
import yt_dlp

app = Flask(__name__)

# HTML template with proxy integration
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Saver Pro</title>
    <style>
        body { font-family: sans-serif; background: #000; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
        .card { background: #111; padding: 25px; border-radius: 15px; width: 90%; max-width: 420px; text-align: center; border: 1px solid #fe2c55; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px; border: none; box-sizing: border-box; }
        button { background: #fe2c55; color: white; border: none; padding: 12px; width: 100%; border-radius: 8px; font-weight: bold; cursor: pointer; }
        #result { display: none; margin-top: 20px; }
        .media-container { margin-top: 15px; }
        .media-container img, .media-container video { width: 100%; max-height: 400px; border-radius: 10px; object-fit: contain; background: #222; }
        .download-link { display: inline-block; background: #25f4ee; color: black; padding: 10px 20px; margin-top: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; }
        .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; margin-top: 10px; }
        .photo-grid img { width: 100%; border-radius: 6px; cursor: pointer; }
        #loading { display: none; margin-top: 10px; }
        .error-msg { color: #fe2c55; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>TikTok <span style="color:#fe2c55">Saver</span></h2>
        <input type="text" id="url" placeholder="Pega el link de TikTok (video o foto)">
        <button onclick="descargar()">Obtener Contenido</button>
        <div id="loading">⚡ Procesando...</div>
        <div id="result">
            <div id="mediaContainer" class="media-container"></div>
            <a id="downloadBtn" class="download-link" href="" target="_blank">Descargar Sin Marca</a>
            <div id="photoGrid" class="photo-grid"></div>
        </div>
        <div id="errorMsg" class="error-msg"></div>
    </div>
    <script>
        async function descargar() {
            const url = document.getElementById('url').value.trim();
            if(!url) return alert("Pega un link válido");
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('errorMsg').innerText = '';
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
                // Construir URL del proxy
                const proxyUrl = (raw) => '/proxy?url=' + encodeURIComponent(raw);
                if(data.type === 'photo') {
                    if(data.photos && data.photos.length > 0) {
                        data.photos.forEach((p, i) => {
                            const img = document.createElement('img');
                            img.src = proxyUrl(p);
                            img.alt = 'Foto ' + (i+1);
                            grid.appendChild(img);
                        });
                        const mainImg = document.createElement('img');
                        mainImg.src = proxyUrl(data.photos[0]);
                        container.appendChild(mainImg);
                        downloadBtn.href = proxyUrl(data.photos[0]);
                    } else {
                        const img = document.createElement('img');
                        img.src = proxyUrl(data.url);
                        container.appendChild(img);
                        downloadBtn.href = proxyUrl(data.url);
                    }
                } else {
                    // Video
                    const video = document.createElement('video');
                    video.src = proxyUrl(data.url);
                    video.controls = true;
                    video.autoplay = false;
                    video.style.width = '100%';
                    container.appendChild(video);
                    downloadBtn.href = proxyUrl(data.url);
                }
                document.getElementById('loading').style.display = 'none';
                document.getElementById('result').style.display = 'block';
            } catch(e) {
                document.getElementById('errorMsg').innerText = 'Error: ' + e.message;
                document.getElementById('loading').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

# Cookie helper
def get_cookie_file():
    cookie_data = os.environ.get('TIKTOK_COOKIES')
    if cookie_data:
        cookie_path = '/tmp/cookies.txt'
        with open(cookie_path, 'w') as f:
            f.write(cookie_data)
        return cookie_path
    return None

# Proxy endpoint to serve media with correct headers and handle redirects
@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({'error': 'Missing url parameter'}), 400

    # Determine content type from extension or fallback
    ext = target_url.split('.')[-1].lower()
    if ext in ['mp4', 'mov', 'avi']:
        content_type = 'video/mp4'
    elif ext in ['jpg', 'jpeg', 'png', 'webp']:
        content_type = 'image/jpeg'
    else:
        content_type = 'application/octet-stream'

    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Referer': 'https://www.tiktok.com/',
        'Accept': 'video/mp4,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        # Use stream=True and allow redirects
        resp = requests.get(target_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
        if resp.status_code != 200:
            # Try with a different User-Agent if 403
            if resp.status_code == 403:
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                resp = requests.get(target_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
            if resp.status_code != 200:
                return jsonify({'error': f'Proxy fetch failed with status {resp.status_code}'}), 500

        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        response = Response(stream_with_context(generate()), content_type=content_type)
        # Optionally force download
        # response.headers['Content-Disposition'] = f'attachment; filename="media.{ext}"'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Main extraction function with fallbacks
def fetch_tiktok_media(url):
    cookie_file = get_cookie_file()
    # Primary options with cookies and watermark removal
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
                'embed': ['false'],
                'no_watermark': ['true'],
            }
        }
    }
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        # Fallback 1: without cookies, with less strict options
        ydl_opts2 = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
            },
            'format': 'best',
            'ignoreerrors': True,
            'extractor_args': {'tiktok': {'embed': ['false']}}
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts2) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e2:
            # Fallback 2: external API (TikSave)
            api_url = f"https://www.tiksave.com/api?url={url}"
            try:
                resp = requests.get(api_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('status') and data.get('data'):
                        video_data = data['data'].get('video')
                        if video_data and len(video_data) > 0:
                            return {
                                'type': 'video',
                                'url': video_data[0].get('url'),
                                'thumbnail': data['data'].get('cover'),
                                'title': data['data'].get('title', '')
                            }
                        images = data['data'].get('images', [])
                        if images:
                            return {
                                'type': 'photo',
                                'photos': images,
                                'thumbnail': images[0],
                                'title': data['data'].get('title', '')
                            }
            except:
                pass
            # Fallback 3: try another API (SnapTik)
            try:
                api_url2 = f"https://api.snap-tik.com/api?url={url}"
                resp = requests.get(api_url2, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('success') and data.get('data'):
                        video_url = data['data'].get('video')
                        if video_url:
                            return {
                                'type': 'video',
                                'url': video_url,
                                'thumbnail': data['data'].get('cover'),
                                'title': data['data'].get('title', '')
                            }
            except:
                pass
            raise Exception("All extraction methods failed: " + str(e))

    # Parse info for photo/video
    is_photo = False
    photos = []
    video_url = None
    thumbnail = info.get('thumbnail')

    # Check for carousel (entries with thumbnails)
    if 'entries' in info and info['entries']:
        entries = info['entries']
        if entries and 'thumbnails' in entries[0]:
            is_photo = True
            for entry in entries:
                if 'thumbnails' in entry and entry['thumbnails']:
                    thumbs = sorted(entry['thumbnails'], key=lambda x: x.get('width', 0) * x.get('height', 0))
                    if thumbs:
                        photos.append(thumbs[-1]['url'])
                elif 'url' in entry:
                    photos.append(entry['url'])
        else:
            # May be a video playlist? ignore
            pass

    # Single photo detection
    if not is_photo and ('formats' not in info or len(info.get('formats', [])) == 0):
        is_photo = True
        if 'thumbnails' in info and info['thumbnails']:
            thumbs = sorted(info['thumbnails'], key=lambda x: x.get('width', 0) * x.get('height', 0))
            if thumbs:
                photos.append(thumbs[-1]['url'])
        elif 'url' in info:
            photos.append(info['url'])

    if is_photo and photos:
        # Clean photo URLs (some may be relative)
        photos = [p if p.startswith('http') else 'https:' + p if p.startswith('//') else p for p in photos]
        return {
            'type': 'photo',
            'photos': photos,
            'thumbnail': thumbnail,
            'title': info.get('title', '')
        }

    # Video extraction - prioritize download_addr
    formats = info.get('formats', [])
    no_wm_formats = [f for f in formats if 'download_addr' in f.get('format_id', '')]
    if no_wm_formats:
        best = max(no_wm_formats, key=lambda f: f.get('height', 0) * f.get('width', 0) if f.get('height') and f.get('width') else 0)
        video_url = best.get('url')
    else:
        if formats:
            # Prefer format with highest quality and no watermark note
            best_format = max(formats, key=lambda f: f.get('height', 0) * f.get('width', 0) if f.get('height') and f.get('width') else 0)
            video_url = best_format.get('url')
        else:
            video_url = info.get('url')

    if video_url:
        if not video_url.startswith('http'):
            video_url = 'https:' + video_url if video_url.startswith('//') else video_url
        return {
            'type': 'video',
            'url': video_url,
            'thumbnail': thumbnail,
            'title': info.get('title', '')
        }

    raise Exception("No downloadable media found")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL requerida"}), 400
    try:
        result = fetch_tiktok_media(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

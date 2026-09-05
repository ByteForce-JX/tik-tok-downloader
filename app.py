# app.py - ÐŸÐ¾Ð»Ð½Ð¾Ñ†ÐµÐ½Ð½Ñ‹Ð¹ Ð·Ð°Ð³Ñ€ÑƒÐ·Ñ‡Ð¸Ðº TikTok (Ð²Ð¸Ð´ÐµÐ¾ Ð¸ Ñ„Ð¾Ñ‚Ð¾) Ñ Ð¿Ð¾Ð´Ð´ÐµÑ€Ð¶ÐºÐ¾Ð¹ cookie Ð¸ Ñ„ÐµÐ¹Ð»Ð±ÑÐºÐ¾Ð²
import os
import json
import requests
from flask import Flask, request, jsonify, render_template_string
import yt_dlp

app = Flask(__name__)

# HTML-ÑˆÐ°Ð±Ð»Ð¾Ð½ (Ð°Ð´Ð°Ð¿Ñ‚Ð¸Ñ€Ð¾Ð²Ð°Ð½ Ð´Ð»Ñ Ð²Ð¸Ð´ÐµÐ¾ Ð¸ Ñ„Ð¾Ñ‚Ð¾)
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
                    if(data.photos && data.photos.length > 0) {
                        data.photos.forEach((p, i) => {
                            const img = document.createElement('img');
                            img.src = p;
                            img.alt = 'Foto ' + (i+1);
                            grid.appendChild(img);
                        });
                        const mainImg = document.createElement('img');
                        mainImg.src = data.photos[0];
                        container.appendChild(mainImg);
                        downloadBtn.href = data.photos[0];
                    } else {
                        const img = document.createElement('img');
                        img.src = data.url;
                        container.appendChild(img);
                        downloadBtn.href = data.url;
                    }
                } else {
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

# Ð¤ÑƒÐ½ÐºÑ†Ð¸Ñ Ð´Ð»Ñ Ð¿Ð¾Ð»ÑƒÑ‡ÐµÐ½Ð¸Ñ cookie Ð¸Ð· Ð¿ÐµÑ€ÐµÐ¼ÐµÐ½Ð½Ð¾Ð¹ Ð¾ÐºÑ€ÑƒÐ¶ÐµÐ½Ð¸Ñ (Ð´Ð»Ñ Vercel)
def get_cookie_file():
    cookie_data = os.environ.get('TIKTOK_COOKIES')
    if cookie_data:
        # Vercel Ñ€Ð°Ð·Ñ€ÐµÑˆÐ°ÐµÑ‚ Ð·Ð°Ð¿Ð¸ÑÑŒ Ñ‚Ð¾Ð»ÑŒÐºÐ¾ Ð² /tmp
        cookie_path = '/tmp/cookies.txt'
        with open(cookie_path, 'w') as f:
            f.write(cookie_data)
        return cookie_path
    return None

# ÐžÑÐ½Ð¾Ð²Ð½Ð¾Ð¹ Ñ„ÑƒÐ½ÐºÑ†Ð¸Ð¾Ð½Ð°Ð» Ñ Ð¿Ð¾Ð²Ñ‚Ð¾Ñ€Ð½Ñ‹Ð¼Ð¸ Ð¿Ð¾Ð¿Ñ‹Ñ‚ÐºÐ°Ð¼Ð¸ Ð¸ Ñ„ÐµÐ¹Ð»Ð±ÑÐºÐ¾Ð¼
def fetch_tiktok_media(url):
    cookie_file = get_cookie_file()
    # Ð‘Ð°Ð·Ð¾Ð²Ñ‹Ðµ Ð¾Ð¿Ñ†Ð¸Ð¸
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
        # ÐŸÐµÑ€Ð²Ñ‹Ð¹ ÑÑ‚Ñ€Ð°Ñ‚ÐµÐ³Ð¸Ñ‡ÐµÑÐºÐ¸Ð¹ Ñ„ÐµÐ¹Ð»Ð±ÑÐº: Ð¿Ñ€Ð¾Ð±ÑƒÐµÐ¼ Ð±ÐµÐ· ÐºÑƒÐºÐ¸, Ð½Ð¾ Ñ Ð±Ð¾Ð»ÐµÐµ Ð»ÑŽÐ±ÐµÑ€Ð°Ð»ÑŒÐ½Ñ‹Ð¼Ð¸ Ð½Ð°ÑÑ‚Ñ€Ð¾Ð¹ÐºÐ°Ð¼Ð¸
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
            # ÐŸÐ¾ÑÐ»ÐµÐ´Ð½Ð¸Ð¹ Ñ„ÐµÐ¹Ð»Ð±ÑÐº: Ð¸ÑÐ¿Ð¾Ð»ÑŒÐ·ÑƒÐµÐ¼ Ð²Ð½ÐµÑˆÐ½ÑŽÑŽ API (TikSave)
            fallback_url = f"https://www.tiksave.com/api?url={url}"
            try:
                resp = requests.get(fallback_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # ÐžÐ¶Ð¸Ð´Ð°ÐµÐ¼ Ñ„Ð¾Ñ€Ð¼Ð°Ñ‚ {status: true, data: {video: [ {url: ...} ] } }
                    if data.get('status') and data.get('data'):
                        video_data = data['data'].get('video')
                        if video_data and len(video_data) > 0:
                            return {
                                'type': 'video',
                                'url': video_data[0].get('url'),
                                'thumbnail': data['data'].get('cover'),
                                'title': data['data'].get('title', '')
                            }
                        # Ð¢Ð°ÐºÐ¶Ðµ Ð¼Ð¾Ð¶ÐµÑ‚ Ð±Ñ‹Ñ‚ÑŒ Ñ„Ð¾Ñ‚Ð¾
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
            raise Exception("Ð�Ðµ ÑƒÐ´Ð°Ð»Ð¾ÑÑŒ Ð¿Ð¾Ð»ÑƒÑ‡Ð¸Ñ‚ÑŒ Ð¼ÐµÐ´Ð¸Ð° Ñ‡ÐµÑ€ÐµÐ· yt-dlp Ð¸ Ñ„ÐµÐ¹Ð»Ð±ÑÐº API")

    # ÐžÐ±Ñ€Ð°Ð±Ð¾Ñ‚ÐºÐ° Ð¿Ð¾Ð»ÑƒÑ‡ÐµÐ½Ð½Ð¾Ð¹ Ð¸Ð½Ñ„Ð¾Ñ€Ð¼Ð°Ñ†Ð¸Ð¸ (Ð°Ð½Ð°Ð»Ð¾Ð³Ð¸Ñ‡Ð½Ð¾ Ð¿Ñ€ÐµÐ´Ñ‹Ð´ÑƒÑ‰ÐµÐ¼Ñƒ, Ð½Ð¾ Ñ ÑƒÐ»ÑƒÑ‡ÑˆÐµÐ½Ð¸ÑÐ¼Ð¸)
    is_photo = False
    photos = []
    video_url = None
    thumbnail = info.get('thumbnail')

    # ÐŸÑ€Ð¾Ð²ÐµÑ€ÐºÐ° Ð½Ð° ÐºÐ°Ñ€Ñ€ÑƒÑÐµÐ»ÑŒ
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
            # ÐœÐ¾Ð¶ÐµÑ‚ Ð±Ñ‹Ñ‚ÑŒ Ð²Ð¸Ð´ÐµÐ¾-ÐºÐ°Ñ€Ñ€ÑƒÑÐµÐ»ÑŒ? ÐžÐ±Ñ‹Ñ‡Ð½Ð¾ Ð½ÐµÑ‚, Ð½Ð¾ Ð¿Ñ€Ð¾Ð²ÐµÑ€Ð¸Ð¼
            pass

    # ÐŸÑ€Ð¾Ð²ÐµÑ€ÐºÐ° Ð½Ð° Ð¾Ð´Ð¸Ð½Ð¾Ñ‡Ð½Ð¾Ðµ Ñ„Ð¾Ñ‚Ð¾
    if not is_photo and ('formats' not in info or len(info.get('formats', [])) == 0):
        is_photo = True
        if 'thumbnails' in info and info['thumbnails']:
            thumbs = sorted(info['thumbnails'], key=lambda x: x.get('width', 0) * x.get('height', 0))
            if thumbs:
                photos.append(thumbs[-1]['url'])
        elif 'url' in info:
            photos.append(info['url'])

    # Ð•ÑÐ»Ð¸ ÑÑ‚Ð¾ Ñ„Ð¾Ñ‚Ð¾, Ð²Ð¾Ð·Ð²Ñ€Ð°Ñ‰Ð°ÐµÐ¼
    if is_photo and photos:
        return {
            'type': 'photo',
            'photos': photos,
            'thumbnail': thumbnail,
            'title': info.get('title', '')
        }

    # Ð’Ð¸Ð´ÐµÐ¾: Ð¿Ñ‹Ñ‚Ð°ÐµÐ¼ÑÑ Ð½Ð°Ð¹Ñ‚Ð¸ download_addr
    formats = info.get('formats', [])
    no_wm_formats = [f for f in formats if 'download_addr' in f.get('format_id', '')]
    if no_wm_formats:
        best = max(no_wm_formats, key=lambda f: f.get('height', 0) * f.get('width', 0) if f.get('height') and f.get('width') else 0)
        video_url = best.get('url')
    else:
        # ÐŸÑ€Ð¾Ð±ÑƒÐµÐ¼ Ð²Ð·ÑÑ‚ÑŒ Ð¿ÐµÑ€Ð²Ñ‹Ð¹ format Ñ Ð½Ð°Ð¸Ð±Ð¾Ð»ÑŒÑˆÐ¸Ð¼ Ñ€Ð°Ð·Ñ€ÐµÑˆÐµÐ½Ð¸ÐµÐ¼
        if formats:
            best_format = max(formats, key=lambda f: f.get('height', 0) * f.get('width', 0) if f.get('height') and f.get('width') else 0)
            video_url = best_format.get('url')
        else:
            video_url = info.get('url')

    if video_url:
        return {
            'type': 'video',
            'url': video_url,
            'thumbnail': thumbnail,
            'title': info.get('title', '')
        }

    raise Exception("Ð�Ðµ ÑƒÐ´Ð°Ð»Ð¾ÑÑŒ Ð½Ð°Ð¹Ñ‚Ð¸ URL Ð´Ð»Ñ Ð·Ð°Ð³Ñ€ÑƒÐ·ÐºÐ¸")

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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

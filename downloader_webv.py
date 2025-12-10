from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import yt_dlp
import os
import threading
from urllib.parse import parse_qs, urlparse
import io

class DownloadHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/download':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            url = data.get('url', '')
            quality = data.get('quality', '9+2')
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                output_folder = os.path.join(os.path.expanduser("~"), "Downloads", "Videos")
                os.makedirs(output_folder, exist_ok=True)
                
                ydl_opts = {
                    'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
                    'format': quality,
                    'merge_output_format': 'mkv',  # MKV supports embedded subtitles better
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'zh', 'zh-Hans', 'zh-Hant', 'all'],
                    'embedsubtitles': True,
                    'postprocessors': [{
                        'key': 'FFmpegEmbedSubtitle',
                        'already_have_subtitle': False
                    }],
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    title = info.get('title', 'Unknown')
                    
                    response = {
                        'success': True,
                        'message': 'Download completed!',
                        'filename': filename,
                        'title': title
                    }
            except Exception as e:
                response = {
                    'success': False,
                    'message': str(e)
                }
            
            self.wfile.write(json.dumps(response).encode())
    
    def get_html(self):
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Downloader</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 32px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        
        .input-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
            font-size: 14px;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .quality-options {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .quality-option {
            flex: 1;
            min-width: 120px;
        }
        
        input[type="radio"] {
            display: none;
        }
        
        .quality-label {
            display: block;
            padding: 12px 20px;
            background: #f5f5f5;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        input[type="radio"]:checked + .quality-label {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .quality-label:hover {
            border-color: #667eea;
        }
        
        button {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.loading {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .spinner {
            width: 20px;
            height: 20px;
            border: 3px solid #0c5460;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .info-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            font-size: 13px;
            color: #666;
        }
        
        .info-box strong {
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Video Downloader</h1>
        <p class="subtitle">Download videos with audio and subtitles</p>
        
        <form id="downloadForm">
            <div class="input-group">
                <label for="url">Video URL</label>
                <input 
                    type="text" 
                    id="url" 
                    name="url" 
                    placeholder="Paste your video URL here..."
                    required
                >
            </div>
            
            <div class="input-group">
                <label>Quality</label>
                <div class="quality-options">
                    <div class="quality-option">
                        <input type="radio" id="q240" name="quality" value="5+1">
                        <label for="q240" class="quality-label">240p<br><small>Smallest</small></label>
                    </div>
                    <div class="quality-option">
                        <input type="radio" id="q360" name="quality" value="7+2">
                        <label for="q360" class="quality-label">360p<br><small>Good</small></label>
                    </div>
                    <div class="quality-option">
                        <input type="radio" id="q480" name="quality" value="9+2" checked>
                        <label for="q480" class="quality-label">480p<br><small>Best</small></label>
                    </div>
                </div>
            </div>
            
            <button type="submit" id="downloadBtn">Download Video</button>
        </form>
        
        <div id="status" class="status"></div>
        
        <div class="info-box">
            <strong>📁 Save Location:</strong><br>
            ~/Downloads/Videos/
        </div>
    </div>
    
    <script>
        const form = document.getElementById('downloadForm');
        const status = document.getElementById('status');
        const downloadBtn = document.getElementById('downloadBtn');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = document.getElementById('url').value;
            const quality = document.querySelector('input[name="quality"]:checked').value;
            
            // Show loading state
            status.className = 'status loading';
            status.style.display = 'flex';
            status.innerHTML = '<div class="spinner"></div><span>Downloading video... This may take a few minutes.</span>';
            downloadBtn.disabled = true;
            
            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url, quality })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    status.className = 'status success';
                    status.innerHTML = `
                        <strong>✓ Success!</strong><br>
                        <strong>Title:</strong> ${data.title}<br>
                        <strong>Saved to:</strong> ${data.filename}
                    `;
                } else {
                    status.className = 'status error';
                    status.innerHTML = `<strong>✗ Error:</strong> ${data.message}`;
                }
            } catch (error) {
                status.className = 'status error';
                status.innerHTML = `<strong>✗ Error:</strong> ${error.message}`;
            } finally {
                downloadBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
        '''

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, DownloadHandler)
    print(f"🚀 Video Downloader is running!")
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print(f"💾 Videos will be saved to: ~/Downloads/Videos/")
    print(f"\nPress Ctrl+C to stop the server")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
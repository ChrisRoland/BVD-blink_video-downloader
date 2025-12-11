from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import yt_dlp
import os
import threading
from urllib.parse import parse_qs, urlparse, quote
import io
import uuid

class DownloadHandler(SimpleHTTPRequestHandler):
    # Store download sessions
    download_sessions = {}
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        elif self.path.startswith('/get_file/'):
            # Extract session ID from path
            session_id = self.path.split('/get_file/')[1]
            if session_id in self.download_sessions:
                file_path = self.download_sessions[session_id]
                if os.path.exists(file_path):
                    self.send_file(file_path)
                    # Clean up after sending
                    try:
                        os.remove(file_path)
                        del self.download_sessions[session_id]
                    except:
                        pass
                else:
                    self.send_error(404, "File not found")
            else:
                self.send_error(404, "Session expired")
        else:
            super().do_GET()
    
    def send_file(self, file_path):
        """Send file to user's browser for download"""
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{quote(filename)}"')
            self.send_header('Content-Length', str(file_size))
            self.end_headers()
            
            # Stream file to user
            with open(file_path, 'rb') as f:
                chunk_size = 8192
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except Exception as e:
            print(f"Error sending file: {e}")
    
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
                # Use /tmp directory on Render (ephemeral storage)
                output_folder = os.path.join('/tmp', 'Videos')
                os.makedirs(output_folder, exist_ok=True)
                
                # Map quality presets to flexible format strings that work across platforms
                quality_map = {
                    '5+1': 'worst[height<=240]+bestaudio/worst',
                    '7+2': 'best[height<=360]+bestaudio/best[height<=360]',
                    '9+2': 'best[height<=480]+bestaudio/best[height<=480]'
                }
                
                format_string = quality_map.get(quality, 'best[height<=480]+bestaudio/best')
                
                ydl_opts = {
                    'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
                    'format': format_string,
                    'merge_output_format': 'mkv',  # MKV supports embedded subtitles better
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en'],
                    'embedsubtitles': True,
                    'ignoreerrors': True,  # Continue even if subtitles fail
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
                    
                    # Generate unique session ID for this download
                    session_id = str(uuid.uuid4())
                    self.download_sessions[session_id] = filename
                    
                    response = {
                        'success': True,
                        'message': 'Download completed!',
                        'session_id': session_id,
                        'title': title,
                        'filename': os.path.basename(filename)
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
    <link rel="icon" href="https://fav.farm/🎬">
    <title>BVD</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #A1BC98;
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
            color: #A1BC98;
            margin-bottom: 10px;
            font-size: 32px;
        }
        
        h3 {
            color: #A1BC98;
            margin-bottom: 20px;
            font-size: 20px;
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
            border-color: #A1BC98;
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
            background: #A1BC98;
            color: white;
            border-color: #A1BC98;
        }
        
        .quality-label:hover {
            border-color: #A1BC98;
        }
        
        button {
            width: 100%;
            padding: 16px;
            background: #A1BC98;
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
        
        .download-btn {
            background: #28a745;
            margin-top: 10px;
        }
        
        .download-btn:hover:not(:disabled) {
            box-shadow: 0 10px 20px rgba(40, 167, 69, 0.3);
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
        <div style="text-align: center; margin-bottom: 20px;">
        <h1>BVD</h1>
        <h3>Blink-Video-Downloader</h3>
        </div>
        <p class="subtitle">Download videos with audio and subtitles directly to your device</p>
        
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
            
            <button type="submit" id="downloadBtn">Prepare Download</button>
        </form>
        
        <div id="status" class="status"></div>
        
        <div class="info-box">
            <strong> Download Info:</strong><br>
            Video will be downloaded directly to your device's Downloads folder after processing.
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
            status.innerHTML = '<div class="spinner"></div><span>Processing video... This may take a few minutes.</span>';
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
                    status.style.display = 'block';
                    status.innerHTML = `
                        <strong>✓ Ready!</strong><br>
                        <strong>Title:</strong> ${data.title}<br>
                        <strong>File:</strong> ${data.filename}<br>
                        <button class="download-btn" onclick="downloadFile('${data.session_id}', '${data.filename}')">
                            Download to Device
                        </button>
                    `;
                } else {
                    status.className = 'status error';
                    status.style.display = 'block';
                    status.innerHTML = `<strong>✗ Error:</strong> ${data.message}`;
                }
            } catch (error) {
                status.className = 'status error';
                status.style.display = 'block';
                status.innerHTML = `<strong>✗ Error:</strong> ${error.message}`;
            } finally {
                downloadBtn.disabled = false;
            }
        });
        
        function downloadFile(sessionId, filename) {
            // Create a temporary link and trigger download
            const link = document.createElement('a');
            link.href = '/get_file/' + sessionId;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Update status
            status.innerHTML = '<strong>✓ Download started!</strong><br>Check your Downloads folder.';
        }
    </script>
</body>
</html>
        '''

def run_server(port=8000):
    # Bind to 0.0.0.0 to accept connections from any network interface
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DownloadHandler)
    print(f"🚀 Video Downloader is running!")
    print(f"📱 Server listening on port {port}")
    print(f"💾 Videos will be streamed directly to users")
    print(f"\nPress Ctrl+C to stop the server")
    httpd.serve_forever()

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 8000))
    run_server(port)
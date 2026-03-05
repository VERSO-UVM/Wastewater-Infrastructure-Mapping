import http.server
import socketserver
import webbrowser
import os

PORT = 8000
os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler
handler.extensions_map.update({'.geojson': 'application/json'})

with socketserver.TCPServer(('', PORT), handler) as httpd:
    url = f'http://localhost:{PORT}'
    print(f'Serving at {url}')
    print('Press Ctrl+C to stop.')
    webbrowser.open(url)
    httpd.serve_forever()

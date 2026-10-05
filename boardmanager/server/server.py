from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path("/home/board/boardmanager/bm.autodarts.io").resolve()

class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)

        if self.path.startswith("/assets/") or Path(path).is_file():
            return super().do_GET()

        self.path = "/index.html"
        return super().do_GET()

server = ThreadingHTTPServer(("127.0.0.1", 3001), SPAHandler)
print("Board Manager lokal auf 127.0.0.1:3001")
server.serve_forever()

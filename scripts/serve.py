"""Serve the offline WASM app on loopback only. No uploads, accounts or API."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from functools import partial
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
root=Path(__file__).resolve().parents[1]/'web'
print(f'DoctorTracer: http://127.0.0.1:{args.port}  (Ctrl+C to stop)',flush=True)
try:ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(root))).serve_forever()
except KeyboardInterrupt:pass

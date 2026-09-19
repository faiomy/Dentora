# -*- coding: utf-8 -*-
"""تشغيل خادم الـ API بمفرده (للتطوير/التجربة):

    python -m api                     # 127.0.0.1:8100
    python -m api --host 0.0.0.0 --port 9000
"""

import argparse
import os

from api.config import DEFAULT_HOST, DEFAULT_PORT
from api.server import get_api_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dentora API server")
    parser.add_argument("--host", default=os.environ.get("DENTORA_API_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("DENTORA_API_PORT", DEFAULT_PORT)))
    args = parser.parse_args()

    srv = get_api_server()
    srv.host = args.host
    srv.port = args.port
    print(f"Dentora API listening on http://{srv.host}:{srv.port}/docs")
    if srv.start():
        # البقاء حيًا في الـ main thread (آخر شيء) لحد ما يطلب stop
        import time
        try:
            while srv.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            srv.stop()
#!/usr/bin/env python3
"""
NAUB Enquiry Chatbot — Application Entry Point
Run: python run.py [port]
"""

import sys
import os
import http.server

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbot.database import init_db
from chatbot.engine import get_engine
from chatbot.server import NAUBHandler

DEFAULT_PORT = 8000


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    print("=" * 56)
    print("  NAUB Enquiry Chatbot")
    print("  Nigerian Army University Biu")
    print("=" * 56)

    print("  Initialising database...", end=" ", flush=True)
    init_db()
    print("OK")

    print("  Loading NLP engine...", end=" ", flush=True)
    engine = get_engine()
    print(f"OK ({len(engine.kb)} intents loaded)")

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), NAUBHandler)
    print(f"  Server running at  http://localhost:{port}")
    print(f"  Admin dashboard:   http://localhost:{port}/admin")
    print(f"  Default creds:     admin / naub@admin2024")
    print("=" * 56)
    print("  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down. Goodbye!")
        server.server_close()


if __name__ == "__main__":
    main()

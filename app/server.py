#!/usr/bin/env python3
"""Local HTTP server for the AutoTrader Analyzer dashboard."""
from http.server import ThreadingHTTPServer

from services.config import HOST, PORT  # noqa: F401  (config also prepares sys.path)
from services.http_handler import AnalyzerHandler
from services.movers_facade import start_mover_scheduler


def main():
    start_mover_scheduler()
    server = ThreadingHTTPServer((HOST, PORT), AnalyzerHandler)
    print(f"AutoTrader Analyzer listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

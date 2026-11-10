# ngrok permanent webhook URL (D79)
Setup (once): ngrok.com sign up -> Dashboard -> Domains -> claim the free static domain -> Your Authtoken -> paste both on Paytience Connections ("ngrok") -> Save & Test.
Then paste https://<domain>/api/webhook/tradingview into the TradingView alert once; it never changes.
Code: backend/app/tunnel.py (manager, pinned downloads), connections registry/testers, desktop/paytience_app.py env. Tests: tests/unit/test_tunnel.py, tests/integration/test_connections.py.
Not verified against a real ngrok account here (no account in the sandbox); the log-line parsing (`started tunnel`, `ERR_NGROK_*`) follows ngrok's documented logfmt output.

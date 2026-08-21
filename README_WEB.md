Web UI for QFA-LTL Demo

Quick start (after installing dev requirements):

```bash
python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/ in a browser. Click **Run Demo** to execute the backend pipeline and view results.

Notes:
- The server uses the repository code as backend logic. If `qiskit` is not installed, the circuit compilation demo is skipped and an informative message is returned.
- The frontend lives in `webapp/static/` (plain HTML/CSS/JS, no build step).
- For production demos, consider containerizing (Docker) or adding authentication before exposing to the internet.

Web UI for QFA-LTL Demo

Quick start (after installing dev requirements):

```powershell
py -3 -m pip install -r requirements-dev.txt
py -3 -m uvicorn webapp.app:app --reload
```

Open http://127.0.0.1:8000/ in a browser. Click **Run Demo** to execute the backend pipeline and view results.

Notes:
- The server uses the repository code as backend logic. If `qiskit` is not installed, the circuit compilation demo is skipped and an informative message is returned.
- For production demos, consider containerizing (Docker) or adding authentication before exposing to the internet.

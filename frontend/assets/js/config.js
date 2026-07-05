// Point this at wherever the Django backend is running.
// During local development: run the backend on :8000 and this frontend on :8080
// (e.g. `python3 -m http.server 8080` from this folder), and the .env's
// CORS_ALLOWED_ORIGINS already allows http://localhost:8080 by default.
window.API_BASE_URL = "http://localhost:8000/api/v1";

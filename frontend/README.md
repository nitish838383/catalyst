# SkillBridge AI — HTML / Vanilla JS / Tailwind Frontend

This frontend intentionally uses only:
- HTML5
- Vanilla JavaScript
- Tailwind CSS (CDN)
- Lucide Icons
- Chart.js only on analytics page

The FastAPI backend remains unchanged.

## Run locally

1. Start backend on `http://127.0.0.1:8000`.
2. In this `frontend` directory run a static server:
   - `python -m http.server 3000`
3. Open `http://127.0.0.1:3000`.

The default API URL is `http://127.0.0.1:8000/api/v1`. Change it in `assets/js/config.js` or set localStorage key `skillbridge_api_url`.

## Important

Backend CORS must allow `http://127.0.0.1:3000` and/or `http://localhost:3000` when running locally.

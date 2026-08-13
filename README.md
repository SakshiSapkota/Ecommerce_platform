# Ecommerce — A Tiny Full‑Stack Demo

Welcome! This is a compact, hands-on e‑commerce demo that pairs a lightweight Python backend with a static HTML/JS frontend. I built this as a learning playground — the kind of project you can read through in one sitting, tweak in an afternoon, and use as a starting point for features you actually care about.

**Why this project**
- I wanted something real enough to show how frontend + backend interact, but small enough to understand end-to-end.
- It’s great for practicing JavaScript fetch APIs, basic Python HTTP handling, file uploads, and simple stateful flows like cart → checkout.

**What you’ll find here**
- `backend/`: Minimal Python server code powering API endpoints and data handling.
- `frontend/`: Static pages, styles, and JS that call the backend and manage UI state.
- `uploads/` and `images/`: Simple places for uploaded product images and assets.

**Highlights**
- Browse products, add to cart, and complete a simple checkout flow.
- Authentication skeleton pages (login/register/forgot/reset).
- Lightweight, easy to read code — ideal for learning and experimentation.

**Tech stack**
- Backend: Plain Python (small HTTP server and handlers in `backend/`).
- Frontend: Static HTML, CSS, and vanilla JavaScript under `frontend/`.

**Quick Start**
1. Start the backend server (from the project root):

```powershell
python backend/server.py
```

2. Open the frontend in your browser by opening `frontend/index.html` (or serve the `frontend/` folder with a static server).

Notes: This repo intentionally keeps dependencies minimal. If your environment requires a virtualenv, create and activate it before running the backend.

**Key files**
- [backend/server.py](backend/server.py) — main server entry and routing.
- [backend/handlers.py](backend/handlers.py) — request handlers, API logic.
- [backend/db.py](backend/db.py) — simple data persistence utilities.
- [frontend/index.html](frontend/index.html) — landing page and product browsing UI.
- [frontend/js/api.js](frontend/js/api.js) — frontend API helpers and fetch wrappers.
- [frontend/js/cart.js](frontend/js/cart.js) — cart state and actions.
- [frontend/css/main.css](frontend/css/main.css) — base styling.


If you want, I can:
- Expand the README with setup steps and dependency management.
- Add a `requirements.txt` and a simple `run.sh`/`run.ps1` for convenience.
- Convert backend to use Flask/FastAPI for a more robust API structure.

Happy hacking!

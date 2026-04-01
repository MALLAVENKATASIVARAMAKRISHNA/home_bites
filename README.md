# Home Bites

Home Bites is an online ordering and management system for a home-based food business. Customers can browse items, place orders, track their orders, and manage their profile. Admin users can manage items, users, and orders from a dedicated dashboard.

## Features

- Customer signup and login
- Cookie-based authenticated sessions
- Browse items and top-ordered picks
- Place orders and view order history
- Cancel orders within policy
- Update customer profile details
- Admin dashboard for items, users, and orders
- Local SQLite development setup
- Production PostgreSQL deployment on Render

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Database: SQLite for local development, PostgreSQL for production
- Auth: JWT in `HttpOnly` cookie-backed sessions
- Frontend: HTML, CSS, JavaScript
- Deployment: Render

## Project Structure

```text
home_bites/
├── backend/
│   ├── alembic/
│   ├── auth.py
│   ├── database.py
│   ├── db_models.py
│   ├── db_utils.py
│   ├── main.py
│   ├── models.py
│   ├── requirements.txt
│   └── settings.py
├── frontend/
│   ├── admin.html
│   ├── admin.js
│   ├── config.js
│   ├── index.html
│   ├── items.html
│   ├── my-orders.html
│   ├── my-profile.html
│   ├── styles.css
│   └── ui.js
├── render.yaml
├── scope.md
├── specification.md
└── codex.md
```

## Key Pages

- `frontend/index.html`: landing page, login, signup, featured items, cart
- `frontend/items.html`: full catalog page
- `frontend/my-orders.html`: customer order history
- `frontend/my-profile.html`: customer profile management
- `frontend/admin.html`: admin dashboard

## Backend API Highlights

Auth and user:

- `POST /register`
- `POST /login`
- `POST /logout`
- `GET /me`
- `PUT /me/profile`
- `GET /health`

Items:

- `GET /items`
- `GET /items/top-ordered?limit=3`
- `GET /items/{item_id}`
- `POST /items/`
- `PUT /items/{item_id}`
- `DELETE /items/{item_id}`

Orders:

- `POST /orders/complete`
- `GET /orders/{order_id}/complete`
- `GET /users/{user_id}/orders`
- `POST /orders/{order_id}/cancel`

Admin:

- `GET /users`
- `POST /users/`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`
- `GET /orders`
- `PUT /orders/{order_id}`

## MCP Server

A lightweight MCP server is available at `backend/mcp_server.py`. It exposes project data as MCP tools/resources for assistants and agent clients.

Highlights:

- read tools for health, items, users, and orders
- opt-in write tools for creating orders and updating order state
- write operations are disabled by default for safety

Run it from the `backend` directory after installing dependencies:

```bash
cd backend
pip install -r requirements.txt
python mcp_server.py
```

To enable write-capable tools:

```bash
export HOME_BITES_MCP_ALLOW_WRITES=true
python mcp_server.py
```

## Local Development

### Backend

1. Create and activate a virtual environment.
2. Install backend dependencies.
3. Run the FastAPI server from the `backend` directory.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Local backend default URL:

```text
http://127.0.0.1:8000
```

### Frontend

Serve the `frontend` directory with any static file server. For example:

```bash
cd frontend
python -m http.server 5500
```

Then open:

```text
http://127.0.0.1:5500
```

The frontend defaults to the local backend automatically on `localhost` or `127.0.0.1`.

## Database

- Local development uses SQLite.
- Production uses PostgreSQL.
- Alembic migrations are included in `backend/alembic/`.

Run migrations manually if needed:

```bash
cd backend
alembic -c alembic.ini upgrade head
```

## Environment Variables

Important backend environment variables:

- `APP_ENV=production`
- `DEBUG=false`
- `SECRET_KEY=<long random value>`
- `DATABASE_URL=<postgres connection string>`
- `CORS_ORIGINS=https://home-bites-frontend.onrender.com`

Frontend:

- no frontend env var is required for the current production setup
- optional override: `HOME_BITES_API_BASE_URL`

## Render Deployment

This repo includes a Render blueprint in `render.yaml`.

Backend service:

- service name: `home-bites-api`
- root directory: `backend`
- build command: `pip install -r requirements.txt`
- start command: `alembic -c alembic.ini upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`

Production URLs:

- backend: `https://home-bites.onrender.com`
- frontend origin: `https://home-bites-frontend.onrender.com`

## Auth and CORS Notes

- Sessions are cookie-based and use `credentials: "include"` in frontend requests.
- CORS is handled by FastAPI `CORSMiddleware` with env-driven allowed origins.
- `POST /register` always creates users with role `user`, even if the client sends another role.

## Known Production Behavior

- Render free-tier instances may sleep when idle.
- The first request after inactivity can be slow.
- The homepage uses a longer API timeout and sends a best-effort `/health` warm-up request to reduce first-request failures before login or signup.

## Reference Docs

- `scope.md`
- `specification.md`
- `codex.md`

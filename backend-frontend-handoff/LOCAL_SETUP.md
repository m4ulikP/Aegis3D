# Aegis3D Local Backend Running Guide

This guide provides instructions for the frontend developer to run the Aegis3D FastAPI backend locally and connect the Next.js application shell to it.

---

## Service URLs & Endpoints

| Resource | URL |
| :--- | :--- |
| **Backend Host** | `localhost` or `127.0.0.1` |
| **Backend Port** | `8000` |
| **API Base URL** | `http://localhost:8000/api/v1` |
| **Interactive Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **ReDoc API Documentation** | [http://localhost:8000/redoc](http://localhost:8000/redoc) |
| **OpenAPI Specification JSON** | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) |
| **Liveness Check** | [http://localhost:8000/health](http://localhost:8000/health) |
| **Database Readiness Check** | [http://localhost:8000/health/db](http://localhost:8000/health/db) |

---

## Step-by-Step Local Setup

### 1. Prerequisites
- Python 3.10+
- Docker Desktop (for PostgreSQL 15 container)
- Git

### 2. Environment Setup
At the repository root, create your local environment config file:
```bash
cp .env.example .env
```
*(Default environment parameters point to `localhost:5432` PostgreSQL, database `aegis3d`, user `aegis_user`, password `aegis_password`).*

### 3. Start PostgreSQL Database Container
Run Docker Compose from the repository root:
```bash
docker compose up -d postgres
```

### 4. Install Python Virtual Environment & Dependencies
```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\activate

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

### 5. Run Database Migrations
Apply Alembic database migrations to initialize PostgreSQL schema tables (`zones`, `events`, `baselines`, `health_snapshots`, `alerts`, `monitoring_sessions`):
```bash
alembic upgrade head
```

### 6. Start FastAPI Development Server
```bash
uvicorn app.main:app --reload
```
The server will start on `http://127.0.0.1:8000`.

---

## Environment Variables Relevant to Frontend Integration

In your Next.js environment (`frontend/.env.local`), configure the API base URL:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

*Note on CORS*: The backend does not currently have CORS middleware enabled. If calling the backend directly from browser `fetch` in local Next.js client components (`http://localhost:3000`), set up a Next.js rewrite in `frontend/next.config.js` or run Next.js server component fetch calls to bypass browser origin checks:

```js
// frontend/next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ]
  },
}
```

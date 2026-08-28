# ARGO Oceanographic Float Data Backend (SIH Project)

Backend and Data Architecture foundation for the **Smart India Hackathon (SIH)** project processing oceanographic ARGO float datasets.

---

## 🌊 Architecture & Responsibilities (Member 3)

This backend is designed with a **clean, decoupled, 3-tier architecture** that operates 100% independently while being fully prepared for future AI/LLM integration:

- **Web Framework:** FastAPI (async REST API with OpenAPI documentation)
- **ASGI Server:** Uvicorn
- **Database Layer:** PostgreSQL + PostGIS spatial extension
- **ORM & Data Access:** SQLAlchemy 2.0 (Async) + GeoAlchemy2 + asyncpg
- **Migrations:** Alembic (async database migration engine)
- **Data Validation:** Pydantic v2
- **Spatial Computations:** PostGIS geodesic queries (`ST_DWithin`, `ST_Distance`)

---

## 📂 Project Structure

```
SIH-Project/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── floats.py         # GET /floats, GET /floats/{id}, GET /floats/{id}/trajectory
│   │   │   │   ├── health.py         # GET /health
│   │   │   │   ├── measurements.py   # GET /measurements
│   │   │   │   ├── profiles.py       # GET /profiles, GET /profiles/{id}
│   │   │   │   ├── query.py          # POST /query (multi-criteria & AI-ready)
│   │   │   │   ├── spatial.py        # POST /nearest-floats (PostGIS spatial queries)
│   │   │   │   └── statistics.py     # GET /statistics (oceanographic stats)
│   │   │   └── router.py             # Router aggregator
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings (.env configuration)
│   │   └── logging.py                # Structured application logger
│   ├── db/
│   │   ├── base.py                   # SQLAlchemy 2.0 DeclarativeBase
│   │   └── session.py                # Async engine, sessionmaker, and get_db dependency
│   ├── models/                       # SQLAlchemy Database Models (modular, ready for ARGO tables)
│   │   └── __init__.py
│   ├── schemas/                      # Pydantic v2 validation & response models
│   │   ├── common.py                 # Pagination & GeoJSON standards
│   │   ├── floats.py                 # Float & trajectory schemas
│   │   ├── health.py                 # Health status schema
│   │   ├── measurements.py           # Depth & sensor measurement schemas
│   │   ├── profiles.py               # Cycle profile schemas
│   │   ├── query.py                  # Structured query & AI prompt schemas
│   │   ├── spatial.py                # PostGIS nearest-float schemas
│   │   └── statistics.py             # Ocean statistics schemas
│   └── main.py                       # FastAPI application entrypoint & middleware
├── alembic/                          # Alembic async database migration scripts
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/                            # Automated test suite (pytest + httpx)
│   ├── conftest.py
│   ├── test_endpoints.py
│   └── test_health.py
├── .env.example                      # Sample configuration
├── alembic.ini                       # Alembic config
├── docker-compose.yml                # PostgreSQL 16 + PostGIS 3.4 container
├── requirements.txt                  # Python dependencies
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Docker & Docker Desktop (for running PostgreSQL + PostGIS locally)

---

### 2. Environment Setup

Clone and navigate to the project directory:
```bash
cd SIH-Project
```

Create and activate a virtual environment:
* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

Install dependencies:
```bash
pip install -r requirements.txt
```

---

### 3. Start PostgreSQL + PostGIS (Docker)

Start the PostGIS container in the background:
```bash
docker-compose up -d
```

The database container includes:
- **Port:** `5432`
- **Database:** `argo_db`
- **User:** `argo_user`
- **Password:** `argo_password`
- **Extension:** PostGIS 3.4 pre-enabled

---

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

---

### 5. Run Database Migrations (Alembic)

To apply future database migrations once the ARGO dataset schema is defined:
```bash
alembic upgrade head
```

To create a new migration after adding models in `app/models/`:
```bash
alembic revision --autogenerate -m "create_argo_tables"
```

---

### 6. Run the FastAPI Application

Start the development server with hot-reload enabled:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be accessible at:
- **API Base:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc Docs:** `http://localhost:8000/redoc`

---

## 🧪 Running Tests

Run the test suite with `pytest`:
```bash
pytest
```

Run tests with detailed coverage and logs:
```bash
pytest -v -s
```

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Application and database health check |
| `GET` | `/floats` | Paginated list of ARGO oceanographic floats |
| `GET` | `/floats/{id}` | Detailed float metadata by WMO ID |
| `GET` | `/floats/{id}/trajectory` | Float drift and cycle trajectory coordinates |
| `GET` | `/profiles` | List of float cycle profiles |
| `GET` | `/profiles/{id}` | Single profile cycle detail |
| `GET` | `/measurements` | Vertical depth slices (temperature, salinity, pressure) |
| `GET` | `/statistics` | Oceanographic statistics across bounding box & time |
| `POST` | `/nearest-floats` | PostGIS spatial geodesic proximity search |
| `POST` | `/query` | Multi-criteria filter & decoupled AI integration interface |

*Note: All endpoints are also available under the `/api/v1` prefix (e.g., `/api/v1/health`).*

---

## 🧩 Modular Design for Future Schema & AI Integration

1. **ARGO Schema Addition:**
   - When the real dataset format (NetCDF/CSV) is confirmed, define SQLAlchemy models in `app/models/` and Pydantic schemas in `app/schemas/`.
   - Run `alembic revision --autogenerate -m "add_argo_tables"` and `alembic upgrade head`.

2. **AI Layer Integration:**
   - The `/query` endpoint accepts structured filter parameters and an optional `natural_language_prompt` payload.
   - When the AI team builds their NLP/Text-to-SQL or RAG layer, it can consume `/query` or service query builders without altering database access rules or frontend contracts.

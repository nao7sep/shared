# FastAPI Dependencies

This document lists essential packages for FastAPI backend and Python GUI development, with guidance on which to choose.

## Core FastAPI Stack

### Minimal FastAPI Setup

```bash
poetry add fastapi uvicorn pydantic pydantic-settings
```

**What each does**:
- **fastapi**: Web framework
- **uvicorn**: ASGI server (runs FastAPI apps)
- **pydantic**: Data validation (built into FastAPI, but explicit install ensures latest version)
- **pydantic-settings**: Environment variable management

**Run development server**:
```bash
poetry run uvicorn app.main:app --reload
```

### Enhanced FastAPI Setup

```bash
poetry add fastapi "uvicorn[standard]" pydantic pydantic-settings
```

**uvicorn[standard]** includes:
- **watchfiles**: Auto-reload on code changes (faster than default)
- **websockets**: WebSocket support
- **httptools**: Faster HTTP parsing

**Recommendation**: Always use `uvicorn[standard]` for development.

## Database

Choose based on your database type:

### PostgreSQL (Recommended for production)

```bash
# Async driver
poetry add asyncpg

# ORM (optional but recommended)
poetry add sqlalchemy[asyncio] alembic
```

**Connection string**:
```python
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
```

**Why PostgreSQL**:
- Production-ready
- JSON support (great for flexible schemas)
- Excellent Python ecosystem
- Free and open source

### SQLite (Recommended for prototypes)

```bash
# Async driver
poetry add aiosqlite

# ORM (optional)
poetry add sqlalchemy[asyncio] alembic
```

**Connection string**:
```python
DATABASE_URL = "sqlite+aiosqlite:///./test.db"
```

**Why SQLite**:
- No separate database server needed
- Good for development and small projects
- Easy to get started

### MySQL/MariaDB

```bash
# Async driver
poetry add aiomysql

# ORM
poetry add sqlalchemy[asyncio] alembic
```

**Connection string**:
```python
DATABASE_URL = "mysql+aiomysql://user:password@localhost/dbname"
```

### Summary: Which Database Driver?

| Database   | Async Driver | Sync Driver (avoid) | Connection String                     |
|------------|--------------|---------------------|---------------------------------------|
| PostgreSQL | asyncpg      | psycopg2            | postgresql+asyncpg://...              |
| SQLite     | aiosqlite    | sqlite3 (built-in)  | sqlite+aiosqlite:///...               |
| MySQL      | aiomysql     | pymysql             | mysql+aiomysql://...                  |

**Always use async drivers with FastAPI.**

## ORM and Migrations

### SQLAlchemy 2.0 (Recommended)

```bash
poetry add sqlalchemy[asyncio]
```

**Why**:
- Industry standard ORM
- Excellent type hints
- Async support in 2.0+
- Great FastAPI integration

**Basic usage**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = create_async_engine("postgresql+asyncpg://localhost/test")

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
```

### Alembic (Database Migrations)

```bash
poetry add alembic
```

**Why**: Track database schema changes over time (like Entity Framework migrations).

**Initialize**:
```bash
poetry run alembic init alembic
```

**Create migration**:
```bash
poetry run alembic revision --autogenerate -m "Add user table"
```

**Apply migration**:
```bash
poetry run alembic upgrade head
```

## Authentication

### JWT Authentication

```bash
poetry add python-jose[cryptography] passlib[bcrypt] python-multipart
```

**What each does**:
- **python-jose**: JWT token creation/verification
- **passlib[bcrypt]**: Password hashing with bcrypt
- **python-multipart**: Form data parsing (for login forms)

**Basic usage**:
```python
from passlib.context import CryptContext
from jose import jwt

pwd_context = CryptContext(schemes=["bcrypt"])

# Hash password
hashed = pwd_context.hash("my-password")

# Verify password
is_valid = pwd_context.verify("my-password", hashed)

# Create JWT token
token = jwt.encode({"sub": user.email}, SECRET_KEY, algorithm="HS256")

# Decode JWT token
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

### OAuth2 (For third-party login)

```bash
poetry add authlib httpx
```

**Use when**: Implementing "Login with Google/GitHub/etc."

## HTTP Client (For calling external APIs)

```bash
# Async (recommended)
poetry add httpx

# Sync (if you must)
poetry add requests
```

**Usage**:
```python
import httpx

# In async endpoint
async def fetch_external_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

## Validation and Serialization

**Already included in FastAPI via Pydantic**, but useful to know:

```bash
# If you need email validation
poetry add pydantic[email]

# If you need advanced validation
poetry add pydantic-extra-types
```

## CORS (For frontend integration)

**Already included in FastAPI**, just configure:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Environment Variables

```bash
poetry add pydantic-settings python-dotenv
```

**Usage**:
```python
# .env file
DATABASE_URL=postgresql://localhost/test
SECRET_KEY=your-secret-key

# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## Testing

```bash
poetry add -G dev pytest pytest-asyncio httpx
```

**What each does**:
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **httpx**: Test FastAPI endpoints (async client)

**Usage**:
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/users", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 201
```

## Code Quality Tools

```bash
poetry add -G dev black ruff mypy
```

**What each does**:
- **black**: Code formatter (like Prettier for Python)
- **ruff**: Fast linter (replaces flake8, isort, etc.)
- **mypy**: Static type checker

**Usage**:
```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy app/
```

## Background Tasks

### Celery (For complex workflows)

```bash
poetry add celery redis
```

**Use when**:
- Long-running tasks (email sending, data processing)
- Scheduled tasks (cron jobs)
- Distributed task queue

### FastAPI BackgroundTasks (For simple tasks)

**Already included in FastAPI**, no install needed:

```python
from fastapi import BackgroundTasks

def send_email(to: str):
    # Send email logic
    pass

@app.post("/register")
async def register(background_tasks: BackgroundTasks):
    # Register user
    background_tasks.add_task(send_email, "user@example.com")
    return {"message": "Registered"}
```

**Use when**: Simple tasks that can run in the same process.

## Caching

### Redis

```bash
poetry add redis[hiredis]
```

**Usage**:
```python
import redis.asyncio as redis

r = await redis.from_url("redis://localhost")
await r.set("key", "value")
value = await r.get("key")
```

**Use when**: Need caching, session storage, or pub/sub.

## WebSockets

**Already included in FastAPI** (if using uvicorn[standard]):

```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

## File Uploads

**Already handled by FastAPI**:

```python
from fastapi import UploadFile

@app.post("/upload")
async def upload_file(file: UploadFile):
    contents = await file.read()
    # Process file
    return {"filename": file.filename}
```

**For async file I/O**:
```bash
poetry add aiofiles
```

## Python GUI Development

If building desktop GUI apps (not FastAPI):

### PyQt6 (Most Popular)

```bash
poetry add PyQt6
```

**Pros**: Rich widgets, mature, good documentation
**Cons**: LGPL license (commercial apps need license)

**Usage**:
```python
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton

app = QApplication([])
window = QMainWindow()
button = QPushButton("Click Me")
window.setCentralWidget(button)
window.show()
app.exec()
```

### PySide6 (Official Qt Binding)

```bash
poetry add PySide6
```

**Pros**: Official Qt binding, LGPL license (more permissive)
**Cons**: Similar to PyQt6

**Usage**: Nearly identical to PyQt6 (just import from PySide6 instead of PyQt6).

### Tkinter (Built-in)

**No install needed** (included with Python):

```python
import tkinter as tk

root = tk.Tk()
button = tk.Button(root, text="Click Me")
button.pack()
root.mainloop()
```

**Pros**: No dependencies, simple
**Cons**: Looks dated, limited widgets

### Kivy (Cross-platform, Mobile Support)

```bash
poetry add kivy
```

**Pros**: Runs on desktop + mobile (Android, iOS)
**Cons**: Different paradigm, less conventional

### Dear PyGui (Modern, Fast)

```bash
poetry add dearpygui
```

**Pros**: Fast, modern, immediate mode GUI
**Cons**: Smaller community

## Complete FastAPI Project Setup

**Minimal** (getting started):
```bash
poetry add fastapi "uvicorn[standard]" pydantic pydantic-settings
poetry add -G dev pytest pytest-asyncio httpx black ruff
```

**Standard** (with database):
```bash
poetry add fastapi "uvicorn[standard]" pydantic pydantic-settings
poetry add sqlalchemy[asyncio] alembic asyncpg  # or aiosqlite
poetry add python-jose[cryptography] passlib[bcrypt] python-multipart
poetry add -G dev pytest pytest-asyncio httpx black ruff mypy
```

**Full-featured** (production-ready):
```bash
# Core
poetry add fastapi "uvicorn[standard]" pydantic pydantic-settings

# Database
poetry add sqlalchemy[asyncio] alembic asyncpg

# Auth
poetry add python-jose[cryptography] passlib[bcrypt] python-multipart

# HTTP client
poetry add httpx

# Caching
poetry add redis[hiredis]

# Background tasks
poetry add celery

# Environment
poetry add python-dotenv

# Dev tools
poetry add -G dev pytest pytest-asyncio httpx black ruff mypy
```

## Dependency Checklist

Use this when starting a new FastAPI project:

**Core**:
- [ ] fastapi
- [ ] uvicorn[standard]
- [ ] pydantic
- [ ] pydantic-settings

**Database** (choose one):
- [ ] PostgreSQL: asyncpg + sqlalchemy[asyncio] + alembic
- [ ] SQLite: aiosqlite + sqlalchemy[asyncio] + alembic

**Authentication**:
- [ ] python-jose[cryptography]
- [ ] passlib[bcrypt]
- [ ] python-multipart

**Testing**:
- [ ] pytest
- [ ] pytest-asyncio
- [ ] httpx (for testing)

**Code Quality**:
- [ ] black
- [ ] ruff
- [ ] mypy

**Optional**:
- [ ] httpx (external API calls)
- [ ] redis (caching)
- [ ] celery (background tasks)
- [ ] aiofiles (async file I/O)

## Summary

**Always install**:
- FastAPI core: `fastapi`, `uvicorn[standard]`, `pydantic`
- Testing: `pytest`, `pytest-asyncio`, `httpx`
- Code quality: `black`, `ruff`

**Install based on needs**:
- Database: Choose async driver (asyncpg, aiosqlite) + SQLAlchemy + Alembic
- Auth: `python-jose`, `passlib`
- External APIs: `httpx`
- Caching: `redis`
- GUI: `PyQt6`, `PySide6`, `tkinter`, `kivy`, or `dearpygui`

**Version constraints**: Use `^` for most packages, exact versions only when needed.

**Remember**: Always use async libraries (asyncpg, httpx, aiosqlite) for FastAPI to avoid blocking the event loop.

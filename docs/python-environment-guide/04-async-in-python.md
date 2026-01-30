# Async in Python

## Why Async Matters for FastAPI

FastAPI is built on async Python. Understanding async vs sync affects:
- **Which libraries you choose** (asyncpg vs psycopg2, httpx vs requests)
- **How you write code** (async/await syntax)
- **Performance** (async allows concurrent I/O operations)

## Async vs Sync: The Key Difference

**Sync (blocking)**:
```python
import time

def fetch_data():
    time.sleep(1)  # Simulates I/O (database, API call)
    return "data"

def main():
    data1 = fetch_data()  # Waits 1 second
    data2 = fetch_data()  # Waits 1 second
    data3 = fetch_data()  # Waits 1 second
    # Total: 3 seconds

main()
```

**Async (non-blocking)**:
```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)  # Simulates I/O
    return "data"

async def main():
    data1, data2, data3 = await asyncio.gather(
        fetch_data(),
        fetch_data(),
        fetch_data()
    )
    # Total: 1 second (runs concurrently)

asyncio.run(main())
```

**Key insight**: Async doesn't make each operation faster, but allows many operations to run concurrently while waiting for I/O.

## Coming from C#

If you know C# async/await, Python's async is similar but with differences:

**C#**:
```csharp
public async Task<string> FetchDataAsync()
{
    await Task.Delay(1000);
    return "data";
}

public async Task Main()
{
    var data = await FetchDataAsync();
}
```

**Python**:
```python
async def fetch_data():
    await asyncio.sleep(1)
    return "data"

async def main():
    data = await fetch_data()

asyncio.run(main())
```

**Similarities**:
- `async` keyword to define async function
- `await` keyword to wait for async operation
- Can't use `await` outside async function

**Differences**:
- Python uses `async def` (not return type annotation)
- Python's `asyncio.run()` vs C#'s runtime handling
- Python's async is single-threaded by default (event loop)

## When to Use Async vs Sync

**Use async when**:
- Building web APIs (FastAPI)
- Making I/O calls (database, HTTP requests, file I/O)
- You need to handle many concurrent operations
- Using libraries that support async (asyncpg, httpx)

**Use sync when**:
- Writing scripts that run sequentially
- CPU-bound tasks (calculations, data processing)
- Library doesn't support async
- Simplicity matters more than concurrency

**For FastAPI**: Use async endpoints when doing I/O, sync endpoints for CPU work or when using sync libraries.

## Async Libraries vs Sync Libraries

Many Python libraries have both sync and async versions:

### Database Drivers

**PostgreSQL**:
```python
# Sync (psycopg2)
import psycopg2
conn = psycopg2.connect("dbname=test")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users")
results = cursor.fetchall()  # Blocks until data arrives

# Async (asyncpg)
import asyncpg
conn = await asyncpg.connect("postgresql://localhost/test")
results = await conn.fetch("SELECT * FROM users")  # Non-blocking
```

**SQLite**:
```python
# Sync (sqlite3 - built-in)
import sqlite3
conn = sqlite3.connect("test.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users")
results = cursor.fetchall()

# Async (aiosqlite)
import aiosqlite
async with aiosqlite.connect("test.db") as conn:
    async with conn.execute("SELECT * FROM users") as cursor:
        results = await cursor.fetchall()
```

### HTTP Clients

```python
# Sync (requests)
import requests
response = requests.get("https://api.example.com/data")
data = response.json()  # Blocks until response arrives

# Async (httpx)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/data")
    data = response.json()  # Non-blocking
```

### Redis

```python
# Sync
import redis
r = redis.Redis(host='localhost', port=6379)
value = r.get('key')

# Async
import redis.asyncio as redis
r = await redis.from_url("redis://localhost")
value = await r.get('key')
```

## Choosing Libraries for FastAPI

**Principle**: Use async libraries when available for better performance.

### Database (Use async)

```bash
# PostgreSQL - Use asyncpg (NOT psycopg2)
poetry add asyncpg

# SQLite - Use aiosqlite (NOT sqlite3)
poetry add aiosqlite

# ORM - SQLAlchemy 2.0 with async mode
poetry add sqlalchemy[asyncio]
```

**Why**: FastAPI is async. Using sync database drivers blocks the event loop, reducing performance.

### HTTP Clients (Use async)

```bash
# Use httpx (NOT requests)
poetry add httpx
```

**Why**: If your FastAPI endpoint calls external APIs, async HTTP clients allow concurrent requests.

### File I/O (Usually sync is fine)

```bash
# For async file I/O (optional)
poetry add aiofiles
```

**When to use**: If you're reading/writing many large files concurrently. Otherwise, sync file I/O is acceptable.

## FastAPI Async Endpoints

FastAPI supports both async and sync endpoints:

**Async endpoint** (recommended for I/O):
```python
from fastapi import FastAPI
import asyncpg

app = FastAPI()

@app.get("/users")
async def get_users():
    conn = await asyncpg.connect("postgresql://localhost/test")
    users = await conn.fetch("SELECT * FROM users")
    await conn.close()
    return users
```

**Sync endpoint** (for sync libraries or CPU work):
```python
@app.get("/calculate")
def calculate_fibonacci(n: int):
    # CPU-bound work, no I/O
    def fib(n):
        if n <= 1:
            return n
        return fib(n-1) + fib(n-2)

    result = fib(n)
    return {"result": result}
```

**Mixing async and sync**:
```python
@app.get("/data")
async def get_data():
    # Async database call
    users = await fetch_users_from_db()

    # Can't directly call sync function in async context
    # Use run_in_executor for CPU-bound work
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, expensive_calculation, users)

    return result
```

## SQLAlchemy with Async

SQLAlchemy 2.0 supports async:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Create async engine
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/dbname",
    echo=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Use in FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
```

**Note**: Connection string must specify async driver:
- PostgreSQL: `postgresql+asyncpg://...`
- SQLite: `sqlite+aiosqlite:///...`

## Common Pitfalls

### Pitfall 1: Calling Async Function Without await

```python
# WRONG
async def fetch_data():
    return "data"

def main():
    result = fetch_data()  # Returns coroutine object, not "data"
    print(result)  # Prints: <coroutine object fetch_data at 0x...>

# CORRECT
async def main():
    result = await fetch_data()
    print(result)  # Prints: data
```

### Pitfall 2: Using Sync Library in Async Code

```python
# WRONG - Blocks event loop
import requests

@app.get("/external-data")
async def get_external_data():
    response = requests.get("https://api.example.com/data")  # Blocks!
    return response.json()

# CORRECT - Use async HTTP client
import httpx

@app.get("/external-data")
async def get_external_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

### Pitfall 3: Forgetting async in FastAPI Endpoint

```python
# WRONG - Can't use await in sync function
@app.get("/users")
def get_users():
    users = await fetch_users()  # SyntaxError!
    return users

# CORRECT
@app.get("/users")
async def get_users():
    users = await fetch_users()
    return users
```

### Pitfall 4: Not Closing Async Resources

```python
# WRONG - Connection leak
async def get_data():
    conn = await asyncpg.connect("postgresql://localhost/test")
    data = await conn.fetch("SELECT * FROM users")
    return data  # Connection never closed!

# CORRECT - Use context manager
async def get_data():
    async with asyncpg.create_pool("postgresql://localhost/test") as pool:
        async with pool.acquire() as conn:
            data = await conn.fetch("SELECT * FROM users")
            return data  # Connection auto-closed
```

## Testing Async Code

Use pytest with pytest-asyncio:

```bash
poetry add -G dev pytest pytest-asyncio httpx
```

**Test async functions**:
```python
import pytest

@pytest.mark.asyncio
async def test_fetch_data():
    data = await fetch_data()
    assert data == "expected value"
```

**Test FastAPI endpoints**:
```python
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_users():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/users")
        assert response.status_code == 200
```

## Performance Comparison

**Sync endpoint with sync database** (baseline):
```python
@app.get("/users")
def get_users():
    # Each request blocks thread until DB responds
    # 10 concurrent requests = 10x response time
    users = sync_db.query(User).all()
    return users
```

**Async endpoint with async database** (better):
```python
@app.get("/users")
async def get_users():
    # 10 concurrent requests can wait for DB concurrently
    # 10 concurrent requests ≈ 1x response time (if I/O bound)
    users = await async_db.execute(select(User))
    return users.scalars().all()
```

**When async doesn't help**:
- CPU-bound tasks (calculations, data processing)
- No I/O operations
- Single request at a time

## Summary

**Async in Python**:
- Use `async def` to define async functions
- Use `await` to call async functions
- Single-threaded event loop (not multi-threading)
- Allows concurrent I/O operations

**For FastAPI development**:
- Use async endpoints when doing I/O
- Use async libraries (asyncpg, httpx, aiosqlite)
- Use SQLAlchemy with async mode
- Test with pytest-asyncio

**Key principle**: Async makes I/O operations concurrent, not faster individually. Use it when you have many I/O operations happening at once.

**Rule of thumb**:
- Building FastAPI app → Use async
- Database calls → Use async driver
- External API calls → Use async HTTP client (httpx)
- File I/O → Use async if handling many files, sync otherwise
- CPU-heavy work → Use sync, or run_in_executor

Next: Learn which dependencies to install in 05-fastapi-dependencies.md

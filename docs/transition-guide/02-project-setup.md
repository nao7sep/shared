# New Project Setup: FastAPI + React/TypeScript

This document covers starting a new FastAPI backend + React/TypeScript frontend project from scratch.

## Project Structure

Create this exact structure:

```
project-name/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app instance, startup/shutdown
│   │   ├── api/                 # HTTP layer
│   │   │   ├── __init__.py
│   │   │   └── v1/              # Versioned routes
│   │   │       ├── __init__.py
│   │   │       ├── router.py    # Aggregates all endpoints
│   │   │       └── endpoints/   # Individual route files
│   │   │           ├── __init__.py
│   │   │           ├── auth.py
│   │   │           └── users.py
│   │   ├── core/                # Cross-cutting concerns
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Settings, environment vars
│   │   │   ├── security.py      # Auth, password hashing
│   │   │   └── deps.py          # Shared dependencies
│   │   ├── models/              # Database models (SQLAlchemy)
│   │   │   ├── __init__.py
│   │   │   └── user.py
│   │   ├── schemas/             # Pydantic models (request/response)
│   │   │   ├── __init__.py
│   │   │   └── user.py
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   └── user_service.py
│   │   └── db/                  # Database concerns
│   │       ├── __init__.py
│   │       ├── base.py          # Base class for models
│   │       └── session.py       # Database session management
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Pytest fixtures
│   │   └── api/
│   │       └── v1/
│   │           └── test_auth.py
│   ├── alembic/                 # Database migrations
│   ├── pyproject.toml           # Dependencies (use this, not requirements.txt)
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── api/                 # API client code
│   │   │   ├── client.ts        # Axios/fetch setup
│   │   │   └── auth.ts          # Auth endpoints
│   │   ├── components/          # Reusable components
│   │   │   └── common/
│   │   ├── hooks/               # Custom React hooks
│   │   │   └── useAuth.ts
│   │   ├── pages/               # Page-level components
│   │   │   ├── Login.tsx
│   │   │   └── Dashboard.tsx
│   │   ├── types/               # TypeScript type definitions
│   │   │   └── api.ts           # Generated from backend
│   │   ├── utils/               # Utility functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts           # Or webpack/Next.js config
│   └── .env.example
│
├── docs/                        # Project documentation
│   ├── decisions.md             # Architectural decision record
│   ├── entities.md              # Domain entities
│   └── api.md                   # API contract
│
├── .gitignore
└── README.md
```

## Phase 1: Decisions (Make These NOW)

Before writing any code, decide these. Document in `docs/decisions.md`.

### 1. Authentication Method
**Options**: JWT, OAuth2, session-based
**Recommendation**: JWT with httpOnly cookies
**Rationale**: Secure (httpOnly prevents XSS), stateless, FastAPI has excellent support

### 2. Database
**Options**: PostgreSQL, MySQL, SQLite
**Recommendation**: PostgreSQL (use Postgres.app on Mac)
**Rationale**: Production-ready, excellent Python support, JSON support

### 3. ORM
**Options**: SQLAlchemy, Tortoise ORM, raw SQL
**Recommendation**: SQLAlchemy 2.0
**Rationale**: Industry standard, async support, good type hints

### 4. Frontend State Management
**Options**: Redux, Zustand, Jotai, React Context
**Recommendation**: React Query + Zustand
**Rationale**: React Query for server state (caching, refetching), Zustand for client state (UI state, user preferences). Less boilerplate than Redux.

### 5. Styling
**Options**: Tailwind CSS, CSS Modules, styled-components, MUI
**Recommendation**: Tailwind CSS
**Rationale**: Fast development, composable, no CSS file management

### 6. Frontend Framework Details
**Options**: Vite, Create React App, Next.js
**Recommendation**: Vite
**Rationale**: Fast, modern, simple for SPAs. Use Next.js only if you need SSR.

## Phase 2: Document First

Before implementing, document your domain and API.

### docs/entities.md

```markdown
# Core Entities

## User
- id: UUID (primary key)
- email: string (unique, indexed)
- hashed_password: string
- name: string
- is_active: boolean (default: true)
- created_at: datetime
- updated_at: datetime

## Product
- id: UUID (primary key)
- name: string
- description: text (nullable)
- price: decimal(10, 2)
- owner_id: UUID (foreign key → User.id)
- created_at: datetime
- updated_at: datetime
```

### docs/api.md

```markdown
# API Contract

Base URL: `/api/v1`

## Authentication

### POST /auth/register
**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response** (201):
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe"
  },
  "access_token": "jwt-token"
}
```

**Errors**:
- 400: Invalid email format
- 409: Email already registered

### POST /auth/login
**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response** (200):
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

## Products

### GET /products
**Query params**:
- `page`: int (default: 1)
- `limit`: int (default: 20, max: 100)
- `owner_id`: UUID (optional)

**Response** (200):
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Product Name",
      "price": 29.99,
      "owner_id": "uuid"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20
}
```
```

### docs/decisions.md

```markdown
# Architectural Decisions

## Authentication: JWT with httpOnly cookies
**Decided**: 2026-01-30
**Rationale**: Secure (XSS protection), stateless, good FastAPI support
**Alternatives considered**: Session-based (requires session store), OAuth2 (too complex for MVP)

## Database: PostgreSQL + SQLAlchemy 2.0
**Decided**: 2026-01-30
**Rationale**: Production-ready, async support, type safety
**Alternatives considered**: SQLite (not production-ready), raw SQL (too much boilerplate)

## Frontend: React Query + Zustand
**Decided**: 2026-01-30
**Rationale**: React Query handles server state elegantly, Zustand for simple client state
**Alternatives considered**: Redux (too much boilerplate)
```

## Phase 3: Backend Implementation

### Step 1: Initialize Project

```bash
cd backend
# Use poetry or pdm (modern alternatives to pip)
poetry init
poetry add fastapi uvicorn sqlalchemy alembic pydantic-settings python-jose passlib bcrypt
poetry add --group dev pytest httpx black ruff
```

### Step 2: Tell AI to Implement

**Instruction template**:
```
Set up the FastAPI project structure according to docs/entities.md and docs/api.md.

Requirements:
1. Implement User model with SQLAlchemy
2. Implement Pydantic schemas for User (create, response)
3. Implement user registration endpoint at POST /api/v1/auth/register
4. Use bcrypt for password hashing
5. Return JWT token on successful registration
6. Use dependency injection for database session

Follow these patterns:
- Separate routes (api/), business logic (services/), and data access (models/)
- Use Pydantic Settings for configuration
- Add proper error handling with HTTPException
```

### Step 3: Review AI Output

Check for:
- **Security**: Passwords hashed, not plain text? No SQL injection? Input validation?
- **Error handling**: Are errors informative but not leaking sensitive info?
- **Follows spec**: Does it match docs/api.md?
- **Separation of concerns**: Routes → Services → Database?

### Step 4: Iterate

```
Add email validation to ensure lowercase and valid format.
Add rate limiting to prevent abuse.
Add tests for the registration endpoint.
```

## Phase 4: Frontend Implementation

### Step 1: Generate TypeScript Types

**Option A**: Use FastAPI's OpenAPI schema
```bash
# Install openapi-typescript
npm install --save-dev openapi-typescript

# Generate types
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

**Option B**: Use pydantic-to-typescript
```bash
# In backend
poetry add --group dev pydantic-to-typescript
pydantic2ts --module app.schemas --output ../frontend/src/types/api.ts
```

### Step 2: Tell AI to Implement

```
Create a React registration form component.

Requirements:
1. Use the User and UserCreate types from src/types/api.ts
2. Create a React Query mutation for registration
3. Form validation: email format, password min 8 chars
4. Show loading state during submission
5. Show error messages from API
6. On success, redirect to dashboard

Use Tailwind CSS for styling.
```

### Step 3: Review

Check for:
- **Type safety**: Using generated types from backend?
- **Error handling**: Network errors handled? API errors displayed?
- **UX**: Loading states? Disabled submit during loading?
- **Accessibility**: Labels, error announcements?

## What Can Wait

Don't implement these in the initial setup:

- **Caching strategy**: Add when you have performance data
- **Background jobs**: Add when you need async processing
- **Websockets/real-time**: Add when you have real-time features
- **Comprehensive logging**: Basic logging is fine initially
- **Monitoring/metrics**: Add before production, not during development
- **Docker setup**: Add when you need deployment
- **CI/CD**: Add when you have tests and deployment target
- **Advanced optimization**: Add when you measure bottlenecks

## Workflow Summary

For each feature:

1. **Document** in docs/entities.md or docs/api.md
2. **Backend**: Tell AI to implement according to docs
3. **Review** for security, correctness, fit
4. **Generate types** for frontend
5. **Frontend**: Tell AI to implement using types
6. **Review** for type safety, UX, error handling
7. **Test** manually or with automated tests
8. **Commit** when feature works

## Common Pitfalls

### Pitfall 1: Starting Without Decisions
**Problem**: Changing auth method mid-development
**Solution**: Make core decisions before writing code

### Pitfall 2: No API Contract
**Problem**: Frontend and backend diverge
**Solution**: Write API contract in docs/api.md first

### Pitfall 3: Manual Type Syncing
**Problem**: TypeScript types don't match Pydantic models
**Solution**: Generate types from backend automatically

### Pitfall 4: Over-Engineering Initially
**Problem**: Adding features "you might need"
**Solution**: Implement only what's in the spec. Add more when needed.

## Next Steps

After initial setup:
1. Implement one complete feature (auth registration)
2. Test end-to-end
3. Document any patterns you want to reuse in `~/code/shared/guidelines/`
4. Use this project as a template for future projects

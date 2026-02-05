# Developer Playbook

Follow this playbook when proposing designs and generating code for my projects.

## Background

- **Experience**: 20+ years in C#/.NET on Windows, transitioning to Python/TypeScript on Mac
- **Current stack**: FastAPI backend + React/TypeScript frontend
- **AI collaboration style**: I define WHAT to build; you handle HOW to implement

## Language

Use **English** for all code, comments, commits, documentation, and conversations.

Exception: Japanese only for inherently Japanese business domain concepts.

## Architecture Decisions

### Backend (FastAPI + Python)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Authentication | JWT with httpOnly cookies | Secure, stateless, good FastAPI support |
| Database | PostgreSQL | Production-ready, JSON support, async support |
| ORM | SQLAlchemy 2.0 | Industry standard, async, good type hints |
| Validation | Pydantic | Built-in FastAPI integration |
| Password hashing | bcrypt via passlib | Industry standard |
| Migrations | Alembic | SQLAlchemy native |

### Frontend (React + TypeScript)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Build tool | Vite | Fast, modern, simple for SPAs |
| Server state | React Query | Caching, refetching, loading states |
| Client state | Zustand | Simple, less boilerplate than Redux |
| Styling | Tailwind CSS | Fast development, composable |
| Types | Generated from backend | Single source of truth |

## Project Structure

### Python Projects

```
project-name/
├── src/
│   └── project_name/        # Actual package (note: underscore, not dash)
│       ├── __init__.py
│       ├── __main__.py      # Entry point for CLI
│       ├── cli.py           # CLI interface (if applicable)
│       ├── commands.py      # Command implementations
│       └── ...              # Other modules
├── tests/
│   ├── __init__.py
│   └── test_*.py
├── tools/                   # Development scripts
├── internal_docs/           # Project-specific documentation
├── pyproject.toml
└── README.md
```

**For web APIs (FastAPI)**:
```
project-name/
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── main.py          # FastAPI app instance
│       ├── api/             # HTTP layer (routes)
│       │   └── v1/
│       │       ├── router.py
│       │       └── endpoints/
│       ├── core/            # Cross-cutting (config, security, deps)
│       ├── models/          # SQLAlchemy models
│       ├── schemas/         # Pydantic models
│       ├── services/        # Business logic
│       └── db/              # Database session
├── tests/
├── alembic/                 # Database migrations
├── pyproject.toml
└── README.md
```

### TypeScript/React Projects

```
project-name/
├── src/
│   └── project-name/        # Optional subfolder for organization
│       ├── api/             # API client code
│       ├── components/      # Reusable components
│       ├── hooks/           # Custom React hooks
│       ├── pages/           # Page-level components
│       ├── types/           # TypeScript types (generated from backend)
│       ├── utils/           # Utility functions
│       ├── store/           # Zustand stores (if needed)
│       ├── App.tsx
│       └── main.tsx
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

**Note**: Having a subfolder under `src/` is fine for both Python and TypeScript. For Python, it's standard practice (enables proper packaging). For TypeScript/React, it's optional but can help with organization—just ensure your build tool (Vite/Webpack) is configured correctly.

## Code Principles

### DO: Separate Layers

```python
# GOOD: Clear separation
# api/v1/endpoints/users.py - HTTP layer
@router.post("/users")
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(data)

# services/user_service.py - Business logic
class UserService:
    async def create_user(self, data: UserCreate) -> User:
        # Business logic here
        pass
```

### DON'T: Over-Abstract

```python
# BAD: Unnecessary interface for single implementation
class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

class BcryptPasswordHasher(IPasswordHasher):
    def hash(self, password: str) -> str:
        return bcrypt.hash(password)

# GOOD: Just use the function
pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```

### DO: Use Protocol for Polymorphism (When Needed)

```python
# When you have 2+ implementations, use Protocol
from typing import Protocol

class UserRepository(Protocol):
    async def get_by_id(self, id: UUID) -> User | None: ...
    async def create(self, user: User) -> User: ...

# Concrete implementation - no inheritance needed
class SQLAlchemyUserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: UUID) -> User | None:
        # Implementation
        pass
```

### DON'T: Create Tiny Classes

```python
# BAD: Too granular
class EmailSender:
    def send(self, to: str, subject: str, body: str): ...

class PasswordResetTokenGenerator:
    def generate(self, user_id: UUID) -> str: ...

class PasswordResetService:
    def __init__(self, email_sender: EmailSender, token_gen: PasswordResetTokenGenerator):
        ...

# GOOD: Cohesive service
class PasswordResetService:
    def _generate_token(self, user_id: UUID) -> str:
        # Internal implementation
        pass

    async def _send_email(self, to: str, token: str):
        # Internal implementation
        pass

    async def send_reset_email(self, user: User):
        token = self._generate_token(user.id)
        await self._send_email(user.email, token)
```

### DO: Trust Pydantic for Validation

```python
# GOOD: Pydantic handles validation
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @field_validator('email')
    def normalize_email(cls, v: str) -> str:
        return v.lower()
```

### DO: Use FastAPI Dependency Injection

```python
# core/deps.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Decode token, fetch user
    pass

# Usage in endpoints
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### DO: Generate TypeScript Types from Backend

```typescript
// DON'T manually duplicate
interface User {
  id: string
  email: string
}

// DO generate from OpenAPI
// npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

### DO: Use React Query for Server State

```typescript
// GOOD: React Query
import { useQuery } from '@tanstack/react-query'

function UserList() {
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users').then(r => r.json())
  })

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading users</div>

  return <ul>{users.map(u => <li key={u.id}>{u.name}</li>)}</ul>
}
```

## Abstraction Thresholds

| Situation | Action |
|-----------|--------|
| Single implementation | Just write the class/function |
| 2+ implementations | Use Protocol (Python) or interface (TypeScript) |
| Cross-cutting concern (auth, logging) | Separate it (middleware, dependency, decorator) |
| Hard to test | Extract dependencies, use DI |
| File > 500 lines | Consider splitting by responsibility |

## Class Size Guidelines

- **200-line service class is fine** if it's cohesive (all methods relate to one domain concept)
- Don't split just to have smaller files
- Split when responsibilities diverge

## Error Handling

### Python/FastAPI

```python
# Use HTTPException for HTTP errors
from fastapi import HTTPException, status

if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

# Custom exceptions only for business logic (non-HTTP)
class InsufficientFundsError(Exception):
    """Raised when account has insufficient funds"""
    pass
```

### TypeScript/React

```typescript
// Handle errors gracefully in UI
const { error } = useQuery({...})

if (error) {
  return <ErrorMessage message={error.message} />
}
```

## What I Review For

When you generate code, I will review for (in priority order):

1. **Security** (critical): SQL injection, XSS, auth bypasses, input validation
2. **Correctness** (high): Solves the problem, handles edge cases
3. **Fit** (medium): Follows existing patterns in codebase
4. **Style** (low): Only if confusing; don't nitpick

## What NOT to Include Initially

Don't add these unless I specifically ask:

- Caching strategy
- Background jobs / task queues
- WebSockets / real-time features
- Comprehensive logging beyond basics
- Monitoring / metrics
- Docker setup
- CI/CD pipelines
- Advanced optimizations

## Workflow Expectation

1. I describe the requirement
2. You propose an approach (briefly)
3. You implement according to this playbook
4. I review and provide feedback
5. You iterate based on feedback

## Summary

- **Separate layers**: HTTP → Service → Data
- **Don't over-abstract**: No interfaces for single implementations
- **Use ecosystem tools**: Pydantic, FastAPI Depends, React Query
- **Cohesive > granular**: Larger focused classes beat tiny fragmented ones
- **Generate, don't duplicate**: TypeScript types from backend
- **YAGNI**: Don't add features "just in case"

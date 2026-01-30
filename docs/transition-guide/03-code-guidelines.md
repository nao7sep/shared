# Code Guidelines: C# Principles in Python/TypeScript

This document helps you balance SOLID principles and separation of concerns from C# with Python and TypeScript idioms.

## The Core Challenge

Your C# instincts are **mostly correct**, but Python and TypeScript have different trade-offs:

- **C#**: Explicit interfaces, dependency injection frameworks, compile-time guarantees
- **Python**: Duck typing, runtime flexibility, "we're all adults here"
- **TypeScript**: Structural typing, gradual typing, JavaScript runtime

The goal: Write maintainable, testable code that doesn't violate the idioms of each language.

## The Five Balance Rules

### Rule 1: Do Separate Layers, Don't Over-Abstract Within Them

**DO separate**: HTTP → Business Logic → Data Access

```python
# GOOD: Clear layer separation
# api/v1/endpoints/users.py
@router.post("/users")
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(data)

# services/user_service.py
class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, data: UserCreate) -> User:
        # Business logic here
        hashed_password = hash_password(data.password)
        user = User(email=data.email, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.commit()
        return user
```

**DON'T over-abstract** within layers:

```python
# BAD: Unnecessary abstraction
class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

class BcryptPasswordHasher(IPasswordHasher):
    def hash(self, password: str) -> str:
        return bcrypt.hash(password)

# GOOD: Just use the function
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```

**Why**: You don't have multiple password hashing implementations. Don't create an interface for a single implementation.

### Rule 2: Use Protocols for Polymorphism, Not ABC

**C# brain says**: "Create an interface for testability!"

**Python says**: "Use Protocol for type hints, duck typing for runtime."

```python
# Instead of this (too C#-ish):
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

class UserRepository(IUserRepository):
    async def get_by_id(self, id: UUID) -> User | None:
        # Implementation
        pass

# Do this (Pythonic):
from typing import Protocol

class UserRepository(Protocol):
    async def get_by_id(self, id: UUID) -> User | None: ...
    async def create(self, user: User) -> User: ...

# Concrete implementation doesn't need inheritance
class SQLAlchemyUserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        return user
```

**When to use Protocol**:
- You have 2+ implementations (e.g., SQLAlchemyRepo, InMemoryRepo for testing)
- You want static type checking without inheritance
- You're writing a library

**When NOT to use Protocol**:
- Single implementation (just write the class)
- Simple functions (no need for objects)

### Rule 3: Trust Pydantic for Validation, Not Custom Classes

**C# brain**: "Create a validator class with rules!"

**Python with Pydantic**: Use built-in validators.

```python
# Instead of this:
class UserValidator:
    def validate_email(self, email: str) -> tuple[bool, str]:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return False, "Invalid email format"
        return True, ""

    def validate_password(self, password: str) -> tuple[bool, str]:
        if len(password) < 8:
            return False, "Password too short"
        return True, ""

# Do this:
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    email: EmailStr  # Built-in email validation
    password: str
    name: str

    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @field_validator('email')
    def normalize_email(cls, v: str) -> str:
        return v.lower()  # Ensure lowercase
```

**Benefits**:
- Validation happens automatically on instantiation
- Serialization/deserialization is free
- FastAPI integrates seamlessly
- Type hints are documentation

### Rule 4: Service Classes Are Fine, But Keep Them Focused

**Good service class** (focused, clear responsibility):

```python
class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, data: UserCreate) -> User:
        # Check if user exists
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")

        # Create user
        hashed_password = hash_password(data.password)
        user = User(
            email=data.email,
            hashed_password=hashed_password,
            name=data.name
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user
```

**Signs of over-engineering**:
- Service has only one method (just make it a function)
- Service delegates to another service that delegates to another service
- Service is just a thin wrapper around repository (merge them)

**200-line service class is fine** if it's cohesive (all methods relate to one domain concept).

### Rule 5: Separate Concerns, But Don't Create Tiny Classes

**C# background**: SRP means "every class does one thing."

**Python interpretation**: Every *module* or *class* has one cohesive responsibility, but that responsibility can be substantial.

```python
# DON'T do this (too granular):
class EmailSender:
    def send(self, to: str, subject: str, body: str): ...

class PasswordResetTokenGenerator:
    def generate(self, user_id: UUID) -> str: ...

class PasswordResetService:
    def __init__(self, email_sender: EmailSender, token_gen: PasswordResetTokenGenerator):
        self.email_sender = email_sender
        self.token_gen = token_gen

    def send_reset_email(self, user: User):
        token = self.token_gen.generate(user.id)
        self.email_sender.send(user.email, "Reset", f"Token: {token}")

# DO this (cohesive):
class PasswordResetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_token(self, user_id: UUID) -> str:
        # Token generation logic
        return jwt.encode({"user_id": str(user_id), "exp": ...}, SECRET)

    async def _send_email(self, to: str, token: str):
        # Email sending logic
        # Use an email library or service
        pass

    async def send_reset_email(self, user: User):
        token = self._generate_token(user.id)
        await self._send_email(user.email, token)
```

**When to extract a class**:
- You have 2+ implementations (EmailSender, MockEmailSender)
- The component is used across multiple services
- The logic is complex enough to warrant isolated testing

**When to keep it internal**:
- Single use case
- Implementation detail
- Makes code harder to follow if extracted

## FastAPI-Specific Patterns

### Dependency Injection

Use FastAPI's `Depends()` for shared resources:

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

# api/v1/endpoints/users.py
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

**Benefits**:
- Automatic dependency resolution
- Easy testing (override dependencies)
- Clear dependency graph

### Error Handling

Use `HTTPException` with proper status codes:

```python
from fastapi import HTTPException, status

# DON'T create custom exception classes for HTTP errors
class UserNotFoundException(Exception):
    pass

# DO use HTTPException
if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

# For business logic exceptions (non-HTTP), custom exceptions are fine
class InsufficientFundsError(Exception):
    """Raised when account has insufficient funds"""
    pass
```

### Response Models

Always specify response models:

```python
# DON'T return raw models (exposes everything)
@router.get("/users/{user_id}")
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    return user  # BAD: Exposes hashed_password

# DO use response schemas
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    return user  # Pydantic filters fields automatically
```

## TypeScript-Specific Patterns

### Type Safety from Backend

Always generate types from backend:

```typescript
// DON'T manually duplicate types
interface User {
  id: string
  email: string
  name: string
}

// DO generate from OpenAPI or Pydantic
// types/api.ts (generated)
export interface User {
  id: string
  email: string
  name: string
  created_at: string
}
```

### React Query for Server State

Use React Query for all API data:

```typescript
// DON'T manage server state in React state
const [users, setUsers] = useState<User[]>([])

useEffect(() => {
  fetch('/api/users').then(r => r.json()).then(setUsers)
}, [])

// DO use React Query
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

**Benefits**:
- Automatic caching
- Refetching on window focus
- Loading and error states
- Optimistic updates

### Zustand for Client State

Use Zustand for UI state (not server data):

```typescript
// store/ui.ts
import create from 'zustand'

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  toggleSidebar: () => void
  setTheme: (theme: 'light' | 'dark') => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  theme: 'light',
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => set({ theme })
}))

// Use in components
function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore()

  return (
    <div className={sidebarOpen ? 'open' : 'closed'}>
      <button onClick={toggleSidebar}>Toggle</button>
    </div>
  )
}
```

## When to Refactor

**Refactor when you feel pain**:
- Testing is hard (extract dependencies)
- Code is duplicated (extract function/class)
- Changes ripple across many files (wrong boundaries)
- Files are >500 lines (split by responsibility)

**Don't refactor**:
- "Just because" (waste of time)
- To make it look more like C# (fight the language)
- Before you have working code (premature)
- Speculatively for "future flexibility" (YAGNI)

## Decision Framework

When making architectural decisions, ask:

1. **Do I have 2+ implementations?**
   - Yes → Use Protocol/interface
   - No → Just write the class

2. **Is this a cross-cutting concern?** (auth, logging, validation)
   - Yes → Separate it (middleware, dependency, decorator)
   - No → Keep it with the domain logic

3. **Will this be hard to test?**
   - Yes → Extract dependencies, use DI
   - No → Keep it simple

4. **Is this pattern common in the ecosystem?**
   - Yes → Follow the pattern (even if it differs from C#)
   - No → Apply your judgment

5. **Am I fighting the language?**
   - Yes → Step back, learn the idiom
   - No → Proceed

## Summary

**Keep from C#**:
- Layer separation (HTTP, Business, Data)
- Dependency injection
- Input validation
- Type safety (via type hints and TypeScript)

**Adapt for Python**:
- Use Protocol instead of ABC
- Don't create interfaces for single implementations
- Trust Pydantic for validation
- Larger, more cohesive classes are fine

**Adapt for TypeScript**:
- Generate types from backend
- Use React Query for server state
- Use Zustand for client state
- Embrace structural typing

**Golden Rule**: Write straightforward code. Refactor when you feel pain. Don't pre-optimize structure.

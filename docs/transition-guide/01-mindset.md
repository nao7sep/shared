# AI-Collaborative Development Mindset

## The Mental Model Shift

### Old Model: AI as Writing Helper
- **You**: Design architecture, choose patterns, specify implementation details
- **AI**: Write the code you already decided on
- **Your control**: Micromanaging the HOW

### New Model: AI as Development Partner
- **You**: Define problems, requirements, constraints, and preferences
- **AI**: Propose approaches, implement, adapt based on feedback
- **Your control**: Validating outcomes and guiding direction

## What Control Actually Means Now

You haven't lost control by focusing on WHAT instead of HOW—you've gained **leverage**.

Control now means:
- **Validating** that solutions actually solve your problem
- **Catching** bugs, security issues, and edge cases
- **Ensuring** code fits your project's patterns and constraints
- **Making** architectural decisions when there are trade-offs
- **Reviewing** for correctness, not writing every line

### Analogy

A construction manager doesn't specify which hand the carpenter uses to hammer nails. They specify what gets built and verify quality.

That's not less control—it's **appropriate delegation**.

## Language Choice: English vs Japanese

### Recommendation
Use **English** for all development work: code, comments, commits, documentation, and AI conversations.

### Rationale

1. **Token efficiency**: Japanese uses 2-4x more tokens than English
   - Directly impacts costs
   - Reduces available context window
   - Slows down responses

2. **Technical precision**: Programming ecosystem is English-native
   - Error messages are in English
   - Documentation is in English
   - Stack Overflow, GitHub issues are in English
   - Less translation friction = less cognitive overhead

3. **Your English is sufficient**: You're communicating clearly
   - "Almost always good enough to get work done" = good enough
   - The gap between your English and perfect English is smaller than the overhead of translation

4. **Muscle memory**: Building mental context in one language helps
   - Switching between Japanese and English adds cognitive load
   - Consistency reduces mental fatigue

### Exceptions

Use Japanese only when:
- Complex business domain concepts that are inherently Japanese
- Precision of thought matters more than efficiency (rare)
- Personal notes where comfort > optimization

## How to Give Effective Instructions

### The WHAT Framework

**Define the outcome**, not the implementation:

❌ Bad: "Create a UserService class with a CreateUser method that takes email and password parameters, validates them using regex, hashes the password with bcrypt, creates a User entity, saves it to the database using the repository pattern, and returns the user ID."

✅ Good: "Implement user registration. Requirements: validate email format, hash passwords securely, store in database, return user ID. Follow our existing patterns in the codebase."

### Specify Constraints, Not Steps

**What to specify**:
- Requirements and acceptance criteria
- Security constraints
- Performance requirements
- Compatibility requirements
- Which existing patterns to follow

**What NOT to specify** (unless you have strong reasons):
- Which specific libraries to use (unless mandated)
- Implementation algorithms
- Variable naming conventions (AI knows conventions)
- Code organization within a function

### Example Instructions

**Starting a feature**:
```
Implement the user registration endpoint according to docs/api.md.
- Use Pydantic for validation
- Hash passwords with bcrypt
- Return JWT token
- Follow FastAPI patterns from existing auth code
```

**Refining**:
```
Add rate limiting to the registration endpoint.
- 5 attempts per IP per hour
- Return 429 with Retry-After header
```

**Fixing issues**:
```
The email validation is case-sensitive, but emails should be
case-insensitive. Fix this and ensure uniqueness checks work correctly.
```

## What to Review For

Your job is **quality assurance**, not line-by-line writing.

### Security (Critical)
- SQL injection vulnerabilities
- XSS vulnerabilities
- Authentication/authorization bypasses
- Sensitive data exposure
- Input validation gaps

### Correctness (High Priority)
- Does it actually solve the problem?
- Does it handle edge cases?
- Are error messages informative?
- Does it match the specification?

### Fit (Medium Priority)
- Does it follow existing code patterns?
- Is it consistent with the rest of the codebase?
- Does it integrate well with existing systems?

### Style (Low Priority)
- Variable naming (only if confusing)
- Code organization (only if messy)
- Comments (only if needed for clarity)

**Important**: Don't nitpick style. If the code works, is secure, and is maintainable, it's good enough.

## Common Mindset Traps

### Trap 1: Over-Specifying
**Symptom**: You're telling AI which specific functions to call, which variables to create, how to structure the code.

**Fix**: Step back. Define the requirement and let AI handle implementation. Review the result.

### Trap 2: Not Trusting the Output
**Symptom**: You're rewriting everything AI produces "just to be sure."

**Fix**: Review critically but trust by default. If you spot patterns of errors, give AI feedback to correct them.

### Trap 3: Asking Too Many Questions
**Symptom**: You're asking "Should I do X or Y?" for every small decision.

**Fix**: Make decisions yourself for project-level choices. Let AI make decisions for implementation details. Override if needed.

### Trap 4: Treating AI Like a Junior Developer
**Symptom**: You're explaining basic concepts, showing examples of simple patterns.

**Fix**: AI knows programming patterns. Focus on your specific requirements, not teaching.

## When to Step In

**Do intervene when**:
- Security vulnerabilities are introduced
- The approach doesn't fit your requirements
- Performance will be unacceptable
- The code breaks existing patterns in ways that matter

**Don't intervene when**:
- Variable names are "not what you would choose" but are clear
- The implementation approach differs from yours but works
- Code style differs slightly from your preference
- AI uses a library you're unfamiliar with (learn it instead)

## Measuring Success

**Old metric**: "Did I write most of the code?"
**New metric**: "Did I ship working, secure, maintainable software faster?"

Success is:
- Solving problems quickly
- Catching bugs in review
- Maintaining code quality
- Learning new patterns from AI implementations
- Spending time on architecture and requirements, not typing

## Recalibration

Read this document quarterly, or when you notice:
- Giving overly detailed instructions
- Rewriting large portions of AI output
- Feeling like you're "not coding anymore"
- Spending more time instructing than reviewing

The goal is **effective leverage**, not perfect control.

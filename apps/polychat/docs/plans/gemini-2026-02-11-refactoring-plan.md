# PolyChat Refactoring & Improvement Plan

**Agent:** Gemini
**Date:** 2026-02-11

## Overview
Review of the PolyChat project revealed a functional but increasingly complex codebase with some "God Object" patterns and tangled concerns in the main execution loop. This plan outlines high-ROI refactorings to improve maintainability, testability, and safety without over-engineering.

## Primary Objectives
1.  **Decouple REPL from Execution Logic**: Extract the complex AI execution flow from `repl.py`.
2.  **Modularize Commands**: Move away from massive mixins to a more structured command system.
3.  **Refine Session Management**: Reduce the surface area of `SessionManager` by extracting secondary responsibilities.
4.  **Centralize UI Interactions**: Ensure consistent output and better testability by abstracting console interactions.

---

## Phase 1: AI Execution & REPL Cleanup (High Priority)

### 1.1 Extract `AIExecutionService`
The `execute_send_action` function in `repl.py` is too large and handles too many concerns.
- **Goal**: Create `src/polychat/ai/service.py` to encapsulate the lifecycle of an AI request.
- **Responsibilities**:
    - Provider validation and retrieval.
    - AI invocation and streaming management.
    - Thought callback handling.
    - Citation enrichment (fetching and saving pages).
    - Logging of requests and responses.
- **Benefit**: Simplifies `repl.py` significantly, making the core loop readable and the execution logic testable in isolation.

### 1.2 Thin the REPL Loop
- **Goal**: Reduce `repl_loop` to just handling input and delegating to the Orchestrator and the new Execution Service.
- **Action**: Move prompt-toolkit setup and key bindings to a helper if necessary, but focus on removing "business" logic.

---

## Phase 2: Command System Refactoring

### 2.1 Replace Mixins with Command Registry
The multiple inheritance pattern in `CommandHandler` is becoming hard to track.
- **Goal**: Implement a `Command` class/interface and a `CommandRegistry`.
- **Action**: 
    - Each command becomes a small class or a decorated function.
    - `CommandHandler` becomes a dispatcher that looks up commands in the registry.
- **Benefit**: Better separation of concerns, easier to add/remove commands, and improved discoverability of command logic.

---

## Phase 3: Session & State Decoupling

### 3.1 Extract Hex ID Management
`SessionManager` currently handles hex ID assignment and tracking.
- **Goal**: Move this to a `HexIdManager` or similar utility that operates on the chat data.
- **Benefit**: Reduces `SessionManager` size (currently 26KB) and localizes hex ID logic.

### 3.2 Refine Provider Caching
- **Goal**: Move provider caching out of `SessionState`/`SessionManager` into a dedicated `ProviderCache`.
- **Benefit**: Cleaner state container and better encapsulation of caching strategies (e.g., timeout-aware caching).

---

## Phase 4: UI & Interaction abstraction

### 4.1 Expand `UserInteractionPort`
- **Goal**: Add methods for standardized output (info, warning, error, AI response prefix).
- **Action**: Update `ThreadedConsoleInteraction` to implement these.
- **Benefit**: Reduces direct `print()` calls in domain logic, facilitating easier integration testing with mocked interactions.

---

## Success Criteria
- `repl.py` reduced in size by at least 40%.
- `SessionManager.py` reduced in size by at least 30%.
- All tests pass, and new tests cover the extracted `AIExecutionService`.
- No regressions in user-facing behavior.

## Time to Market Note
These refactorings are designed to be "safe" and incremental. Each phase can be implemented and verified independently. Shipping remains #1; quality is achieved through better structure that prevents future bugs.

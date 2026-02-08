# PolyChat Architecture Refactoring Plan

**Created**: 2026-02-08
**Status**: Planning Phase
**Estimated Total Effort**: 31-40 hours

---

## Executive Summary

This document outlines a comprehensive refactoring plan to address architectural concerns in the PolyChat codebase. The primary goals are:

1. **Separation of Concerns**: Separate UI logic from business logic
2. **Unified State Management**: Eliminate session/session_dict duality
3. **Maintainability**: Extract the "God Module" (repl.py) into focused components
4. **Testability**: Add comprehensive tests before risky refactorings

---

## Architectural Issues Identified

### 1. repl.py - God Module (HIGH PRIORITY)
**Location**: `src/poly_chat/repl.py` (571 lines)

**Problems**:
- Handles UI logic (prompt-toolkit setup, keybindings, console printing)
- Session orchestration (managing chat switching, handling special command signals)
- AI communication (looping and sending messages)
- Tightly coupled state management

**Impact**: Hard to test, hard to modify, violations of Single Responsibility Principle

---

### 2. chat_manager.py - Mixed Concerns (MEDIUM PRIORITY)
**Location**: `src/poly_chat/chat_manager.py`

**Problems**:
- Mixes file system services with CLI UI logic
- `format_chat_info()` - presentation formatting (should be in UI layer)
- `prompt_chat_selection()` - interactive prompts (should be in UI layer)
- `delete_chat()` - includes user confirmation prompts (should be caller's responsibility)

**Impact**: Can't reuse file operations without pulling in UI dependencies

---

### 3. app_state.py - Dual State Management (MEDIUM PRIORITY)
**Location**: `src/poly_chat/app_state.py` and `src/poly_chat/repl.py`

**Problems**:
- Defines `SessionState` dataclass (clean, typed)
- But repl.py creates BOTH `SessionState` AND `session_dict`
- Commands operate on `session_dict`, not `SessionState`
- Constant manual synchronization required (repl.py lines 401-407)

**Impact**: Code duplication, potential sync bugs, unclear source of truth

---

### 4. commands/ - Direct Dictionary Manipulation (MEDIUM PRIORITY)
**Location**: `src/poly_chat/commands/`

**Problems**:
- Every command mixin operates directly on mutable `session_dict`
- No defined interface or contract
- Commands directly handle persistence logic

**Impact**: Tight coupling, hard to refactor state management

---

### 5. ai_runtime.py - UI in Business Logic (LOW PRIORITY)
**Location**: `src/poly_chat/ai_runtime.py` (line 96)

**Problems**:
- `send_message_to_ai()` calls `display_streaming_response()` (UI concern)
- Business logic shouldn't know about presentation

**Impact**: Can't reuse AI logic without UI, harder to test

---

### 6. profile.py - Hardcoded UI Output (LOW PRIORITY)
**Location**: `src/poly_chat/profile.py` (lines 220-221)

**Problems**:
- `create_profile()` has hardcoded `print()` statements
- Utility function making UI decisions

**Impact**: Can't reuse function in non-CLI contexts, harder to test

---

## Refactoring Plan

### Phase 1: Quick Wins (Low Risk - ~1.5 hours)

**Goal**: Build confidence with safe refactorings

#### Task #1: Refactor profile.py to return status messages
**Risk**: Very Low (~5%)
**Time**: 30 minutes

**Changes**:
- Update `create_profile()` to return `(profile_dict, messages_list)`
- Move `print()` calls to caller in `cli.py`
- No logic changes, pure mechanical refactoring

**Files Modified**:
- `src/poly_chat/profile.py`
- `src/poly_chat/cli.py`

**Testing**:
- Run `pc init test-profile` and verify output unchanged
- Unit test the function

---

#### Task #2: Extract UI functions from chat_manager.py
**Risk**: Low (~10%)
**Time**: 1 hour

**Changes**:
- Create new module: `src/poly_chat/ui/chat_ui.py`
- Move `format_chat_info()` (pure function, no dependencies)
- Move `prompt_chat_selection()` (pure function)
- Update `delete_chat()` to NOT prompt, move confirmation to callers

**Files Modified**:
- `src/poly_chat/chat_manager.py` - Remove UI functions
- `src/poly_chat/ui/chat_ui.py` - NEW file with moved functions
- `src/poly_chat/ui/__init__.py` - NEW file
- `src/poly_chat/commands/chat_files.py` - Update imports, add confirmation
- `src/poly_chat/commands/metadata.py` - Update imports if needed

**Testing**:
- Test `/open`, `/delete`, `/rename` commands
- Verify chat list displays correctly
- Verify delete confirmation still works

**Dependencies**: None (can run in parallel with Task #1)

---

### Phase 2: Foundation - Unify State Management (High Risk - ~10-14 hours)

**Goal**: Eliminate session/session_dict duality - THE CORE PROBLEM

#### Task #3: Add comprehensive state management tests
**Risk**: Low (testing only, no code changes)
**Time**: 2-3 hours

**CRITICAL**: This is our safety net before risky refactoring

**Changes**:
- Create `tests/test_session_state.py`
- Create `tests/test_repl_orchestration.py`

**Test Coverage**:
- SessionState creation and initialization
- session_dict creation from SessionState
- State synchronization (session → session_dict → session)
- Chat switching (state reset, hex ID management)
- Retry mode state transitions
- Secret mode state transitions
- Provider caching
- Command signal handling behavior

**Dependencies**: Should complete Phase 1 first

---

#### Task #4: Design SessionManager interface
**Risk**: Low (design only, no integration)
**Time**: 2-3 hours

**Changes**:
- Create `src/poly_chat/session_manager.py`
- Design SessionManager class that:
  - Wraps SessionState as single source of truth
  - Provides dict-like interface for backward compatibility
  - Handles state transitions (chat switching, mode changes)
  - Manages hex IDs
  - Handles provider caching

**Key Design Decisions**:
```python
class SessionManager:
    """Unified session state management."""

    def __init__(self, profile: dict, ...):
        self._state = SessionState(...)

    # Property access (preferred)
    @property
    def current_ai(self) -> str:
        return self._state.current_ai

    # Dict-like access (backward compatibility)
    def __getitem__(self, key: str):
        return getattr(self._state, key)

    # State transitions
    def switch_chat(self, chat_path: str, chat_data: dict):
        """Handle chat switching with proper state reset."""
        ...

    def enter_retry_mode(self):
        """Enter retry mode with proper state setup."""
        ...
```

**Files Created**:
- `src/poly_chat/session_manager.py` - NEW SessionManager class
- `tests/test_session_manager.py` - Unit tests for new class

**Testing**:
- Unit test all SessionManager methods
- Test dict-like access works
- Test state transitions are correct

**Dependencies**: Task #3 (tests must exist first)

---

#### Task #5: Integrate SessionManager into repl.py
**Risk**: High (~50%)
**Time**: 3-4 hours

**Changes**:
- Replace SessionState + session_dict with SessionManager in repl.py
- Keep `manager.to_dict()` for backward compat with CommandHandler
- Update repl.py internal code to use manager instead of session
- Remove manual sync code (lines 401-407)

**Incremental Approach**:
1. Create SessionManager instance (replace lines 41-76)
2. Update repl.py to use manager properties
3. Pass `manager.to_dict()` to CommandHandler (commands unchanged for now)
4. Verify keybindings still work
5. Remove sync code

**Files Modified**:
- `src/poly_chat/repl.py` - Replace SessionState + session_dict

**Testing**:
- Run full test suite
- Manual testing of all modes (normal, retry, secret)
- Test chat switching
- Test provider switching
- Test all keybindings

**Dependencies**: Task #4 must be complete

---

#### Task #6: Update commands to use SessionManager
**Risk**: Medium (~40%)
**Time**: 3-4 hours

**Changes**:
- Update CommandHandler to accept SessionManager instead of dict
- Update all command mixins to use manager properties
- Change `self.session["current_ai"]` → `self.session.current_ai`

**Files Modified**:
- `src/poly_chat/commands/base.py` - Update CommandHandler
- `src/poly_chat/commands/runtime.py` - Update all commands
- `src/poly_chat/commands/chat_files.py` - Update all commands
- `src/poly_chat/commands/metadata.py` - Update all commands
- `src/poly_chat/commands/misc.py` - Update all commands
- `src/poly_chat/repl.py` - Pass manager instead of manager.to_dict()

**Testing**:
- Test EVERY command: `/use`, `/mode`, `/retry`, `/secret`, `/open`, `/new`, `/close`, `/delete`, `/rename`, `/rewind`, `/help`, `/exit`
- Verify state changes work correctly
- Test error handling in commands

**Dependencies**: Task #5 must be complete and tested

---

### Phase 3: Separate Concerns - AI Runtime (Medium Risk - ~2 hours)

**Goal**: Remove UI logic from business logic

#### Task #7: Separate AI response streaming from ai_runtime
**Risk**: Medium (~25%)
**Time**: 1-2 hours

**Changes**:
- Update `send_message_to_ai()` to return stream instead of accumulated text
- Update all callers to handle streaming display

**Before**:
```python
# ai_runtime.py line 96
response_text = await display_streaming_response(response_stream, prefix="")
return response_text, metadata
```

**After**:
```python
# ai_runtime.py
return response_stream, metadata
```

**Files Modified**:
- `src/poly_chat/ai_runtime.py` - Remove display call, return stream
- `src/poly_chat/repl.py` - Update 4 call sites:
  - Lines ~380-388 (secret oneshot)
  - Lines ~451-459 (secret mode)
  - Lines ~481-489 (retry mode)
  - Lines ~507-515 (normal mode)

**Each call site becomes**:
```python
response_stream, metadata = await send_message_to_ai(...)
response_text = await display_streaming_response(response_stream, prefix="")
```

**Testing**:
- Test streaming works in all modes
- Verify token counts still display
- Test error handling during streaming
- Test KeyboardInterrupt during streaming

**Dependencies**: Can be done after Phase 1, before or during Phase 2

---

### Phase 4: Extract Orchestration (Very High Risk - ~15-20 hours)

**Goal**: Break up the repl.py God Module

#### Task #8: Design ChatOrchestrator interface
**Risk**: Low (design only)
**Time**: 3-4 hours

**Changes**:
- Create `src/poly_chat/orchestrator.py`
- Design ChatOrchestrator class that handles:
  - Command signal processing
  - Chat lifecycle (open, close, switch, rename, delete)
  - Mode transitions (retry, secret)
  - State persistence

**Key Design**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class OrchestratorAction:
    """Result of orchestration that tells REPL what to do."""
    action: str  # "continue", "break", "print", "error"
    message: Optional[str] = None
    chat_path: Optional[str] = None
    chat_data: Optional[dict] = None

class ChatOrchestrator:
    """Handles chat lifecycle and mode transitions."""

    def __init__(self, session_manager: SessionManager):
        self.session = session_manager

    async def handle_command_response(
        self,
        response: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Process command response signal and return action for REPL."""
        ...

    async def handle_user_message(
        self,
        user_input: str,
        chat_path: str,
        chat_data: dict
    ) -> OrchestratorAction:
        """Process user message and return action for REPL."""
        ...
```

**Files Created**:
- `src/poly_chat/orchestrator.py` - NEW ChatOrchestrator class
- `tests/test_orchestrator.py` - Unit tests

**Testing**:
- Unit test all orchestrator methods
- Test signal handling logic
- Test state transitions

**Dependencies**: Phase 2 must be complete (needs SessionManager)

---

#### Task #9: Extract signal handling to ChatOrchestrator
**Risk**: Very High (~70%)
**Time**: 6-8 hours

**Changes**:
- Move command response handling from repl.py to ChatOrchestrator
- Replace massive if/elif chain (lines 200-422) with orchestrator calls

**Incremental Approach** (one signal at a time):
1. `__EXIT__` (simplest)
2. `__CLOSE_CHAT__`
3. `__NEW_CHAT__`
4. `__OPEN_CHAT__`
5. `__RENAME_CURRENT__`
6. `__DELETE_CURRENT__`
7. `__CLEAR_SECRET_CONTEXT__`
8. `__CANCEL_RETRY__`
9. `__APPLY_RETRY__`
10. `__SECRET_ONESHOT__` (most complex)

**Strategy for Each Signal**:
1. Move logic to orchestrator method
2. Update repl.py to call orchestrator
3. Test thoroughly before moving to next signal
4. Commit after each successful migration

**Files Modified**:
- `src/poly_chat/orchestrator.py` - Implement signal handlers
- `src/poly_chat/repl.py` - Replace if/elif chain with orchestrator calls

**Testing** (after EACH signal migration):
- Test the specific command that triggers this signal
- Test state transitions work correctly
- Test error handling paths
- Run full test suite

**Dependencies**: Task #8 must be complete

---

#### Task #10: Extract message handling to ChatOrchestrator
**Risk**: Very High (~70%)
**Time**: 6-8 hours

**Changes**:
- Move user message handling logic (lines ~443-559) to ChatOrchestrator
- Includes: secret mode, retry mode, normal flow, error handling

**After this refactoring, repl.py should be**:
- Prompt setup and display (~100 lines)
- Input collection (~20 lines)
- Calling orchestrator (~50 lines)
- Displaying results (~30 lines)
- **Total: ~200 lines** (down from 571)

**Files Modified**:
- `src/poly_chat/orchestrator.py` - Add `handle_user_message()`
- `src/poly_chat/repl.py` - Simplify main loop

**Before** (repl.py lines 443-559):
```python
# 100+ lines of complex logic
if session.secret_mode:
    # ... 20 lines ...
if session.retry_mode:
    # ... 30 lines ...
# Normal message handling
# ... 50+ lines ...
```

**After**:
```python
action = await orchestrator.handle_user_message(user_input, chat_path, chat_data)
if action.action == "break":
    break
elif action.action == "print":
    print(action.message)
# etc.
```

**Testing**:
- Test all message modes (normal, retry, secret)
- Test error recovery
- Test KeyboardInterrupt handling
- Test hex ID assignment
- Test chat persistence

**Dependencies**: Task #9 must be complete

---

### Phase 5: Final Cleanup (Low Risk - ~3 hours)

**Goal**: Clean up and document the new architecture

#### Task #11: Final cleanup and documentation
**Risk**: Very Low
**Time**: 2-3 hours

**Changes**:
1. Remove obsolete code (app_state.py functions if no longer needed)
2. Update docstrings throughout
3. Create architecture documentation
4. Add architecture diagrams
5. Update README if needed
6. Remove any TODO comments added during refactoring
7. Final code review pass

**Files to Update**:
- All modified files - Review and polish
- `docs/architecture/ARCHITECTURE.md` - NEW - Document new structure
- `README.md` - Update if architecture is described

**Architecture Documentation Should Include**:
- Component diagram showing new structure
- Sequence diagrams for key flows
- State management explanation
- Command system explanation
- Extension points for future development

**Testing**:
- Run full test suite
- Manual end-to-end testing
- Performance testing (ensure no regressions)
- Test all commands and modes

**Dependencies**: Phases 1-4 must be complete

---

## Decision Points & Checkpoints

### Checkpoint 1: After Phase 1
**Decision**: Are we comfortable with the workflow?

- ✅ **Proceed** if: Changes went smoothly, tests pass, confident in approach
- ⏸️ **Pause** if: Unexpected issues, need to reassess approach

---

### Checkpoint 2: After Task #3 (Tests)
**Decision**: Do tests adequately cover existing behavior?

- ✅ **Proceed** if: Comprehensive test coverage, confident in safety net
- ⏸️ **Add more tests** if: Coverage gaps identified

---

### Checkpoint 3: After Task #6 (SessionManager Complete)
**Decision**: Is SessionManager working well?

- ✅ **Proceed to Phase 4** if: Clean implementation, all tests pass, commands work
- ⏸️ **Stabilize** if: Issues discovered, need refinement

---

### Checkpoint 4: After Task #8 (Orchestrator Design)
**Decision**: Does orchestrator design make sense?

- ✅ **Start extraction** if: Design is clean, interfaces make sense
- ⏸️ **Refine design** if: Unclear responsibilities, need more thought

---

## Risk Management Strategy

### For High-Risk Tasks (5, 6, 9, 10):

1. ✅ **Git commit before starting** - Ensure clean state
2. ✅ **Work in small increments** - Don't change everything at once
3. ✅ **Test continuously** - Run tests after each change
4. ✅ **Keep rollback plan** - Know how to revert if needed
5. ✅ **Peer review** - Get feedback on complex changes

---

### Signs to STOP and Reassess:

- 🚫 Tests start failing and we can't figure out why
- 🚫 Changes cascade beyond planned scope
- 🚫 Logic becomes more complex instead of simpler
- 🚫 We're rewriting functionality instead of reorganizing
- 🚫 Bugs appearing that weren't there before

---

### Recovery Strategies:

**If Task Fails**:
1. Revert to last good commit
2. Analyze what went wrong
3. Adjust approach
4. Try again with smaller increments

**If Tests Fail**:
1. Don't proceed until fixed
2. Understand why they're failing
3. Fix or update tests as needed
4. Only continue when green

---

## Effort Estimates

| Phase | Risk Level | Tasks | Estimated Time |
|-------|-----------|-------|----------------|
| Phase 1: Quick Wins | 🟢 Low | #1-2 | 1.5 hours |
| Phase 2: State Management | 🔴 High | #3-6 | 10-14 hours |
| Phase 3: AI Runtime | 🟡 Medium | #7 | 2 hours |
| Phase 4: Orchestration | 🔴 Very High | #8-10 | 15-20 hours |
| Phase 5: Cleanup | 🟢 Low | #11 | 3 hours |
| **TOTAL** | | **11 tasks** | **31-40 hours** |

---

## Recommended Approaches

### Option A: All-In
**Complete all phases sequentially**

- **Best for**: Complete architectural overhaul
- **Timeline**: 1-2 weeks of focused work
- **Risk**: High, but highest payoff
- **Outcome**: Fully refactored, maintainable codebase

---

### Option B: Staged
**Do Phases 1-2, pause, then 3-4-5 later**

- **Best for**: Validate approach before committing to complex work
- **Timeline**: Phase 1-2 (week 1), assess, Phase 3-5 (week 2+)
- **Risk**: Medium, can stop with value delivered
- **Outcome**: Core issues fixed, can continue later if desired

---

### Option C: Minimal
**Just Phases 1-2**

- **Best for**: Quick wins + core state management fix
- **Timeline**: 1 week
- **Risk**: Low-Medium
- **Outcome**: Improved state management, some UI separation, repl.py remains large

---

## Recommended Approach: **Option B (Staged)**

### Rationale:
1. **Phase 1** provides immediate value with minimal risk
2. **Phase 2** fixes the core architectural issue (state duality)
3. **Natural checkpoint** after Phase 2 to assess before tackling repl.py extraction
4. **Can stop with value delivered** if Phase 4 proves too risky
5. **Builds confidence incrementally**

---

## Next Steps

1. ✅ Review this plan
2. ✅ Choose approach (A, B, or C)
3. ✅ Begin with **Task #1**: Refactor profile.py
4. ✅ After each task: test, commit, assess
5. ✅ Use checkpoints to decide whether to continue

---

## Success Metrics

### After Phase 1:
- ✅ UI functions separated from business logic
- ✅ No hardcoded print statements in utility functions
- ✅ All tests passing

### After Phase 2:
- ✅ Single source of truth for session state
- ✅ No manual state synchronization needed
- ✅ Commands use clean interface
- ✅ Comprehensive test coverage

### After Phase 3:
- ✅ AI runtime doesn't know about UI
- ✅ Business logic testable in isolation

### After Phase 4:
- ✅ repl.py reduced to ~200 lines
- ✅ Clear separation: UI / Orchestration / Commands
- ✅ Easy to add new commands or signals
- ✅ State management encapsulated

### After Phase 5:
- ✅ Complete documentation
- ✅ Architecture diagrams
- ✅ Clean, maintainable codebase

---

## Appendix: File Impact Analysis

### Files to Create:
- `src/poly_chat/ui/__init__.py`
- `src/poly_chat/ui/chat_ui.py`
- `src/poly_chat/session_manager.py`
- `src/poly_chat/orchestrator.py`
- `tests/test_session_state.py`
- `tests/test_repl_orchestration.py`
- `tests/test_session_manager.py`
- `tests/test_orchestrator.py`
- `docs/architecture/ARCHITECTURE.md`

### Files to Modify Significantly:
- `src/poly_chat/repl.py` (major refactoring)
- `src/poly_chat/profile.py` (minor refactoring)
- `src/poly_chat/chat_manager.py` (medium refactoring)
- `src/poly_chat/ai_runtime.py` (minor refactoring)
- `src/poly_chat/commands/base.py` (medium refactoring)
- `src/poly_chat/commands/runtime.py` (minor refactoring)
- `src/poly_chat/commands/chat_files.py` (minor refactoring)
- `src/poly_chat/commands/metadata.py` (minor refactoring)
- `src/poly_chat/commands/misc.py` (minor refactoring)

### Files Potentially Made Obsolete:
- `src/poly_chat/app_state.py` (may be merged into session_manager.py)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-08
**Status**: Ready for implementation

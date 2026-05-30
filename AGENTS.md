## Testing Rules (TDD Detroit-Style)

### Core Principles
- **State verification over interaction verification** — assert on resulting state, not mock calls
- **Hand-written fakes** — no `unittest.mock`, `MagicMock`, `patch`, or `pytest-mock`
- **Protocol-based DI** — fakes implement `Protocol` classes from `ports/`
- **Tests first** — write failing tests (RED), then implement (GREEN), then refactor

### Test Levels
| Level | Location | Purpose |
|-------|----------|---------|
| Unit | `test/unit/` | Domain + Application together, fakes only for infrastructure ports |
| Integration | `test/integration/` | IO-dependent: real HTTP, real filesystem, real external APIs |
| E2E | `test/e2e/` | Full system flows from user entry point to observable outcome |

> **Note:** E2E tests are sparse by design — one per critical user journey. The pyramid shape
> (many unit → fewer integration → fewest E2E) reflects cost and speed, not importance.

### Integration Tests = IO-Dependent
- Integration tests MUST involve real IO (network, disk, audio)
- Integration tests MUST NOT replace unit tests — they complement them at the IO boundary
- Integration tests MUST be marked with `@pytest.mark.integration`
- The `Protocol` in `ports/` defines the contract; integration tests verify that the real adapter
  satisfies it — if `infrastructure/` is empty, the test fails with `ImportError`, not with a
  meaningful assertion failure; the RED that matters comes after the adapter exists but behaves wrong

### BVA (Boundary Value Analysis)
For every input domain, test all five points:

| Point | Description | Example (range 1–99) |
|-------|-------------|----------------------|
| Below minimum | First invalid value below lower bound | `0` |
| Minimum | Lowest valid value | `1` |
| Just above minimum | First value inside the valid range | `2` |
| Just below maximum | Last value inside the valid range | `98` |
| Maximum | Highest valid value | `99` |
| Above maximum | First invalid value above upper bound | `100` |

`None` and empty string are **invalid inputs**, not boundary values — test them as their own
invalid equivalence classes, not as substitutes for the minimum boundary.

### Equivalence Class Partitioning
- **Valid classes**: group inputs that behave the same → one test per class
- **Invalid classes**: each invalid class → separate test to verify rejection
- Never test two invalid classes in the same test

### Retiring Tests
Remove tests that are:
- **Subsets** — behavior already proven by a more specific test that covers the same path
- **Trivially true** — assert on type annotations or built-in Python behavior
- **Implementation details** — test caching, internal state that does not affect observable behavior
- **True duplicates** — same initial state, same action, same expected outcome in a different test
  class (not just similar assertion pattern — different test classes may use the same assertion
  form to verify different code paths)

### Mutation Testing
- Run `mutmut` to verify test quality
- Aim for **zero surviving mutants** — each survivor exposes a gap in the test suite
- Mutmut mutates operators (`<` → `<=`, `+` → `-`), literals (`0` → `1`), and logical
  operators (`and` → `or`); tests must catch all of these, not only boundary comparisons
- Equivalent mutants (mutations that do not change observable behavior) may be explicitly
  whitelisted with a comment; do not write a meaningless test just to kill them

### Test Conventions
- Arrange-Act-Assert (AAA) pattern
- Test classes grouped by method/feature
- `conftest.py` for shared fakes and fixtures
- Parametrize for equivalence classes with many valid inputs

---

## Architecture

### Clean Architecture Layers
```
src/harpi/
├── domain/          # Track, Queue, LoopMode (no dependencies)
├── application/     # PlayerService, Commands, Ports
│   ├── ports/       # Protocol interfaces
│   └── commands/    # Command + CommandHandler pairs
└── infrastructure/  # Real IO adapters (YoutubeResolver, DiscordPlayer)
```

### Rules
- **Domain**: zero external dependencies, pure business logic
- **Application**: depends only on domain; defines ports as `Protocol` interfaces that Infrastructure must implement
- **Infrastructure**: implements ports with real IO; Pydantic lives here (deserialization,
  API schemas, external data validation) — not in the domain
- **Commands**: frozen dataclass + handler with narrow protocol
- Each handler defines its own protocol

### Code Style
- Python 3.12+, type hints on all public methods
- `@dataclass(frozen=True)` for commands (application layer)
- `@dataclass(frozen=True)` or plain Python classes for domain models — no third-party base
  classes in the domain layer; keep it dependency-free
- `Pydantic BaseModel` for infrastructure DTOs and API schemas only
- `Protocol` for dependency inversion
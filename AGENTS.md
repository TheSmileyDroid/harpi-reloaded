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

## Commands

### Running Tools (always use `uv run`)

| Tool | Command |
|------|---------|
| Tests | `uv run pytest test/ -v` |
| Type check | `uv run ty check src/harpi/ test/ main.py` |
| Mutation | `uv run mutmut run` |
| Lint | `uv run ruff check src/ test/` |
| Format | `uv run ruff format src/ test/` |
| All | `uv run ty check src/harpi/ test/ main.py && uv run ruff check src/ test/ && uv run pytest test/ -v --ignore=test/e2e` |

### Mutmut Config Caveats
- Mutmut creates a `mutants/` directory and runs tests from there
- The `paths_to_mutate` directories are copied into `mutants/src/` — any other source
  directories needed at test time must be listed in `also_copy` in `[tool.mutmut]`
- Example: if tests import `harpi.infrastructure`, add `also_copy = ["src/harpi/infrastructure"]`
- Always run with `uv run mutmut run`, never `python -m mutmut run` (system Python may be
  a different version and fails with `set_start_method('fork')` errors)
- Run `rm -rf mutants/` before re-running if the config changed

### Ty Type Checker (v0.0.39)
- Must pass `main.py` explicitly if it's not under `src/harpi/` or `test/`
- Keyword arguments are not allowed for positional parameters in function calls
  (call `handle(service, args)` not `handle(service=service, args=args)`)
- Lambda return types are not always inferred correctly — prefer named wrapper functions:
  ```python
  def _wrap(self, handler: Handler) -> Callable[[str], Awaitable[str]]:
      async def wrapped(args: str) -> str:
          return await handler(self._player_service, args)
      return wrapped
  ```

### Dependency Management (uv)
- `uv add <package>` — adds to pyproject.toml and installs
- `uv pip install -e .` — installs project in dev mode (needed for mutmut to resolve imports)
- `uv pip list | grep <name>` — check if a package is installed
- Always check both `pyproject.toml` and actual `uv pip list` after adding a dependency

---

## Architecture

### Clean Architecture Layers
```
src/harpi/
├── domain/          # Track, Queue, LoopMode (no dependencies)
├── application/     # PlayerService, Commands, Ports
│   ├── ports/       # Protocol interfaces
│   └── commands/    # Handlers registered via @register decorator
└── infrastructure/  # Real IO adapters (YoutubeResolver, DiscordPlayer)
```

### Rules
- **Domain**: zero external dependencies, pure business logic
- **Application**: depends only on domain; defines ports as `Protocol` interfaces that Infrastructure must implement
- **Infrastructure**: implements ports with real IO; Pydantic lives here (deserialization,
  API schemas, external data validation) — not in the domain
- **Commands**: async functions decorated with `@register("name")`, collected into a
  registry dict at import time

### Command Registry Pattern
- Define handlers as plain async functions in `handlers.py`
- Decorate with `@register("command_name")` from `harpi.application.commands`
- The decorator stores the function in `_registry` dict at module load time
- `get_handlers()` returns a copy of the registry for the router to consume
- New command = 3 lines: `@register("name")` + `async def handler(service, args):`
- The handlers module must be imported for decorators to execute — add
  `from harpi.application.commands import handlers` at the end of `__init__.py`

### Code Style
- Python 3.12+, type hints on all public methods
- `@dataclass(frozen=True)` for commands (application layer)
- `@dataclass(frozen=True)` or plain Python classes for domain models — no third-party base
  classes in the domain layer; keep it dependency-free
- `Pydantic BaseModel` for infrastructure DTOs and API schemas only
- `Protocol` for dependency inversion

## Fakes & Test Doubles

### FakeResolver Behavior
- `FakeResolver.resolve(link)` always returns `Track(title="Fake Track", duration=120, ...)`
  regardless of the link — it does NOT use the `track1`, `track2`, `track3` fixtures
- Use `set_failure(link, exc)` to simulate errors
- For custom track properties (different titles, durations, None titles), create an inline
  `AudioResolverProtocol` implementation in the test

### FakePlayer State
- `FakePlayer.playing` — the currently playing track (or None)
- `FakePlayer.is_paused` / `FakePlayer.is_stopped` — boolean flags
- `FakePlayer.background_tracks` — list of background tracks
- All player methods are async (`play`, `pause`, `resume`, `stop`)
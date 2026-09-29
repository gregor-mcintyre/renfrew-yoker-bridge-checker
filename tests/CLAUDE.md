# Test conventions

The root `CLAUDE.md` governs this tree too. Where a rule below contradicts it, this file
wins for code under `tests/`; everything it doesn't override still applies.

---

## Commands

The canonical test commands — `README.md` copies them, so change them here first.

| Task              | Command                                      |
|-------------------|----------------------------------------------|
| Whole test suite  | `pytest`                                     |
| One tier          | `pytest tests/unit`                          |
| One file or test  | `pytest <path>` / `pytest -k <name>`         |
| Coverage          | `pytest --cov`                               |

---

## Overrides of the root `CLAUDE.md`

- **Docstrings** — required only where the table under *Docstrings and annotations*
  below says so; most test files carry none, and the root file's voice and
  `Args:`/`Returns:` rules apply only where one is required.
- **Module naming** — the root file bans `helpers`/`utils`/`common` as module names;
  `helpers.py` is the sanctioned name for shared test helpers here.
- **Helper placement** — a helper used by one test module stays in it, above its first
  caller; one shared by two or more moves to a locality-scoped module beside them.
- **Annotations** — test functions carry none; fixtures and shared modules keep the
  production standard.

`[[tool.mypy.overrides]]` relaxes `disallow_untyped_defs` and `disallow_incomplete_defs`
for `tests.*`; the rest of strict still applies. `per-file-ignores` silences
`D100`-`D103` on `tests/**/test_*.py`, so the docstring rules below are checked on
review, not by tooling. Shared modules aren't covered by either, so theirs is enforced.

---

## Layout

`tests/` mirrors the project's deployment roots: `tests/<tier>/<root>/...`. A new
deployment root needs a matching test directory, and `pythonpath` and `mypy_path` in
`pyproject.toml` are what let tests import across roots.

A directory's mirroring `tests/` package counts as part of that directory for the root
file's leading-underscore rule — tests importing a private name leave the underscore
intact.

---

## Tiers

Each tier answers a different question, and a higher tier never replaces a lower one.

- **Unit** — one class, method, property, or function in isolation. Every collaborator
  mocked. Synthetic data, defined in the test.
- **Integration** — two or more real units across their seams. All internal
  collaborators real; only network, clock, filesystem or other genuine third-party
  boundaries faked. Synthetic data, or small committed fixtures.
- **E2e** — the whole system, invoked exactly as a user does. Everything real, external
  integrations too where practical. Real bundled data, committed.

Routing a case:

- The assertion holds with every collaborator mocked → **unit**.
- It breaks only when real code meets real code — a signature across a seam, the shape
  of data handed on, ordering through a chain, an error crossing layers →
  **integration**.
- Only invoking the whole deliverable from outside produces it — process boundaries,
  packaging, deployment configuration, a real external integration → **e2e**.

Branch coverage lives in the unit tier. Integration covers the collaboration only, and
e2e is a happy path plus what nothing lower can reach. Before placing a case above the
unit tier, name the tier that cannot reach it; if a lower tier can, it belongs there. An
extra high-tier case is slower, more brittle, and duplicates cheaper coverage.

### Unit isolation

- **Mock every collaborator the unit calls**, asserted or not — an unmocked one runs for
  real and fires side effects (logs, I/O, clock reads) the test never meant to exercise.
  That holds most of all when it has its own tests or is a trusted library.
- **Keep a collaborator real only where the unit acts on what it returns** — branches on
  it, unpacks it, transforms it — so the assertion covers that handling, not a mock
  echoing itself. A value the unit merely forwards is plumbing: mock it and assert the
  forwarding.
- **Arguments follow the same judgement.** A parameter the unit only checks for
  truthiness, counts, `%r`-formats or passes on is opaque to it — pass a mock. Build a
  real object only where the unit reads its fields or transforms it.
- **A helper with its own `Test<Unit>` class is asserted at one level only.** Its
  caller's tests mock it and assert only that it was called, and with what — never what
  it does. Re-asserting it through the caller duplicates coverage and breaks two tests
  per change.

### Integration and e2e boundaries

- **No internal mocking in integration.** Only genuine third-party boundaries may be
  faked. A test that can't pass without patching an internal name means the seam is
  drawn in the wrong place, or the case belongs in the unit tier.
- **Integration scope follows the entry point**, not the file it lives in, and entry
  points nest into layers: in `fetch_user_data` → `fetch_remote_api` →
  `_validate_response`, each arrow is a seam. Each seam is tested in the lowest layer
  that has it, so the lower the layer, the more of the real behaviour the file of that
  layer tests. A layer above tests only how it pieces that layer in — one case per kind
  of outcome it handles, not one per branch below. A case whose failure would point at a
  lower layer belongs in the file of that layer, so every failure points at the layer
  that owns it.
- **A layer earns its own file when its seam has behaviour of its own.** A pass-through,
  or a private helper with one caller and no branching, is left to the file above — the
  only case where an outer file makes an inner one redundant. That can leave the top
  layer as the only file, but as a judgement, never the default.
- **E2e is driven from outside** — the documented command, script or handler — never by
  importing internals. A test that reaches inside is an integration test misnamed.
- **E2e keeps externals real where practical.** Where one genuinely isn't (a paid API,
  live hardware, a non-deterministic remote), stub the narrowest piece.

---

## Files

- **Unit** — `test_<module>.py`, mirroring the source 1:1. Drop a private module's
  underscore: `_parsing.py` → `test_parsing.py`, never `test__parsing.py`.
- **Integration** — named for what it exercises: usually the entry point of the layer
  under test, public or private, or any apt name that reads better. Not a list of
  collaborators, not a sentence. It may share the name of the unit file; the tier
  directory disambiguates.
- **E2e** — named for the user-facing entry point it drives: the CLI command, script or
  handler. Usually one per deliverable.
- **Shared helpers and factories** — locality-scoped modules beside their consumers,
  never inside a `test_*.py`.

---

## Names and grouping

- Tests: `test_<unit>_<scenario>_<expected>`.
- A unit with 2+ tests gets one `Test<Unit>` class; a function or method counts as a
  unit. Drop any leading underscore and CapWord it: `_validate_response` →
  `TestValidateResponse`. Inside the class, names drop `<unit>`:
  `test_<scenario>_<expected>`. A unit with one test keeps a standalone function with
  the full name.
- The default scenario — the unit called with ordinary input while every collaborator
  succeeds — is the one scenario left unnamed: `test_<expected>` inside a class,
  `test_<unit>_<expected>` standalone. Every other case names its scenario first, so
  an error case is `test_<error>_<expected>`, never `test_<expected>_if_<error>`.
- Fixtures: `lower_snake_case`, named for what they provide. Mocks: `mock_` prefix.
- The value returned by the code under test is always bound to `result`, never a
  contextual name like `status`.
- Re-check counts after any restructure: rules keyed to "2+ tests" or "used more than
  once" flip when tests move.

---

## Order and shape

- Negative → positive: errors and edge cases first, happy path last. Exception: tests
  pinning *how a collaborator is called* may precede error tests that stub that
  collaborator — they state the precondition those cases assume.
- One test, one reason to fail. Combine assertions only for inseparable concepts.
- **Arrange–Act–Assert**, a blank line between phases. Arrange builds inputs, then
  configures mocks, with a blank line between the two. Act is one call to the code under
  test; the blank line before it is required. With nothing to arrange, open on the act —
  the blank line before the asserts still stands.

---

## Assertions

- A value you both set and assert — a mock return, a config field, an input literal — is
  bound to one local and used in both places.
- Assert against the mock, not the literal you fed it: `assert result ==
  mock_fetch.return_value`, not `== "closed"`. Pin calls with `assert_called_once_with`
  or `call_args` rather than retyping the arguments.
- Prefer `assert_called_once_with` to `call_count`: same effort, proves the arguments
  too. `ANY` marks an argument whose presence matters but value doesn't.
- Derive an expected value the code's way only when that derivation is trusted — a
  stdlib call or a separately tested collaborator (`bound_input.isoformat()` rather than
  a hardcoded ISO string). When it is project-owned logic, hardcode the literal:
  deriving it the same way lets a defect pass on both sides.

---

## Mocks

- Patch where a name is **used**, not where it is defined — including same-module
  private helpers.
- Prefer `Mock` to `MagicMock`: `Mock` creates no magic methods, so a stand-in fails
  loudly the day the code does `len(x)` or `with x:`. `@patch` injects a `MagicMock`
  regardless.
- A mock inside a container passed as a typed parameter needs a `cast` — strict mypy
  checks test bodies, containers are invariant, and `spec=` doesn't help:
  `cast(list[Item], [Mock()])`. The cast is bookkeeping, not a hint a real object was
  wanted. A bare `Mock` needs none: typeshed gives it an `Any` base.
- When every test in a class patches the same target, decorate the class. Its mocks
  arrive in bottom-up decorator order, after `self` and before fixtures. Decorate a
  method only when tests need different targets.

---

## Patch targets

Call them *patch targets*, never "paths". A literal used once stays inline; used twice,
it becomes a constant, and is never retyped once the constant exists — build longer
targets from it.

- **A module in one file** — a private `_MODULE` constant: `_API_MODULE = "myapp._api"`,
  used as `@patch(f"{_API_MODULE}.requests.get")`.
- **A module two files need** — move first, import after. Put it in the shared
  patch-target module in the narrowest directory covering both consumers (beside the
  tests, never in a `test_*.py`). It is now imported from another directory, so it has
  no leading underscore before that import is written — never import a still-private
  module and rename it later. Name that module by what it holds: `patch_target.py` while
  it holds one target, `patch_targets.py` once it holds two or more — rename it and its
  importers when the count crosses. Import it dotted from `tests` (`from tests import
  patch_targets`, assuming `tests` is a regular package) and module-import it, since a
  bare `API` is ambiguous. The `_MODULE` suffix goes: `patch_targets.API`, not
  `.API_MODULE`.
- **The package** — the shared module names it for the package plus what it is,
  `MY_APP_PACKAGE = "myapp"`, never a bare `PACKAGE`. A target only one file uses isn't
  centralised; that file builds its `_MODULE` constant from the package constant.
- **A target part** (after the module — `requests.get`) used twice in a file — a
  file-local constant without the module name: `_REQUESTS_GET =
  f"{_API_MODULE}.requests.get"`, not `_API_REQUESTS_GET`.

---

## Docstrings and annotations

| File                              | Module docstring    | Classes and functions |
|-----------------------------------|---------------------|-----------------------|
| Unit `test_*.py`                  | None                | None                  |
| Integration or e2e `test_*.py`    | One line            | None                  |
| `conftest.py`                     | One line            | —                     |
| `helpers.py`, `patch_targets.py`… | Production standard | Production standard   |

- The one-line docstring is one plain sentence, measured — not eyeballed — against 88
  columns. Name the entry point and describe the real collaboration in general terms; a
  name-by-name list of collaborators overclaims and runs long.
  `"""Tests `fetch_user_data`, including real fetch and parse errors."""`
  `"""Tests the request handler end to end, from API request to JSON response."""`
- Fixtures always carry a full docstring and annotations, wherever they live — they are
  the suite's API, as are shared helpers.
- Test functions carry no annotations — no `-> None`, no parameter types.

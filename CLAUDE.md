# renfrew-yoker-bridge-checker

- **What it is:** An Alexa skill that reports when the Renfrew-Yoker pedestrian bridge
  is closed. A Raspberry Pi scrapes the council site on a schedule and caches the result
  in AWS SSM Parameter Store; an AWS Lambda reads that cache to answer voice requests
  inside Alexa's 8-second window.
- **Python:** 3.14

These conventions are the standard for this project — flag mismatches with existing
code or config instead of imitating them.

On Python 3.14+, never write `from __future__ import annotations`; PEP 649/749 make it
unnecessary.

---

## Commands

Run from the repository root, with `.venv` activated.

| Task              | Command                                                       |
|-------------------|---------------------------------------------------------------|
| Whole test suite  | `pytest`                                                      |
| One tier          | `pytest tests/unit`                                           |
| One file or test  | `pytest <path>` / `pytest -k <name>`                          |
| Every hook        | `pre-commit run --all-files`                                  |
| Lint / format     | `ruff check --no-fix .` / `ruff format --check .`             |
| Type-check        | `mypy .`                                                      |
| Dead code         | `vulture --min-confidence 80 .`                               |

`pytest` is not a pre-commit hook — run it yourself before committing. Verify a change
with the narrowest command that covers it, then run `pre-commit run --all-files` before
committing.

---

## Enforced by tooling — don't re-litigate

Ruff (lint, format, import sorting, docstring style, naming), mypy (static type
checking) and vulture (`--min-confidence 80`), all wired through pre-commit. House
defaults: 88 columns, double quotes, Google-style docstrings.

Ruff's `COM812` requires a trailing comma on any construct that spans lines, and the
formatter's magic trailing comma then holds it open — so **a wrapped signature or call
puts one argument per line**. Nothing to remember: let the tools tell you.

Hooks **report without auto-fixing** — fix flagged lines by hand, re-stage, and
re-commit; never pass `--fix` or skip a hook to force a commit through.

Actual settings live in `pyproject.toml` and `.pre-commit-config.yaml` — read them
rather than assuming.

Everything below is what those tools *can't* check.

---

## Naming

**Acronyms in CapWords.** Domain proper-noun initialisms keep full caps —
`HTTPClient`, `TestParseCSVHeaders`. Generic abbreviations take a leading capital
only — `db` → `Db`, `id` → `Id`, `ft` → `Ft`. Reword when adjacent initialisms
get hard to parse.

**Leading underscore** marks a name — constant, function, module, or package
directory — never imported outside its own directory: `_CONFIG_PATH`,
`_validators.py`. Extra importers *inside* that directory don't matter — the
mark tracks where a name is reachable from, not how often it's used. A directory's
mirroring `tests/` package counts as part of it, so tests importing a private name
leave the underscore intact; it's wrong only once a name is imported from a directory
that is neither the defining one nor its test mirror. A package directory earns the
underscore the same way — a subpackage nothing outside its parent imports. Manual
convention, not Ruff-enforced; doesn't apply to non-Python files.

**Module names.** PEP 8 mandates short, all-lowercase, underscores-if-it-helps
names. House convention: name by subject or shape, never a bare imperative verb
— a module is a namespace read at the call site, so `validate.validate_email(x)`
stutters while `validators.email(x)` doesn't. Pick whichever fits the content:

- **Domain noun** — `billing`, `routing` — functions share a subject, not a shape.
- **Gerund / action noun** — `parsing`, `serialization` — related operations on varied
  inputs.
- **Plural agent noun** — `validators`, `converters` — interchangeable members of a
  family.
- **Singular agent noun** — `parser`, `scheduler` — one coherent thing, often built
  around a single class.

Never `manager`/`handler` as a module name, and never `utils`/`helpers`/`common`/`misc`
— see *No generic `utils/`* below. If a `db` package already exists, a models
module is `db/models.py`, not `db_model.py` at the top level — avoid repeating
the package name in its own submodule.

---

## Code style

- **Imports:** object-import when the name is unambiguous and frequent; module-import
  when the prefix adds context or avoids ambiguity. Be consistent per-name — mixing
  styles across the codebase is fine. Never wildcard-import.
- **Arguments:** positional for short, unambiguous calls; keyword at 3+ args, for
  booleans, or for same-typed args; keyword-only (`*,`) for flags and config params.
- **No generic `utils/`.** Name modules by function. Only introduce `utils/` once there
  are enough small unrelated helpers to warrant it, then split by topic.
- **`__init__.py` files are always empty** — re-exports go elsewhere.
- **Helpers are defined above the function that calls them**, within the same module,
  ordered by when that function first uses them.
- **No dead code.** Delete zero-reference functions, classes and variables.
- **Break functions into smaller, testable pieces.** Keep functions and methods small
  and focused so they're easy to unit test — avoid monolithic functions that do
  too much, and refactor once one gets hard to test in isolation.
- **Separate logical blocks with blank lines.** Group related statements together
  within a function or block, with a blank line between distinct logical units —
  e.g., between an early return guard and the main logic that follows.
- **Don't restate default arguments.** Never pass a default argument value explicitly.
  If a function signature is `func(min=0)`, call it as `func()`, not `func(min=0)`.
  Applies to method defaults too — `body.encode()`, not `body.encode("utf-8")`;
  `d.get(key)`, not `d.get(key, None)`. Ruff's `UP012` catches only the string-literal
  form (`"...".encode("utf-8")`), so the variable form is on review.
- **Reuse an existing constant instead of retyping its literal.** If a name
  already captures a value the code needs — even as part of a longer string —
  reference the name; don't retype the literal. `_patch_targets.MY_APP_PACKAGE +
  "._api.requests.get"`, not `"myapp._api.requests.get"` — the second retypes a
  literal the first constant already owns, and the two copies can drift the moment
  the package is renamed. Nothing catches this; it's on review.
- **Inline single-use variables.** A variable used only once should be inlined unless
  inlining reduces readability. The exception: a binding that names an otherwise opaque
  expression improves clarity — then keep the variable even if used once. For example,
  `year_str = str(year)` followed by one use of `year_str` adds no value; inline it. But
  `parsed_date = parse_iso_date(raw_input)` followed by one use clarifies intent; keep
  it.

---

## Docstrings

Google-style, on every public module, class, function and method. Ruff's `D` rules check
presence and shape; everything below is voice, which they don't check.

- **Descriptive, not imperative** — `"""Fetches rows..."""`, not `"""Fetch rows..."""`.
  Exception: `@property`, phrased as an attribute — `"""The connection timeout."""`
- **Types live in the signature only**, never repeated in the docstring.
- **Reference a callee, don't echo it.** A function that delegates work to a helper
  keeps its own `Args:` and `Returns:`, but names the helper for anything its own
  docstring already covers — e.g., name `_validate_dates` rather than paraphrase what
  its docstring already explains.
- **Single backticks for code references:** wrap variable names, class names, method
  names, `None`, and literal numbers in backticks when mentioning them in prose. For
  example: `my_var`, `MyClass`, `None`, `42`. Avoid backticks for string literals unless
  you're specifying a particular string value.
- Generators use `Yields:`.
- **Blank lines:** module/class docstring → one blank line → content. Function/method
  docstring → **no** blank line, code starts immediately.
- **Articles:** "A"/"An" for a general type, "The" for a specific referent tied to this
  call or already introduced earlier in the docstring.
- **Booleans** describe the effect of `True`, not the type.
- Every sentence starts with a capital letter, including each `Args:`/`Returns:` entry.
- **Classes:** `Args:` matches constructor param names exactly. `Attributes:` documents
  actual object state and may diverge from `Args:` when the constructor renames or
  derives values — say so explicitly when it does.
- **Avoid possessive language for objects.** Don't anthropomorphize; prefer "the X of Y"
  over "Y's X".

---

## Testing

| Element                  | Convention                                                                                                                                                                                                                             |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Unit test file           | `test_<module>.py` mirrors source 1:1. Drop any leading underscore from a private module — `_parsing.py` → `test_parsing.py`, never `test__parsing.py`.                                                                                |
| Integration test file    | Named for what it exercises — usually the primary public entry point under test, but any apt name works when it reads better. Not every collaborator, not a sentence. May collide with the unit test filename; the path disambiguates. |
| E2e test file            | Named after the user-facing entry point exercised end to end — the CLI command, script, or handler. Usually one per deliverable.                                                                                                       |
| Test function            | `test_<unit>_<scenario>_<expected>`                                                                                                                                                                                                    |
| Test class               | `Test<Unit>` in CapWords — required once a unit has 2+ tests. A function counts: `_log` → `TestLog`                                                                                                                                    |
| Fixture                  | `lower_snake_case`, named for what it provides                                                                                                                                                                                         |
| Shared helpers/factories | Locality-scoped modules alongside consumers, never in `test_*.py`                                                                                                                                                                      |
| Mock objects             | `mock_` prefix — `mock_session`                                                                                                                                                                                                        |

**Tiers.** Each tier answers a different question; a higher tier never replaces a lower
one.

| Tier            | Exercises                                                             | Collaborators                                                                                                | Data                                     |
|-----------------|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|------------------------------------------|
| **Unit**        | One unit of code — a single function, method, or class — in isolation | Every collaborator mocked                                                                                    | Synthetic, defined in the test           |
| **Integration** | Two or more real units working together across their seams            | All real, no internal mocking; only genuine third-party boundaries (network, clock, filesystem) may be faked | Synthetic, or small committed fixtures   |
| **E2e**         | The whole system start to finish, exactly as a user invokes it        | All real, including external integrations where practical                                                    | Real bundled data, committed to the repo |

E2e stays thin: a subprocess-based happy path, plus the cross-layer failure cases no
unit or integration test can reach. Breadth of coverage still comes from the unit and
integration tiers — e2e does not make them redundant.

Integration scope follows the entry point named in a request, not the file, module, or
package — and entry points nest. Since a test mocks nothing internal, it already drives
through every real seam on its call chain, however many modules that crosses.
`fetch_user_data` calling `fetch_remote_api` calling `_validate_response` is one chain
with two seams — `current` meeting `_api`, and `_validate_response` meeting
`fetch_remote_api` — and testing the outermost entry point proves both, for every branch
its cases drive.

Before adding a file for an entry point, check whether an existing or concurrent file
for an *outer* entry point already drives through all its branches for real. If so, skip
the second file — it would only re-prove the same chain one frame lower. If not —
nothing else calls it, or the outer test's cases miss some branches — it earns its own
file, whether a package entry point or a function one module down.

This is why a narrower file can go stale without changing. Asked for integration tests
on `_api.py` alone, `fetch_remote_api` is the entry point on offer, so its test proves
the `fetch_remote_api` / `_validate_response` seam. Asked afterwards for the whole
package, `fetch_user_data` becomes the outer entry point, and its success/failure cases
drive through that same seam for real — the `_api.py` file is now stale beyond source
and convention drift, since a sibling file proves its chain, and it gets retired rather
than kept alongside the new one. Say so in the report rather than dropping a file
silently; catching this means actively listing the package's existing integration files
and checking each against the newly mapped chain, not noticing only because one was
already in view.

- One `Test<Unit>` class per unit once it has 2+ cases. **A function or method counts as
  a unit** — the rule isn't limited to classes, and here every test class covers a
  function. Derive the name by dropping any leading underscore and converting to
  CapWords: `_log` → `TestLog`, `_validate_response` → `TestValidateResponse`.
  Single-test cases stay standalone functions; inside a class, names drop `<unit>` →
  `test_<scenario>_<expected>`, while standalone functions keep the full form.
- Order tests negative → positive: errors and edge cases first, happy path last.
- Exception: tests that pin *how a collaborator is called* (its arguments) may precede
  the error tests when those error tests stub that collaborator and never reach the real
  call — they state the precondition the error cases assume.
- **One test, one reason to fail.** Combined assertions only when the concepts are
  genuinely inseparable.
- Mock where the name is **used**, not where it's defined — including same-module
  private helpers.
- **Mock almost everything.** A unit test isolates one unit, so mock every collaborator
  it calls — more so when that collaborator has its own tests or comes from a trusted
  third-party library. Keep a collaborator real only where the unit under test *acts on*
  what it returns — branches on it, unpacks it, transforms it — so the assertion covers
  that handling rather than a mock echoing itself. A value the unit merely forwards
  onward is plumbing: mock it and assert the forwarding.
- **Mock every collaborator on the path, asserted or not.** Even a test that asserts
  nothing about a collaborator mocks it if the code under test calls it — otherwise it
  runs for real, firing side effects (logs, I/O, clock reads) the test never meant to
  exercise. `test_returns_the_parsed_data` asserts only the return value, but
  `fetch_user_data` also calls `_log`, so `_log` is patched there too.
- **A helper with its own tests is asserted at one level only.** Once a private helper
  has its own `Test<Unit>` class, its caller's tests mock it and assert only that it was
  *called*, with what arguments — never what it does with them. Re-asserting a helper's
  behaviour through its caller duplicates coverage and couples both to one
  implementation, so one change breaks tests twice. `test_builds_and_returns_result` is
  the pattern: multiple helpers patched, delegation asserted, behaviour asserted
  nowhere.
- **The mock/real judgement applies to arguments too, not just to collaborator
  returns.** A parameter the unit only checks for truthiness, counts, or passes straight
  through is opaque to it — mock it; build a real object only where the unit reads its
  fields or transforms it. `_log` takes `list[Item]` but only checks emptiness and
  `%r`-formats the list, so its tests pass mocks.
- **A mock standing in for a typed parameter needs a `cast`.** `strict` mypy type-checks
  test bodies, and `list[Mock]` isn't `list[Item]` — the container is invariant, so
  `spec=` doesn't help either. Write `cast(list[Item], [Mock(), Mock()])`. The cast is
  type-checker bookkeeping, not a signal a real object was wanted — the rule above
  decides that.
- **Test functions carry no type annotations** — no `-> None`, no parameter types. The
  name and the `mock_` prefix are the documentation; `-> None` on a test says nothing.
  Fixtures and non-test helpers keep full annotations, since they're the suite's API.
  `[[tool.mypy.overrides]]` relaxes `disallow_untyped_defs` and
  `disallow_incomplete_defs` for `tests.*` to permit this — the rest of `strict` still
  applies, so test bodies and calls into production code are type-checked as before.
- **Prefer `Mock` to `MagicMock`.** `Mock` doesn't auto-create magic methods, so a
  stand-in fails loudly the day the code under test starts doing `len(x)` or `with x:`.
  Reach for `MagicMock` only when magic methods are genuinely needed. (`@patch` injects
  a `MagicMock` whatever you do — that's why an injected mock and a hand-built one
  differ.)

**Arrange–Act–Assert.** Every test body runs in three phases — arrange (build inputs,
then configure mocks, separated by a blank line), act (one call to the code under test),
assert — with a blank line between phases. The blank line **before the act** is
required: it marks "this line is the call under test." A test with nothing to arrange
may open straight on the act, but the blank line before the asserts still stands.

- **Name the result `result`.** When capturing the return value of the code under test,
  always bind it to a variable named `result`, not a contextually appropriate name like
  `status` or `parsed_date`. Consistency across all tests makes the pattern instantly
  recognizable and focuses the reader on *what* is being asserted, not *what the
  variable is called*.
- **Bind a value you both set and assert.** When a test configures a value (a mock
  return value, a config field, an input literal) and later asserts that same value,
  bind it to a local variable and reference that variable in both places. A repeated
  literal can drift; a shared variable can't.
- **Assert against the mock, not the literal you fed it.** Prefer
  `assert result == mock_fetch.return_value` over `assert result == "closed"` when
  `"closed"` holds only because you configured `mock_fetch` with it — the assertion
  should show the code returns *what the collaborator gave it*, not that two copies of a
  literal match. Likewise, pin calls with `assert_called_once_with` / `call_args` rather
  than re-stating the arguments you passed in.
- **Prefer `assert_called_once_with` to checking `call_count`.** Pinning the call
  proves both that it happened exactly once and what it was called with, for the same
  effort as `assert mock.call_count == 1`, which proves only the count. Use `ANY` for
  an argument whose value does not matter but whose presence does.

**Patch targets.** A module named more than once as a `@patch` string becomes a
module-level constant — never a bare repeated literal, and never retyped once the
constant exists (see *Reuse an existing constant* above); named once, it stays inline.
Call these *patch targets*, not "paths." Two tiers, climbed only when you have to:

- **One file uses it** — a private constant in that file, suffixed `_MODULE`:
  `_API_MODULE = "myapp._api"`, used as
  `@patch(f"{_API_MODULE}.requests.get")`.
- **A second file needs the same target** — move first, import after. Promote the
  module to a shared location in the narrowest directory covering its consumers
  (alongside the tests, never inside a `test_*.py`), dropping the underscore to
  `patch_targets.py` *before* the cross-directory import is written, per *Leading
  underscore* above — importing the still-private module from its original directory
  and renaming it later leaves it importable from outside its own directory while still
  marked private, exactly what the underscore promises won't happen. The move changes
  location, not import style: still dotted from `tests` — `from tests import
  patch_targets`, never a bare `import patch_targets`. How a module is imported depends
  on your project layout; this pattern assumes `tests` is a regular package with an
  `__init__.py`.

Either way the `_MODULE` suffix goes — the namespace supplies it, and
`_patch_targets.API_MODULE` stutters the same way `db/db_model.py` does. Module-import
it, since a bare `API` is ambiguous. Name a package constant after the package plus what
it is (`MY_APP_PACKAGE`), never a bare role name — `PACKAGE` alone breaks the moment
there are two:

```python
"""Patch targets for the `myapp` package."""

MY_APP_PACKAGE = "myapp"
```

Per-module targets (`API`, `CURRENT`, ...) aren't centralised here — they're built
where they're consumed, as the `_MODULE`-suffixed constants above.

**Patch target parts.** When a specific patch target (the part after the module — e.g.
`requests.get`, `parse_response`) appears more than once in a file, extract it as a
file-local constant. A single-use patch target goes inline — no constant needed. Do not
repeat the module name in the constant; the module context is already supplied:

```
_API_MODULE = "myapp._api"
_REQUESTS_GET = f"{_API_MODULE}.requests.get"  # not _API_REQUESTS_GET
_PARSE_RESPONSE = f"{_API_MODULE}.parse_response"


@patch(_REQUESTS_GET)
def test_something(mock_get):
    pass


@patch(_PARSE_RESPONSE)
def test_another(mock_parse):
    pass
```

This keeps constants readable and avoids stuttering while making repeated targets
searchable and preventing typos.

**Patch decoration.** When every test method in a class patches the same target,
decorate the class instead of each method — the repetition adds nothing, and a shared
decorator states up front that every test in the class runs under the same assumption.
Class-level mocks arrive as parameters in **bottom-up decorator order**, after `self`
and before any fixture:

```python
@patch(f"{_CURRENT_MODULE}._log")
@patch(f"{_CURRENT_MODULE}.parse_data")
@patch(f"{_CURRENT_MODULE}.fetch_remote_api")
class TestFetchUserData:
    def test_fetches_the_remote_data(
        self,
        mock_fetch_remote_api,
        mock_parse_data,
        mock_log,
    ):
        fetch_user_data()

        mock_fetch_remote_api.assert_called_once_with()
```

Decorate an individual method only when tests in the class mock different targets, or
one test needs a mock the others don't.

**Docstrings in tests:**

- Unit test files: **none**. The name should be self-documenting. This covers test
  class/functions only; a fixture or helper living in the same file is exempt, per the
  fixture rule below.
- Integration test files: **a one-line module docstring is required** — one plain
  sentence, measured against the 88-column limit before finalizing, not estimated by
  eye. Name the entry point under test (always short, always unambiguous) and describe
  the real collaboration in general terms. Don't enumerate every collaborator by name —
  a name-for-name list overclaims (it reads as the complete set, which it rarely is) and
  is the most common way this line runs long. For example:

  ```python
  """Tests `fetch_user_data`, including real fetch and parse errors."""
  ```

  Class and function docstrings still omitted.
- E2e test files: **a one-line module docstring is required**, same rule as above —
  name the entry point, describe it in general terms, measure before finalizing:

  ```python
  """Tests the request handler end to end, from API request to JSON response."""
  ```

  Class and function docstrings still omitted, as with integration.
- `conftest.py`: one-line module docstring required.
- Fixtures, and shared non-test modules like `helpers.py`: full docstring standard, same
  as production code — they are the test suite's public API. **Fixtures always carry a
  docstring, wherever they live**, including inside a `test_*.py`.

**Note:** `per-file-ignores` silences `D100` on `tests/**/test_*.py`, so the required
module docstring on integration and e2e files is **not** machine-checked — it's on
review. A shared module such as `patch_target.py` isn't covered by that ignore, so its
module docstring *is* enforced.

---

## Version control

Branching follows Git Flow — `CONTRIBUTING.md` has the branch structure and the
feature/release/hotfix commands. Work happens on `feature/*`, never directly on `main`
or `develop`.

**Git identity.** Commits, merges and tags on this repository are authored as
`Gregor McIntyre <gregor.mcintyre@aol.co.uk>`, set in the repository-local config —
`git config --local user.name` and `git config --local user.email`. Verify the
configured identity before any commit, merge or tag: a wrong author is baked in at the
moment the object is written, and a feature branch carries it into `develop` on finish.
Fix a mismatch with `--local` only, never `--global` or `--system`, which would
reconfigure every other repository on the machine.

Commits and PRs must **not** carry a `Co-Authored-By: Claude` trailer, a "🤖 Generated
with Claude Code" footer, or any other AI-attribution line.

**Commit messages.** A commit that introduces a new module mirrors that module's
docstring in its subject line — the same summary, the same descriptive voice — and
states whether the module ships with tests. E.g. a module docstring of
`"""Fetches text."""` → `Created a module for fetching text; unit tested.` (or `; not
yet tested.`).

**Supporting modules in commits.** When committing a file, also commit any supporting
modules it imports and any `__init__.py` files from parent packages necessary to access
it — the file and its supporting modules form a logical unit that must be versioned
together, along with the tests for the committed files.

This runs in both directions: a newly introduced or modified shared module brings along
every other new-or-modified file that already imports it, wherever in the tree it lives
— not only within the target's own directory, and not only the file that motivated the
commit. Search the whole tree for consumers (e.g. `git grep` the module name) rather
than checking only the target's own neighbours.

---

## Project layout

There is no single importable package and no `src/` layout — don't introduce one.
Multiple deployment roots (`service_a/`, `service_b/`, etc.) are separate,
flat-imported as needed for their environments, with a `shared/` directory holding code
used by more than one. `pythonpath` and `mypy_path` in `pyproject.toml` let tests import
across roots; a new root must be added to both. Service roots never import each
other — anything they both need lives in `shared/`.

`tests/` mirrors that shape: `tests/<tier>/<root>/...`.

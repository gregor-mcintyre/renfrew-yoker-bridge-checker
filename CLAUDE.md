# renfrew-yoker-bridge-checker

- **What it is:** An Alexa skill that reports when the Renfrew-Yoker pedestrian bridge
  is closed. A Raspberry Pi scrapes the council site on a schedule and caches the result
  in AWS SSM Parameter Store; an AWS Lambda reads that cache to answer voice requests
  inside Alexa's 8-second window.
- **Python:** 3.14

These conventions are the standard for this project. Where existing code or config
disagrees, flag the mismatch — don't imitate it.

On Python 3.14+, never write `from __future__ import annotations`; PEP 649/749 make it
unnecessary.

---

## Enforced by tooling — don't re-litigate

Ruff (lint, format, import sorting, docstring style, naming), mypy (static type
checking), vulture (`--min-confidence 80`) and pytest, all wired through pre-commit.
House defaults: 88 columns, double quotes, Google-style docstrings.

Hooks **report without auto-fixing**. Fix flagged lines by hand, re-stage, re-commit.
Never pass `--fix` or skip a hook to force a commit through.

Actual settings live in `pyproject.toml` and `.pre-commit-config.yaml` — read them
rather than assuming.

Everything below is what those tools *can't* check.

---

## Naming

**Acronyms in CapWords.** Domain proper-noun initialisms keep full caps —
`HTTPClient`, `TestParseCSVHeaders`. Generic abbreviations take a leading capital only —
`db` → `Db`, `id` → `Id`, `ft` → `Ft`. Reword when adjacent initialisms get hard to
parse.

**Leading underscore** marks anything never imported outside its own module —
`_COLUMN_MAP`, `_cleaner.py`. Manual convention, not Ruff-enforced. Doesn't apply to
non-Python files.

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
- **Helpers are defined above the function that call them**, within the same module.
- **No dead code.** Delete zero-reference functions, classes and variables.
- **Break functions into smaller, testable pieces.** Functions and methods should be
  reasonably small and focused so they're easier to unit test. Avoid monolithic
  functions that do too many things — refactor when a function gets hard to test in
  isolation.

---

## Docstrings

Google-style, on every public module, class, function and method. Ruff's `D` rules check
presence and shape; everything below is voice, which they don't check.

- **Descriptive, not imperative** — `"""Fetches rows..."""`, not `"""Fetch rows..."""`.
  Exception: `@property`, phrased as an attribute — `"""The connection timeout."""`
- **Types live in the signature only**, never repeated in the docstring.
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
- **Private (`_`-prefixed) functions** don't strictly need a docstring; add a one-liner
  when the logic isn't obvious.

---

## Testing

| Element                  | Convention                                                                                                                                                       |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Unit test file           | `test_<module>.py`, mirrors source 1:1                                                                                                                           |
| Integration test file    | Named after the primary public entry point under test — not every collaborator, not a sentence. May collide with the unit test filename; the path disambiguates. |
| E2e test file            | Named after the user-facing entry point exercised end to end — the CLI command, script, or handler. Usually one per deliverable.                                 |
| Test function            | `test_<unit>_<scenario>_<expected>`                                                                                                                              |
| Test class               | `Test<ClassName>` — required once an object under test has 2+ tests                                                                                              |
| Fixture                  | `lower_snake_case`, named for what it provides                                                                                                                   |
| Shared helpers/factories | Locality-scoped modules alongside consumers, never in `test_*.py`                                                                                                |
| Mock objects             | `mock_` prefix — `mock_session`                                                                                                                                  |

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

- One `Test<ClassName>` per object under test once it has 2+ cases; single-test cases
  stay standalone functions. Inside a class, names drop `<unit>` →
  `test_<scenario>_<expected>`. Standalone functions keep the full form.
- Order tests negative → positive: errors and edge cases first, happy path last.
- **One test, one reason to fail.** Combined assertions only when the concepts are
  genuinely inseparable.
- Mock where the name is **used**, not where it's defined — including same-module
  private helpers.

**Docstrings in tests:**

- Unit test files: **none**, ever — module, class or function. The name is the
  documentation.
- Integration test files: **a one-line module docstring is required**, naming the real
  collaboration being exercised that unit tests mock out. Class and function docstrings
  still omitted.
- E2e test files: **a one-line module docstring is required**, naming the end-to-end
  path exercised. Class and function docstrings still omitted, as with integration.
- `conftest.py`: one-line module docstring required.
- Fixtures, and shared non-test modules like `helpers.py`: full docstring standard, same
  as production code — they are the test suite's public API.

**Note:** `per-file-ignores` silences `D100` on `tests/**/test_*.py`, so the required
module docstring on integration and e2e files is **not** machine-checked. It's on
review.

<!-- ── Everything above is the shared base; project-specific notes go below ── -->

---

## Project layout

There is no single importable package. `shared/`, `pi_refresher/` and `alexa_lambda/`
are three separate deployment roots (Pi cron job, AWS Lambda zip), each flat-imported
the way Lambda expects. `pythonpath` and `mypy_path` in `pyproject.toml` are what let
tests import across them without a `src/` layout.

---

## Version control

Commits and PRs in this repo must **not** carry a `Co-Authored-By: Claude` trailer, a
"🤖 Generated with Claude Code" footer, or any other AI-attribution line. GitHub's
contributor graph treats a co-author trailer as a real contributor, and once indexed the
listing does not reliably clear even after the trailer is removed by rewriting history —
so the only fix is never adding one.

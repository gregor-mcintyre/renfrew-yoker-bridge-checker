# renfrew-yoker-bridge-checker

- **Git identity:** Gregor McIntyre <gregor.mcintyre@aol.co.uk>
- **What it is:** An Alexa skill that reports when the Renfrew-Yoker pedestrian bridge
  is closed. A Raspberry Pi scrapes the council site on a schedule and caches the result
  in AWS SSM Parameter Store; an AWS Lambda reads that cache to answer voice requests
  inside Alexa's 8-second window. The Lambda isn't in the repository yet, though
  `pyproject.toml` already lists its `alexa_lambda` root.
- **Python:** 3.14
- **Test conventions:** `tests/CLAUDE.md`. The rules here govern test code too, except
  where that file overrides them — it is the only place test rules live.

On Python 3.14+, never write `from __future__ import annotations`; PEP 649/749 make it
unnecessary.

---

## Commands

Run these, and the test commands in `tests/CLAUDE.md`, from the repository root with
`.venv` activated.

| Task              | Command                                           |
|-------------------|---------------------------------------------------|
| Every hook        | `pre-commit run --all-files`                      |
| Lint / format     | `ruff check --no-fix .` / `ruff format --check .` |
| Type-check        | `mypy .`                                          |
| Dead code         | `vulture --min-confidence 80 .`                   |

---

## Enforced by tooling — don't re-litigate

Ruff (lint, format, import sorting, docstring style, naming), mypy (static type
checking), vulture (`--min-confidence 80`), the pytest suite and a CRLF line-ending
check, all wired through pre-commit. House defaults: 88 columns, double quotes,
Google-style docstrings.

Ruff's `COM812` requires a trailing comma on any construct that spans lines, and the
formatter's magic trailing comma then holds it open — so **a wrapped signature or call
puts one argument per line**.

Hooks **report without auto-fixing** — fix flagged lines by hand; never pass `--fix`.

Actual settings live in `pyproject.toml` and `.pre-commit-config.yaml` — read them
rather than assuming.

Everything below is what those tools *can't* check.

---

## Naming

**Acronyms in CapWords.** Domain proper-noun initialisms keep full caps — `HTTPClient`,
`CSVWriter`. Generic abbreviations take a leading capital only — `db` → `Db`, `id` →
`Id`, `ft` → `Ft`. Reword when adjacent initialisms get hard to parse.

**Leading underscore** marks a name — constant, function, module, or package directory —
never imported outside its own directory: `_CONFIG_PATH`, `_validators.py`. Extra
importers *inside* that directory don't matter — the mark tracks where a name is
reachable from, not how often it's used. It's wrong only once a name is imported from a
directory that is neither the defining one nor one `tests/CLAUDE.md` treats as part of
it. A package directory earns the underscore the same way — a subpackage nothing outside
its parent imports. Manual convention, not Ruff-enforced; doesn't apply to non-Python
files.

**Module names.** Name by subject or shape, never a bare imperative verb — a module is a
namespace read at the call site, so `validate.validate_email(x)` stutters while
`validators.email(x)` doesn't. Pick whichever fits the content:

- **Domain noun** — `billing`, `routing` — functions share a subject, not a shape.
- **Gerund / action noun** — `parsing`, `serialization` — related operations on varied
  inputs.
- **Plural agent noun** — `validators`, `converters` — interchangeable members of a
  family.
- **Singular agent noun** — `parser`, `scheduler` — one coherent thing, often built
  around a single class.

Never `manager`/`handler` as a module name, and never `utils`/`helpers`/`common`/`misc`
— see *No generic `utils/`* below. If a `db` package already exists, a models module is
`db/models.py`, not `db_model.py` at the top level — avoid repeating the package name in
its own submodule.

---

## Code style

- **Imports:** object-import by default. Module-import is the exception, earned only
  when the bare name is genuinely ambiguous or generic out of context — not merely
  because a prefix could add *some* context, which is true of almost any name. A
  constant like `TIMEOUT` only reads as whose timeout once qualified, so
  `config.TIMEOUT` earns the module-import; `parse_response` stays object-imported even
  though `parsers.parse_response` would add context too — the bar is genuine ambiguity,
  not mere possibility. Be consistent per-name — mixing styles across the codebase is
  fine.
- **Arguments:** positional for short, unambiguous calls; keyword at 3+ args, for
  booleans, or for same-typed args; keyword-only (`*,`) for flags and config params.
- **No generic `utils/`.** Name modules by function. Only introduce `utils/` once there
  are enough small unrelated helpers to warrant it, then split by topic.
- **`__init__.py` files are always empty** — re-exports go elsewhere.
- **Helpers are defined above the function that calls them**, within the same module,
  ordered by when that function first uses them.
- **No dead code.** Delete zero-reference functions, classes and variables.
- **Break functions into smaller, testable pieces** — small and focused, and refactored
  once one gets hard to unit test in isolation.
- **Separate logical blocks with blank lines** — related statements grouped, a blank
  line between distinct units, e.g. between an early-return guard and the main logic.
- **Don't restate default arguments** — with `func(min=0)`, call `func()`, not
  `func(min=0)`. Method defaults too — `body.encode()`, not `body.encode("utf-8")`;
  `d.get(key)`, not `d.get(key, None)`. Ruff's `UP012` catches only the string-literal
  form (`"...".encode("utf-8")`), so the variable form is on review.
- **Reuse an existing constant instead of retyping its literal.** If a name already
  captures a value the code needs — even as part of a longer string — reference the
  name; don't retype the literal. `_BASE_URL + "/status"`, not
  `"https://example.invalid/status"` — the second retypes a literal the first constant
  already owns, and the two copies can drift the moment the host changes. Nothing
  catches this; it's on review.
- **Inline single-use variables** unless inlining hurts readability — as when the
  binding names an otherwise opaque expression. `year_str = str(year)`, used once, adds
  nothing: inline it. `parsed_date = parse_iso_date(raw_input)`, used once, clarifies
  intent: keep it.

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
- **Single backticks for code references** in prose — variable, class, method,
  library, package and tool names, plus `None` and literal numbers: `my_var`, `MyClass`,
  `None`, `42`, `my_lib`. Not for string literals, unless specifying a particular
  string value.
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

## Project layout

There is no single importable package and no `src/` layout — don't introduce one.
Multiple deployment roots (`service_a/`, `service_b/`, etc.) are separate, flat-imported
as needed for their environments, with a `shared/` directory holding code used by more
than one. Service roots never import each other — anything they both need lives in
`shared/`.

The test tree mirrors this shape; `tests/CLAUDE.md` defines it, along with the
`pyproject.toml` settings a new deployment root must be added to.

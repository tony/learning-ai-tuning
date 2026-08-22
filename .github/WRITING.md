# Writing

How this project writes prose, for humans and agents alike. It governs
`README.md`, commit messages, docstrings, source comments, and notebook
markdown cells (`mo.md()` blocks) — every surface a reader reaches.

For environment setup, the gates, and pull request workflow, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Voice

Three surfaces, one voice. A docstring says what a caller may rely on; a
commit message says why a change was made; prose says what happens. All are
present tense, lead with the thing being described, and stop. Why it was built
that way belongs in the commit message, which is timestamped and attached to
the diff.

The most useful editing operation is deleting the introductory sentence.

Lead with verbs and name concrete things. Put identifiers in backticks. Prefer
short declarative sentences, one operational fact each. Do not explain Python
to Python developers; do explain this project's semantics.

Type annotations describe shape. Documentation describes meaning. A sentence
that restates a signature has said nothing.

Use MUST, SHOULD, and MAY only where the normative sense is meant. Say what
actually happens rather than that something is "supported".

| Instead of                       | Prefer                             |
| --------------------------------- | ----------------------------------- |
| "We added…"                      | "The harness now logs…"            |
| "New and improved"               | "`check_licenses.py` now flags…"   |
| "powerful", "seamless"           | state the capability               |
| "easily", "simply", "just"       | omit                                |
| "simple", "obvious", "intuitive" | omit                                |
| "robust"                         | name the failure that is handled   |
| "comprehensive"                  | name what is covered               |
| "production-ready"               | state the guarantee                |
| "optimized", "blazingly fast"    | give the magnitude                 |
| "various fixes"                  | name the components                |
| "under the hood"                 | omit unless observable             |
| "please note that", "note that"  | state the fact                     |
| "leverage", "utilize"            | "use"                               |
| "delve into"                     | "read", or omit                    |
| "best practices"                 | name the practice                  |
| "in order to"                    | "to"                                |

## Who you are writing for

The default reader is fluent in Python and new to this study track. They can
read a signature; they cannot guess why D1 comes before D2, or what a notebook
does without opening it. Serve them first.

A second, smaller reader works on the harness internals or the license-check
script; mark their material opt-in — "for the rarer cases", "advanced" — so
the default reader knows they can stop.

- **Second person, present tense, active.** "You run the notebook headlessly",
  not "The notebook is run".
- **Concept before mechanics.** Open by saying what a notebook teaches and why
  it sits where it does in the D1 → D2 → D3 spine. The command to run it is
  the last detail, not the first.
- **Progressive disclosure.** Order by how many readers need it: the quick
  command, then the one flag a few will tune, then the lower-level detail.
- **Name the trade-off.** If a call costs something — a model download, a
  sandboxed dependency resolve — say so, and say what it buys.

## README

A README is the shortest path from "what is this?" to competent use, not the
project's autobiography. The first sentence is a contract: it says what the
reader has been handed, concretely enough to tell this repository apart from
its sibling.

Get to a runnable command before anything the reader can skip. State the
minimum Python version in prose — `requires-python` in `pyproject.toml` is
the authority; the README must agree with it.

Examples must be real, runnable commands — never `your-command
<some-options>`. This repository does not execute documentation examples as
tests; see [Documented examples that run](#documented-examples-that-run) for
what "runnable" means here. Headings stay conventional and stable, because
people deep-link them.

## Documented examples that run

Elsewhere in this fleet, a `>>> ` prompt inside a fenced block is collected
and executed by `pytest`. **That mechanism does not exist in this
repository**: `pyproject.toml` carries no `[tool.pytest.ini_options]` table,
there is no `testpaths`, no `doctest_optionflags`, and no `conftest.py`. There
are zero `>>> ` prompts anywhere in the source. A fenced code block in
`README.md`, `AGENTS.md`, `.github/*.md`, or a notebook's `mo.md()` cell is
illustrative: a reader copies it and runs it themselves, but nothing in CI
runs it for them.

The one thing that does execute is a notebook's own `test_*` cell: `pytest`
imports the notebook module directly and collects any function named
`test_*` (see `just test` in [CONTRIBUTING.md](CONTRIBUTING.md#tests)). That
is a notebook self-test, not a documented example — it carries no `>>> `
prompt, does not live in `README.md`, and is not part of `just check`.

If a doctest-backed example is ever added here, give the fence the `python`
tag, use `>>> ` prompts, and add the matching `[tool.pytest.ini_options]`
table before relying on it — a fenced block with no prompt does not run
regardless of its tag, in this repository or any other.

## Docstrings

The prime directive: never restate the type. The annotation is the source of
truth; the docstring carries what the annotation cannot.

This is documentation debt wearing a docstring:

    def notebook_deps(path: Path) -> list[str]:
        """Get a notebook's dependencies.

        Parameters
        ----------
        path : Path
            The notebook path.

        Returns
        -------
        list[str]
            The dependencies.
        """

Document instead the dimensions the type system cannot encode: mutation,
ownership, ordering, timing, failure, idempotence, units and ranges, boundary
behaviour, and platform differences. The ambiguity worth resolving by example:
whether "retry three times" means three attempts or four. State it.

The first sentence stands alone; tooling truncates there. PEP 257 applies:
triple double quotes, an imperative one-line summary ending in a period, a
blank line before any extended description. `ruff`'s `D` rules enforce the
NumPy convention (`[tool.ruff.lint.pydocstyle] convention = "numpy"`) — one
dialect, enforced by the linter rather than relitigated in review.

**Classes with fields** — `NamedTuple`, dataclasses — document every field in
an `Attributes` section:

    class RunConfig(NamedTuple):
        """Settings one tuning run was launched with.

        Attributes
        ----------
        base_model : str
            Model id the run started from.
        epochs : int
            Passes over the training set.
        """

A type says how a field is shaped, not what it holds. Describing each one
keeps that meaning next to the code, and anything that renders the class —
a REPL, an editor tooltip — has a description to show instead of a bare name.

**Every `@app.function` and `@app.class_definition` carries a docstring.**
marimo's Documentation panel renders it; an undocumented cell function shows
nothing there.

## Source comments

A comment ships only if it passes all three gates. Fail any: delete or
rewrite. Borderline: delete — borderline means the information is
reconstructible, which is what makes deletion cheap.

**Loss.** Three years from now, would losing this cost a maintainer real time
rediscovering intent, an invariant, a constraint, or a failure mode the code
and tests do not already make obvious?

**Elite.** Would SQLite, Redis, the Go standard library, or CPython write this
comment, at this length? Those projects state the constraint and stop. They do
not argue with an imagined objector.

**Upkeep.** Will it stay true without maintenance? A comment that hand-syncs a
value the code owns — a count, an offset, a line reference, a duplicated
constant — is false the first time that value moves.

### Ceiling

One or two lines. A comment reaching four is either carrying several facts, in
which case split it, or arguing, in which case cut it to the fact.

Rationale, alternatives weighed, and the story of how the code got here belong
in the commit message: timestamped, attached to the exact diff, and free to
maintain.

A comment often holds both a constraint and the deliberation that found it.
Keep the constraint, cut the deliberation. "Runs at most once per second"
survives; "this is the right trade for now" does not.

### Keep

- Why over how: upstream quirks, protocol and compatibility constraints,
  performance tradeoffs still part of the contract.
- Invariants, preconditions, ordering, lifetime, and concurrency requirements
  that types and tests cannot express.
- Code that looks wrong but is not, so a later cleanup does not reintroduce
  the bug.
- A high-level sketch of an algorithm whose local operations do not reveal the
  whole.

### Delete

- Narration of the next lines; code translated into English.
- Restated names, types, defaults, or control flow.
- Values duplicated from the code and hand-synced.
- Justification, hedging, or apology for a choice.
- Speculation about future requirements.
- History version control already holds, including commented-out code.
- Ticket and issue numbers. They say nothing to a reader without tracker
  access, and they rot when the tracker moves. Unfinished work goes in the
  tracker, not the source.
- Transient observations — "currently", "for now", "the latest release" —
  that go stale with no nearby edit.

### The upkeep gate in practice

It reaches values that track our own code. It does not reach frozen external
facts.

Bad (Delete):

    # There are 321 tests to complete for servers.

Good (Keep):

    # CPython < 3.11 has no ExceptionGroup, so this branch stays.

### Documentation exception

Minimal usage examples, and parameter, return, and raises entries on public
API are exempt from the loss gate — they serve the caller, not the
maintainer. They are exempt from nothing else. Ceiling: a good man page entry.

## Terminology and capitalization

Pick the domain noun and keep it. A notebook is a "notebook", not a "script"
in one paragraph and an "nb" in the next. A CI check is a "gate" — the word
`justfile` and `AGENTS.md` already use — not a "check" in one paragraph and a
"gate" in the next.

Python and PyPI keep their own capitalisation. Distribution names are written
as they are published.

Do not write counts into prose — how many notebooks exist, how many tests
there are. They go stale silently and no reader needs them.

## Markdown

Prose wraps at 80 columns. Table rows, badge lines, and long links are exempt,
because breaking them harms rendering.

GitHub alert blocks — `> [!NOTE]`, `> [!WARNING]` — render as literal text
outside GitHub, so reserve them for at most one load-bearing warning per
document.

**Notebook markdown.** marimo's outline panel reads headings (`h1`–`h6`) from
rendered `mo.md()` cells — give every teaching section a `##` heading.
Headings inside accordions, tabs, or carousels are excluded from the outline;
keep those in plain markdown cells instead.

Do not use a local absolute path or an email address in anything published.

## Code blocks

Code blocks are paste-and-run units: pasting one block runs exactly one
intended action.

- **One command per block.** Multiple steps may share a block only when
  explicitly chained with `&&`, `;`, or `\` continuations — the chain is then
  one logical command.
- **Explanations go in prose above the block**, never as `#` comments inside
  it.
- **Command menus are per-command blocks with prose lead-ins**, not tables.
- **Shell commands use the `console` tag with a `$ ` prefix.** This separates
  interactive commands from scripts and enables prompt-aware copy.
- **Split long commands with `\`** — one flag or flag+value pair per indented
  continuation line, positional arguments last.

Good — show the last ten commits as a graph:

```console
$ git log \
    --max-count=10 \
    --graph \
    --oneline
```

Bad:

```console
# Show the last ten commits as a graph
$ git log --max-count=10 --graph --oneline
```

## Commits

```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific technical changes made
- Focused on a single topic
```

Keep the subject to 50 characters or fewer, excluding any trailing `(#NN)`
pull request reference, and wrap body lines at 72. Separate the `why:` and
`what:` blocks with a blank line.

Subjects are plain English. Never put curriculum codes (`D1`, `D2`, `D3`) or
other repo-internal shorthand in the subject line — a reader of `git log
--oneline` should understand every title cold.

Routine maintenance commits drop the colon and take a capitalised
description, which is what distinguishes them at a glance in `git log
--oneline`:

```
py(deps[dev]) Bump dev packages
ai(rules[AGENTS]) Judge comments by three gates
```

Everything that changes behaviour keeps the colon.

Common types:

- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **ci**: Workflow and pipeline changes
- **py(deps)**: Dependencies
- **py(deps[dev])**: Dev dependencies
- **ai(rules[AGENTS])**: AI rule updates

Example:

```
eval(feat[harness]): Add F1 regression gate to the D1 notebook

why: Catch a metric regression before it reaches a written note.

what:
- Add a threshold check against the notebook's stub baseline
- Append the pass/fail result to the JSONL experiment log
```

For a multi-line message, use a heredoc so the formatting survives:

```console
$ git commit -m "$(cat <<'EOF'
Scope(feat[detail]): Concise description

why: Explanation of the change.

what:
- First change
- Second change
EOF
)"
```

## Slop prevention

Treat AI slop as review-hostile noise, not as proof that text or code is
wrong. The goal is to maximise information density.

- **AI signatures.** No "Generated by", no conversational filler, no
  unexplained emoji, no tool metadata.
- **Brittle references.** No hard-coded line numbers, fragile file counts,
  dated "as of" claims, bare SHAs, or local absolute paths — unless they are
  strict evidentiary artefacts such as a benchmark log.
- **Diff narration.** Do not restate what moved, was renamed, or was removed
  in anything the reader holds alongside the diff: code, docstrings, README,
  or a pull request description. The diff and the commit message already
  carry it.
- **Branch-internal narrative.** Do not mention intermediate states,
  abandoned approaches, or "no longer" behaviour unless a reader of the
  current `master` actually experienced the old state.
- **Low-value scaffolding.** No ownerless TODOs, unused future-proofing,
  debug artefacts, or defensive wrappers around failure modes nothing can
  reach.
- **Prose inflation.** The diction table under [Voice](#voice) governs;
  replace an inflated word with a concrete description of behaviour,
  constraints, or trade-offs.
- **Coded labels.** Write rules and findings as plain imperatives. No `[R1]`,
  `Option B`, or any index a reader has to decode.

**Durable source links.** Link to a pinned revision, never to trunk, when
citing another project's source — a permalink, not an unlinked SHA. Prefer a
release tag; otherwise a 7-character commit ref reachable from that project's
trunk, never a PR-head SHA (it can be rebased or garbage-collected). Line
anchors (`#L120-L145`) are only safe on a pinned ref. Reserve an unpinned
`blob/main/…`-style link for a living document meant to always show the
latest state.

Preserve the "why". Never delete a comment documenting an invariant, a
protocol constraint, a platform quirk, or an upstream workaround — those are
the facts [Source comments](#source-comments) keeps, and every other comment
is judged by it.

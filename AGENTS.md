# AGENTS.md

This file provides guidance to coding agents (and humans) working in this repository.

## What This Repo Is

The **Domain D (AI Tuning)** study track: marimo notebooks for learning evaluation
harnesses, fine-tuning (SFT/PEFT/LoRA/QLoRA), and alignment (DPO/RLHF) hands-on.
Companion to [`learning-notebooks`](https://github.com/tony/learning-notebooks)
(local sibling clone: `../learning-notebooks`) — same method: each
notebook is a self-contained, pure-Python file carrying its own dependencies via
PEP 723 inline script metadata, run in an isolated uv environment (`--sandbox`).

The track spine lives in `notes/progression.md`: **D1 (eval harness) → D2
(fine-tuning) → D3 (alignment)** — you can't tune what you can't measure, so D1
comes first. The cross-corpus index is `../learning-notebooks/notes/taxonomy.md`.

## Development Commands

### Essential Commands

Install dev tooling (marimo CLI, ruff, ty):

```bash
uv sync
```

Open a notebook in the editor, in its own isolated env:

```bash
uv run marimo edit --sandbox notebooks/eval/001_eval_harness.py
```

Run a notebook headlessly as a script:

```bash
uv run notebooks/eval/001_eval_harness.py
```

Run `test_*` cells — pytest imports the notebook, which executes its setup
cell, so the notebook's PEP 723 deps must be passed via `--with` (or use
`just test <notebook>`):

```bash
uv run --with pytest --with scikit-learn pytest notebooks/eval/001_eval_harness.py
```

Lint, format, and type check:

```bash
uv run ruff check .; \
uv run ruff format .; \
uv run ty check
```

marimo's notebook-aware linter:

```bash
uv run marimo check --strict notebooks/
```

License deny-list guard:

```bash
uv run scripts/check_licenses.py
```

## Project Structure

- `notebooks/eval/` — D1: metrics, eval suites, regression gates, experiment logs
- `notebooks/finetuning/` — D2: SFT → LoRA → QLoRA (heavy; never in CI smoke list)
- `notebooks/alignment/` — D3: reward models → DPO → RLHF (heavy; never in CI)
- `notes/progression.md` — the D1→D2→D3 study spine
- New notebooks start from `../learning-notebooks/notes/notebook_template.py`

## Authoring Rules

- Same marimo rules as `learning-notebooks/AGENTS.md` (DAG rule, last expression
  is the output, no IPython magics, gate expensive work with `mo.ui.run_button()`
  + `mo.stop()`, wrap model loads in `@mo.persistent_cache`).
- **Execution modes**: notebooks here use tiny proxy models or stubbed logits
  in-sandbox; real multi-GPU runs live outside the sandbox. Never in-sandbox
  monoliths.
- **License policy**: PEP 723 deps must be permissive (MIT/BSD/Apache-2.0/PSF/ISC);
  MPL-2.0 is dev/test-only (flagged). Model weights and datasets carry licenses
  too — prefer Apache-2.0/MIT weights (Qwen, OLMo) and CC0/CC-BY data; keep
  Llama/Gemma-style community licenses and NC datasets out of automated runs.
- **CI-safety**: only light notebooks (no model downloads, deps install in
  seconds) go in the CI smoke-run list. D2/D3 notebooks are heavy by nature —
  exclude them.
- **Outline panel reads markdown headings** (h1–h6) from rendered md cells — give
  every teaching section a `##` heading. Headings inside accordions/tabs/carousels
  are excluded from the outline; keep them in plain md cells. Every `@app.function`
  and `@app.class_definition` carries a docstring (the Documentation panel shows it).
- **Doc style — code blocks are paste-and-run units**: one command per
  triple-backtick block, so pasting a block runs exactly one intended action.
  Don't blur multiple commands annotated by comments into the same block —
  explanations belong in prose above it. A multi-step sequence may share a
  block only when explicitly chained with `;` / `; \` (the chain *is* the
  single action). Command menus are per-command blocks with prose lead-ins,
  not tables.

## Quality Gates (before committing a notebook)

1. `uv run <notebook>.py` exits 0 (headless script run).
2. `uv run ruff check .` and `uv run ruff format .` pass.
3. `uv run ty check` passes.
4. `uv run marimo check --strict notebooks/` passes.
5. `uv run scripts/check_licenses.py` passes (license deny-list).
6. No absolute local paths or PII (`git grep '/home/'` stays empty).

## Git Commit Standards

Format commit messages as:

```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific technical changes made
- Focused on a single topic
```

The blank line between the `why:` block and the `what:` block is
optional — useful when the `why:` body runs to multiple lines and the
two sections benefit from visual separation.

Common commit types:

- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **py(deps)**: Dependencies
- **py(deps[dev])**: Dev Dependencies
- **ai(rules[AGENTS])**: AI rule updates
- **ai(claude[rules])**: Claude Code rules (CLAUDE.md)

Subjects are plain English. Never put curriculum codes or other
repo-internal shorthand in the subject line — a reader of
`git log --oneline` should understand every title cold.

Example:

```
config(feat[merge]): Add deep-merge support for theme options

why: Enable per-project theme overrides without replacing entire dict

what:
- Add deep_merge() helper for nested dict merging
- Update merge_sphinx_config() to deep-merge theme_options
- Add tests for nested override behavior
```

For multi-line commits, use heredoc to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
Scope(type[detail]): concise description

why: Explanation of the change.

what:
- First change
- Second change
EOF
)"
```

## AI Slop Prevention

Treat AI slop as **review-hostile noise**, not as proof that text or
code is wrong. The goal is to maximize information density by removing
artifacts that make the repository harder to trust or navigate.

### The Anti-Slop Rubric

Before committing, audit all AI-assisted changes for these noise
patterns:

- **AI Signatures:** Remove "Generated by", footers, conversational
  filler ("Certainly!", "Here is..."), unexplained emojis (🤖, ✨), and
  AI-tool metadata.
- **Brittle References:** Avoid hard-coded line numbers, fragile
  file/test counts, dated "as of" claims, bare SHAs, and local
  absolute paths unless they are strict evidentiary artifacts (e.g.,
  benchmark logs).
- **Diff Narration:** Do not restate what moved, was renamed, or was
  removed in artifacts the downstream reader holds: code, docstrings,
  README, CHANGES, PR descriptions, or release notes. The diff and
  commit message already carry this history.
- **Branch-Internal Narrative:** Do not mention intermediate branch
  states, abandoned approaches, or "no longer" behavior unless users
  of a published release actually experienced the old state (**The
  Published-Release Test**).
- **Low-Value Scaffolding:** Remove ownerless TODOs (`TODO: revisit`),
  unused future-proofing, debug artifacts, and defensive wrappers that
  do not protect a currently reachable failure mode.
- **Prose Inflation:** Replace generic AI "tells" like *comprehensive,
  robust, seamless, production-ready, leverage, delve, tapestry,* and
  *best practices* with concrete descriptions of behavior,
  constraints, or trade-offs.

### Preservation & Context

**When unsure, leave the text in place and ask.** Subjective cleanup
must never be a reason to remove load-bearing rationale.

- **Preserve the "Why":** You MUST NOT delete comments that document
  invariants, protocol constraints, platform quirks, security
  boundaries, and upstream workarounds.
- **Evidence is Immune:** Preserve exact counts, dates, and SHAs when
  they serve as evidence in benchmark results, release notes, stack
  traces, or lockfiles.
- **Behavior Over Inventory:** A useful description explains what
  changed for the *system or user*; it does not provide an inventory
  of files or functions the diff already shows.

### The Published-Release Test

Long-running branches accumulate tactical decisions — renames,
refactors, attempts-then-reverts. When deciding what counts as
branch-internal, use trunk or the parent branch as the baseline — not
intermediate states inside the current branch. Ask:

> Did users of the most recently published release ever experience
> this old name, old behavior, or bug?

If the answer is **no**, it is branch-internal narrative. Move it to
the commit message and describe only the final state in the artifact.

**Keep in shipped artifacts:**

- Deprecations and migration guides for symbols that actually shipped.
- `### Fixes` entries for bugs that affected users of a published
  release.
- Comments explaining *why the current code looks this way*
  (invariants, platform quirks) that make sense to a reader who never
  saw the previous version.

### Cleanup in Hindsight

When applying these rules retroactively from inside a feature branch,
first establish scope by diffing against the parent branch (or trunk)
to identify which commits this branch actually introduced. Then:

- **In-branch commits:** Prompt the user with two options: `fixup!`
  commits with `git rebase --autosquash` to address each causal commit
  at its source, or a single cleanup commit at branch tip.
- **Trunk/Parent commits:** Default to leaving them alone. Act only on
  explicit user instruction. If the user opts in, fold the cleanup
  into a single commit at branch tip; do not rewrite shared history.
- **Scope guard:** If cleaning prior slop would touch a colleague's
  work or expand the branch beyond its stated goal, stay in lane:
  protect the current goal and leave prior slop alone.

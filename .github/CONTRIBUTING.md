# Contributing

Thanks for looking. This is a personal study repository and is not seeking
outside contributions, but an issue reporting a broken notebook, a licensing
gap, or a place the notes mislead you is useful.

How this project writes prose — README, commit messages, docstrings, and
source comments — is set out separately in [WRITING.md](WRITING.md). Read
that before changing any of it. The constraints every change is held to, and
the map of what is where, are in [AGENTS.md](../AGENTS.md).

## Getting set up

```console
$ uv sync
```

## The gates

CI is the order of record; every gate it runs has to pass before a change is
done.

Lint:

```console
$ uv run ruff check .
```

Format check:

```console
$ uv run ruff format --check .
```

Type check:

```console
$ uv run ty check
```

CI runs the type check as two scoped passes instead of one — `ty check notes
scripts`, then `ty check notebooks --ignore unresolved-import --ignore
unresolved-attribute` — because a notebook's PEP 723 dependencies are not
installed into the `uv sync` environment that a bare `ty check` scans, and
that bare form reports them as unresolved imports.

marimo's notebook-aware linter, scoped to `.py` notebooks:

```console
$ uv run marimo check --strict notebooks/
```

License deny-list, scanning every notebook's PEP 723 dependencies:

```console
$ uv run scripts/check_licenses.py
```

All of the above, in the order CI runs them:

```console
$ just check
```

Neither `just check` nor CI checks for a leaked local path — run this
yourself before committing; it must stay empty:

```console
$ git grep '/home/'
```

This repository has no doctest gate — see
[WRITING.md](WRITING.md#documented-examples-that-run) for why. Before
claiming a gate works, show it failing. A gate that has never been red is an
assumption.

## Tests

A notebook's tests are `test_*` functions inside its own cells. `pytest`
imports the notebook directly, which runs its setup cell — so the
notebook's PEP 723 dependencies must be present, passed via `--with`:

```console
$ just test notebooks/eval/001_eval_harness.py
```

The default extra dependency is `scikit-learn`, which fits
`001_eval_harness.py`. A notebook with a different PEP 723 dependency needs
its own `--with`, passed as the second argument:

```console
$ just test notebooks/eval/004_duckdb_analytics.py '--with duckdb'
```

**`test_*` cells are not part of CI.** CI only smoke-runs the light D1
notebooks headlessly (`uv run notebooks/eval/00N_*.py`), to prove they
execute without a model download; it does not collect or run any `test_*`
cell. Run `just test` locally before relying on one.

D2 (fine-tuning) and D3 (alignment) notebooks are heavy by nature — model
downloads, GPU — and never join the CI smoke-run list.

## Pull requests

One subject per pull request. Unrelated cleanup found along the way belongs in
its own commit, and usually in its own pull request.

Discuss a substantial change via an issue before making it.

Commit format is in [WRITING.md](WRITING.md#commits).

## Decorum

- Participants will be tolerant of opposing views.
- Participants must ensure that their language and actions are free of personal
  attacks and disparaging personal remarks.
- When interpreting the words and actions of others, participants should always
  assume good intentions.
- Behaviour which can be reasonably considered harassment will not be tolerated.

Based on [Ruby's Community Conduct Guideline](https://www.ruby-lang.org/en/conduct/).

## Security

Please do not open a public issue for a vulnerability. Report it through
GitHub's private vulnerability reporting on this repository (the Security tab
→ "Report a vulnerability") instead.

# AGENTS.md

Personal study repo for Domain D (AI tuning): marimo notebooks on eval
harnesses (D1), fine-tuning (D2: SFT/PEFT/LoRA/QLoRA), and alignment (D3:
DPO/RLHF). Companion to [`learning-notebooks`](https://github.com/tony/learning-notebooks)
(sibling clone at `../learning-notebooks`), which holds the cross-corpus
taxonomy and architecture studies.

Follow the conventions already in the tree, and keep a change scoped to what
was asked for.

## What is here

| Path                         | What it is                                            |
| ----------------------------- | ------------------------------------------------------ |
| `notebooks/eval/`            | D1: metrics, eval suites, regression gates, experiment logs |
| `notes/progression.md`       | the D1 → D2 → D3 study spine                          |
| `notes/storage-design.md`    | run-store design rationale                            |
| `scripts/check_licenses.py`  | license deny-list gate for notebook PEP 723 deps      |
| `justfile`                   | task runner: edit/run/test notebooks, quality gates   |

`notebooks/finetuning/` (D2) and `notebooks/alignment/` (D3) do not exist
yet; `notes/progression.md` tracks what each topic still needs.

## Which policy applies

- Documentation, user-facing text, commit messages, docstrings, and source
  comments: [.github/WRITING.md](.github/WRITING.md)
- Environment, the gates, tests, and pull requests:
  [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)

Each of those is the single home for its subject. Where a rule seems to be
stated twice, the file listed above is the one that governs.

## Change discipline

- Make the smallest coherent change that solves the verified problem; keep
  unrelated cleanup out of it.
- Reuse an existing file, helper, or notebook pattern before adding a new one.
- Add a file only for a durable boundary — a distinct responsibility,
  independent reuse, or splitting an oversized module — not for a single-use
  helper or a one-line re-export.
- A passing gate is evidence only once it has been shown capable of failing.

## Domain facts

- Notebooks use tiny proxy models or stubbed logits in-sandbox; real
  multi-GPU runs happen outside `uv --sandbox`.
- Only light notebooks (no model download, deps install in seconds) join the
  CI smoke-run list; D2/D3 notebooks are heavy by nature and stay out of it.
- PEP 723 notebook dependencies must be permissively licensed
  (MIT/BSD/Apache-2.0/PSF/ISC); MPL-2.0 is dev/test-only. Model weights and
  datasets carry licenses too — prefer Apache-2.0/MIT weights and CC0/CC-BY
  data; keep community-license weights (Llama/Gemma-style) and NC datasets
  out of automated runs.
- Marimo conventions (DAG rule, no IPython magics, gate expensive work
  behind `mo.ui.run_button()` + `mo.stop()`, cache model loads with
  `@mo.persistent_cache`) follow `../learning-notebooks/AGENTS.md`.

## References

- [`learning-notebooks`](https://github.com/tony/learning-notebooks) — sibling
  repo, cross-corpus taxonomy and architecture studies
- [marimo](https://github.com/marimo-team/marimo)
- `notes/progression.md` — the study spine

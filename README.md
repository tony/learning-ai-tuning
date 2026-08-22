# learning-ai-tuning

Domain D study track: **AI tuning** via
[marimo](https://github.com/marimo-team/marimo) notebooks — evaluation harnesses
(D1), fine-tuning (D2: SFT/PEFT/LoRA/QLoRA), and alignment (D3: DPO/RLHF).
Requires Python 3.13 or newer.

Spine: `notes/progression.md`. Method and conventions: `AGENTS.md` (mirrors
[`learning-notebooks`](https://github.com/tony/learning-notebooks), the home of
the cross-corpus taxonomy index; its local clone lives as a sibling at
`../learning-notebooks`).

## Quick Start

Browse the notebooks in marimo's directory gallery — zero install, prints a URL
instead of opening a browser:

```console
$ uvx marimo edit --headless notebooks/
```

Open a notebook in its own isolated environment:

```console
$ uvx marimo edit --sandbox --headless notebooks/eval/001_eval_harness.py
```

Run it headlessly as a script:

```console
$ uv run notebooks/eval/001_eval_harness.py
```

(With dev tooling installed — `uv sync` — swap `uvx marimo` for
`uv run marimo`.)

### Optional: just

[just](https://github.com/casey/just) is an optional convenience — every recipe
is a thin wrapper over the plain commands above. Type `just` by itself to list
the quick commands.

The gallery, as above:

```console
$ just gallery
```

Editor — prints the URL, no browser:

```console
$ just edit notebooks/eval/001_eval_harness.py
```

Run a notebook's `test_*` cells:

```console
$ just test notebooks/eval/001_eval_harness.py
```

All quality gates:

```console
$ just check
```

Notebook arguments are real paths, so your shell tab-completes them by track
(`just edit notebooks/eval/<TAB>`) with zero setup. Optional recipe-name
completion: `eval "$(just --completions zsh)"` (also bash/fish/powershell/…).

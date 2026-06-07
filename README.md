# learning-ai-tuning

Domain D study track: **AI tuning** via [marimo](https://github.com/marimo-team/marimo)
notebooks — evaluation harnesses (D1), fine-tuning (D2: SFT/PEFT/LoRA/QLoRA), and
alignment (D3: DPO/RLHF).

Spine: `notes/progression.md`. Method and conventions: `AGENTS.md` (mirrors
[`learning-notebooks`](../learning-notebooks), the home of the cross-corpus
taxonomy index).

```bash
uv sync
uv run marimo edit --sandbox notebooks/eval/001_eval_harness.py
```

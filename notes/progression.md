# Domain D — AI Tuning: study progression

The build order is deliberate: **you can't tune what you can't measure.**

```
D1 Data & eval harness   →   D2 Fine-tuning   →   D3 Alignment
(metrics, eval suites,       (SFT → LoRA →        (reward models →
 regression gates,            QLoRA → quant-       DPO → RLHF/PPO)
 experiment logs)             aware → multi-GPU)
```

Statuses follow `../learning-notebooks/notes/taxonomy.md`:
`existing · needs notebook · needs architecture link · needs license verification ·
study-only · deferred`.

## D1 — Data & eval harness (do first)

| Topic | Packages | Status |
|---|---|---|
| Metrics & regression gates | scikit-learn [BSD] (metrics), stdlib `json` (JSONL logs) | existing — `notebooks/eval/001_eval_harness.py` |
| Dataset curation | datasets [Apache-2.0], evaluate [Apache-2.0] | needs notebook |
| Eval suites | lm-eval-harness [MIT] | needs notebook · needs architecture link |
| Queryable run history | stdlib `sqlite3` [PSF] (upgrade path from JSONL) | needs notebook |

The JSONL experiment-log discipline comes from `learning-ai`'s Appendix C
(`../learning-ai/notes/lesson_plan.md`); `sqlite3` is the additive upgrade.

## D2 — Fine-tuning (SFT / PEFT / LoRA / QLoRA)

| Topic | Packages | Architecture study | Status |
|---|---|---|---|
| Trainer + distributed setup | transformers [Apache-2.0], accelerate [Apache-2.0] | accelerate ✦ (transformers: missing) | needs notebook |
| PEFT/LoRA/QLoRA | peft [Apache-2.0], bitsandbytes [MIT] | (peft: missing) | needs notebook · needs architecture link |
| Declarative pipelines | axolotl [Apache-2.0], optimum [Apache-2.0] | axolotl ✦, optimum ✦ | needs notebook |

`✦` = a deep study already exists in the work-notes architecture corpus
(verified: `architecture/{axolotl,accelerate,optimum}`). `peft`, `trl`, and
`transformers` have **no** architecture study yet — promote-from-source is not
available for those; mark them `needs architecture link`.

## D3 — Alignment & preference tuning

| Topic | Packages | Status |
|---|---|---|
| Reward modeling → DPO → RLHF/PPO | trl [Apache-2.0], peft [Apache-2.0] | needs notebook · needs architecture link |

## Ground rules (from AGENTS.md)

- **Execution modes**: D notebooks use tiny proxy models or stubbed logits
  in-sandbox; real multi-GPU runs happen outside `uv --sandbox`.
- **CI-safety**: D2/D3 are heavy — never in the CI smoke-run list. D1
  metric-level notebooks are light and CI-safe.
- **Licenses**: permissive code deps only; weights/data licensing applies too
  (prefer Qwen/OLMo-style Apache-2.0 weights, CC0/CC-BY data).
- Wrap any model load in `@mo.persistent_cache`; gate long runs behind
  `mo.ui.run_button()` + `mo.stop()`.

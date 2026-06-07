# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
#     "scikit-learn",
# ]
# ///

"""evals — D1 harness: metrics, regression gates, and experiment logs."""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", app_title="evals: D1 harness")

with app.setup:
    import datetime as dt
    import json
    from pathlib import Path

    import marimo as mo
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # evals: D1 — you can't tune what you can't measure

    The first Domain D notebook: an evaluation harness in miniature. A stub
    "model" (stand-in for real logits) is scored against a tiny gold set with
    scikit-learn metrics, a **regression gate** decides pass/fail, and runs can
    be appended to a JSONL **experiment log**. Swap the stub for a real model
    later — the harness shape stays the same.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source reading

    - Upstream: <https://github.com/scikit-learn/scikit-learn> (metrics) and
      <https://github.com/EleutherAI/lm-evaluation-harness> (the real thing)
    - Local clone (sibling of this repo): `../scikit-learn`
    - Architecture corpus: the `axolotl`, `accelerate`, and `optimum` studies
      map the D2 systems this harness will eventually gate.
    """)
    return


@app.function
def stub_sentiment_model(text: str) -> str:
    """Pretend model: a keyword sentiment classifier standing in for real logits.

    Deliberately imperfect — a useful eval set needs failures to measure.
    """
    positives = ("love", "great", "excellent", "happy", "wonderful")
    return "pos" if any(word in text.lower() for word in positives) else "neg"


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The eval set and the stub model
    """)
    return


@app.cell
def _():
    eval_set = [
        ("I love this library", "pos"),
        ("What a wonderful API", "pos"),
        ("Excellent documentation", "pos"),
        ("I am happy with the results", "pos"),
        ("This makes me great at my job", "pos"),
        ("Truly great ergonomics", "pos"),
        ("This is terrible", "neg"),
        ("I hate flaky tests", "neg"),
        ("The worst install experience", "neg"),
        ("Confusing and slow", "neg"),
        ("Not great, honestly", "neg"),
        ("I expected more", "neg"),
    ]
    golds = [label for _, label in eval_set]
    preds = [stub_sentiment_model(text) for text, _ in eval_set]
    return eval_set, golds, preds


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Metrics
    """)
    return


@app.cell
def _(golds, preds):
    accuracy = float(accuracy_score(golds, preds))
    macro_f1 = float(f1_score(golds, preds, average="macro"))
    mo.hstack(
        [
            mo.stat(value=f"{accuracy:.2%}", label="accuracy", bordered=True),
            mo.stat(value=f"{macro_f1:.3f}", label="macro F1", bordered=True),
            mo.stat(value=len(golds), label="examples", bordered=True),
        ],
        gap=1,
    )
    return accuracy, macro_f1


@app.cell
def _(eval_set, golds, preds):
    _cm = confusion_matrix(golds, preds, labels=["pos", "neg"])
    mo.vstack(
        [
            mo.ui.table(
                [
                    {"gold \\ pred": "pos", "pos": int(_cm[0][0]), "neg": int(_cm[0][1])},
                    {"gold \\ pred": "neg", "pos": int(_cm[1][0]), "neg": int(_cm[1][1])},
                ],
                label="confusion matrix",
            ),
            mo.accordion(
                {
                    "Misclassified examples": mo.ui.table(
                        [
                            {"text": text, "gold": gold, "pred": pred}
                            for (text, gold), pred in zip(eval_set, preds, strict=True)
                            if gold != pred
                        ],
                    ),
                }
            ),
        ],
        gap=1,
    )
    return


@app.function
def gate_passes(accuracy: float, macro_f1: float) -> bool:
    """Regression gate: should this eval run block a model promotion?

    TODO(you): this is *the* D1 policy decision — which metrics gate, at what
    thresholds, and hard-fail vs warn. Accuracy is forgiving on balanced sets;
    macro F1 punishes one-class collapse; per-class recall catches silent
    regressions on the minority class. Encode your policy here (~5-10 lines).
    """
    return accuracy >= 0.80 and macro_f1 >= 0.75


@app.cell
def test_regression_gate(golds, preds):
    # Runs under pytest AND in every headless smoke-run — the notebook self-tests.
    assert gate_passes(
        float(accuracy_score(golds, preds)),
        float(f1_score(golds, preds, average="macro")),
    ), "stub model regressed below the gate thresholds"
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The regression gate, explored
    """)
    return


@app.cell
def _():
    min_accuracy = mo.ui.slider(0.5, 1.0, step=0.05, value=0.8, label="explore: min accuracy")
    min_accuracy
    return (min_accuracy,)


@app.cell
def _(accuracy, min_accuracy):
    _verdict = accuracy >= min_accuracy.value
    mo.callout(
        mo.md(
            f"At a `{min_accuracy.value:.2f}` accuracy floor this run would "
            f"**{'pass' if _verdict else 'fail'}** (the committed gate in "
            f"`gate_passes` stays fixed — sliders are for exploration)."
        ),
        kind="success" if _verdict else "danger",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Experiment log
    """)
    return


@app.cell
def _():
    log_button = mo.ui.run_button(label="Append this run to the experiment log")
    log_button
    return (log_button,)


@app.cell
def _(accuracy, log_button, macro_f1):
    mo.stop(not log_button.value, mo.md("👆 *Click to append a JSONL record of this run.*"))
    _log_dir = (mo.notebook_dir() or Path.cwd()) / "__marimo__"
    _log_dir.mkdir(exist_ok=True)
    _log_path = _log_dir / "experiments.jsonl"
    _record = {
        "ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "gate": gate_passes(accuracy, macro_f1),
    }
    with _log_path.open("a", encoding="utf-8") as _f:
        _f.write(json.dumps(_record) + "\n")
    mo.md(
        f"Appended `{json.dumps(_record)}` to `{_log_path.name}` (gitignored). "
        "stdlib `sqlite3` is the upgrade path once runs need querying."
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Where this goes next

    - **D1**: dataset curation (`datasets`, `evaluate`), then `lm-eval-harness`
    - **D2**: fine-tune a tiny proxy model and point *this* gate at it
      (`peft`, `accelerate`, `axolotl` — see `notes/progression.md`)
    - **D3**: alignment (`trl`) — gated by the same harness

    Index: `../learning-notebooks/notes/taxonomy.md` · Spine: `notes/progression.md`
    """)
    return


if __name__ == "__main__":
    app.run()

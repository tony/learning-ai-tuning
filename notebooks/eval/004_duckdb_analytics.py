# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "duckdb",
#     "marimo",
# ]
# ///

"""duckdb — the analytics lens: schema inference over any shape, windows, ablation pivots."""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", app_title="run store: duckdb analytics")


with app.setup:
    import json
    import tempfile
    from pathlib import Path

    import duckdb
    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # The analytics lens: DuckDB over the same run records

    SQLite (002/003) owns the store: point lookups, single-row writes,
    triggers, FTS. The *other* half of experiment tracking is analytical —
    *mean accuracy per learning rate*, *rolling trends*, *rank within a
    sweep* — scans over many runs, few columns. That's columnar territory:
    DuckDB **reads the JSONL archive directly**, infers a schema across
    heterogeneous shapes (missing keys become NULLs), and runs vectorized
    aggregations. A lens, not a second source of truth.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source reading

    - Upstream: <https://github.com/duckdb/duckdb>
    - Local clone (relative): `../../c++/duckdb` — start at the vectorized
      execution engine (DataChunks of ~2048 rows flowing between operators)
    - Architecture corpus: the `duckdb` study's vectorized-data-model notes
      (DataChunk/Vector contracts, validity masks, nested types) and the
      `clickhouse` MergeTree notes (zone maps: min/max per block — why scans
      skip data without per-row indexes)
    - Design rationale: `notes/storage-design.md`
    """)
    return


@app.function
def make_analytics_runs(n: int = 200) -> list[str]:
    """Deterministic nested run records for ablation analytics."""
    schedules = ["cosine", "linear", "constant"]
    runs: list[str] = []
    for i in range(n):
        record = {
            "ts": f"2026-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}T{(8 + i % 12):02d}:00:00",
            "gate": (i % 11) != 0,
            "config": {
                "lr": 10 ** -(2 + i % 3),
                "schedule": schedules[i % 3],
                **({"warmup": (i % 4) * 100} if i % 2 else {}),  # key present half the time
            },
            "metrics": {
                "accuracy": round(0.70 + (i % 23) / 100 + (0.03 if i % 3 == 0 else 0.0), 4),
                "loss": round(1.2 - (i % 23) / 50, 4),
            },
        }
        runs.append(json.dumps(record))
    return runs


@app.cell
def _():
    # DuckDB reads files; stage the archive as a real JSONL file.
    jsonl_path = Path(tempfile.mkstemp(suffix=".jsonl")[1])
    jsonl_path.write_text("\n".join(make_analytics_runs()) + "\n", encoding="utf-8")
    con = duckdb.connect()
    return con, jsonl_path


@app.cell
def _(con, jsonl_path):
    schema = con.sql(f"DESCRIBE SELECT * FROM read_json_auto('{jsonl_path}')")
    mo.vstack(
        [
            mo.md(
                "**Schema inference across shapes** — `config` arrives as a"
                " `STRUCT`; the sometimes-missing `warmup` key is simply a"
                " nullable field. No migrations, no declarations:"
            ),
            mo.ui.table(
                [dict(zip(("column", "type"), row[:2], strict=True)) for row in schema.fetchall()]
            ),
        ],
        gap=0.5,
    )
    return


@app.cell
def _(con, jsonl_path):
    ablation = con.sql(
        f"""
        SELECT config.schedule                       AS schedule,
               config.lr                             AS lr,
               count(*)                              AS runs,
               round(avg(metrics.accuracy), 4)       AS mean_acc,
               round(max(metrics.accuracy), 4)       AS best_acc
        FROM read_json_auto('{jsonl_path}')
        WHERE gate
        GROUP BY ALL
        ORDER BY mean_acc DESC
        """
    )
    mo.vstack(
        [
            mo.md("**Ablation table** — one vectorized scan answers the whole grid:"),
            mo.ui.table(
                [dict(zip(ablation.columns, row, strict=True)) for row in ablation.fetchall()]
            ),
        ],
        gap=0.5,
    )
    return


@app.cell
def _(con, jsonl_path):
    _trend = con.sql(
        f"""
        SELECT ts,
               metrics.accuracy AS accuracy,
               round(avg(metrics.accuracy) OVER (
                   ORDER BY ts ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
               ), 4) AS rolling_10,
               row_number() OVER (
                   PARTITION BY config.schedule ORDER BY metrics.accuracy DESC
               ) AS rank_in_schedule
        FROM read_json_auto('{jsonl_path}')
        WHERE gate
        ORDER BY ts
        LIMIT 12
        """
    )
    mo.vstack(
        [
            mo.md(
                "**Window functions** — a rolling 10-run accuracy trend and each"
                " run's rank inside its schedule sweep, in one pass:"
            ),
            mo.ui.table([dict(zip(_trend.columns, row, strict=True)) for row in _trend.fetchall()]),
        ],
        gap=0.5,
    )
    return


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "Row store vs column store — when each wins": mo.md(
                """
    - **SQLite (row)**: fetch *one run* and all its fields → one b-tree
      descent. Writes, triggers, FTS, constraints. The operational store.
    - **DuckDB (column)**: touch *one field of every run* → read just that
      column's blocks, vectorized 2048 rows at a time, skipping blocks via
      min/max **zone maps** instead of per-row index pointers.
    - The same JSONL archive feeds both — which is the whole design.
    """
            ),
            "Attaching the sqlite store directly (off-CI)": mo.md(
                """
    DuckDB can query 002's database in place — no export step:

    ```sql
    ATTACH 'runs.db' (TYPE sqlite);
    ```

    It loads the `sqlite` extension on first use (a network download, so
    this notebook keeps it out of the headless CI run). A `fts` extension
    exists too, if you want bm25 inside DuckDB.
    """
            ),
            "TODO(you): best-so-far curve": mo.md(
                """
    Write the window query for a *running maximum* accuracy per schedule
    (`max(...) OVER (PARTITION BY ... ORDER BY ts)`), the classic
    "best-so-far" tuning curve. Which schedule reaches 0.90 first?
    """
            ),
        }
    )
    return


@app.cell
def test_analytics_lens(con, jsonl_path):
    # Schema inference unified the shapes: warmup exists as a nullable field.
    _cols = {
        row[0]
        for row in con.sql(
            f"DESCRIBE SELECT config.* FROM read_json_auto('{jsonl_path}')"
        ).fetchall()
    }
    assert "warmup" in _cols and "lr" in _cols
    # The ablation grid covers all 9 (schedule, lr) cells.
    _cells = con.sql(
        f"""
        SELECT count(*) FROM (
            SELECT DISTINCT config.schedule, config.lr FROM read_json_auto('{jsonl_path}')
        )
        """
    ).fetchone()[0]
    assert _cells == 9, _cells
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Where this goes next

    - `005_inverted_index_scratch.py` — how text search works under FTS5:
      postings and BM25 built by hand
    - `006_tantivy_engine.py` — the production-engine end of that spectrum
    - Design rationale: `notes/storage-design.md`
    """)
    return


if __name__ == "__main__":
    app.run()

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
# ]
# ///

"""sqlite — the run store: hybrid schema, generated columns, instant lookups for any shape."""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", app_title="run store: sqlite hybrid schema")


with app.setup:
    import hashlib
    import json
    import sqlite3

    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # The run store: JSONL → SQLite, instant lookups no matter the shape

    Tuning runs produce records whose **shape varies by experiment** — configs
    and metric sets differ run to run. This notebook builds the canonical
    store from `notes/storage-design.md`: a few **hot columns**, the whole
    record as a **JSON payload**, and **generated columns** that turn
    schema-on-read into something *indexable*. The payoff is measured with
    `EXPLAIN QUERY PLAN`: the same query flips from `SCAN` to `SEARCH`.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source reading

    - Upstream: <https://github.com/sqlite/sqlite> (mirror)
    - Local clone (relative): `../../c/sqlite` — `src/json.c` (JSON1 +
      JSONB), `src/where.c` (the query planner choosing your indexes)
    - Architecture corpus: the `sqlite` study's `sql-functions/json.md`
      (JSONB is header+payload, roughly 3x faster than re-parsing text).
    - Design rationale: `notes/storage-design.md`.
    """)
    return


@app.function
def make_runs(n: int = 60) -> list[str]:
    """Generate n heterogeneous run records as JSON strings (three shapes).

    Shapes mirror real tuning logs: a flat early record, a nested
    config/metrics record (keys vary), and a failed run carrying error text.
    Deterministic on purpose — the test cell asserts against it.
    """
    runs: list[str] = []
    for i in range(n):
        ts = f"2026-06-{(i % 28) + 1:02d}T{(8 + i % 12):02d}:{i % 60:02d}:00"
        if i % 7 == 3:  # a failed run: no metrics, but searchable error text
            record = {
                "ts": ts,
                "gate": False,
                "config": {"lr": 10 ** -(2 + i % 3), "batch_size": 2 ** (3 + i % 3)},
                "error": "CUDA out of memory at step 412" if i % 2 else "NaN loss diverged",
            }
        elif i % 2 == 0:  # flat shape (like 001's record)
            record = {
                "ts": ts,
                "accuracy": round(0.70 + (i % 25) / 100, 4),
                "macro_f1": round(0.65 + (i % 30) / 100, 4),
                "gate": True,
            }
        else:  # nested shape: config + metrics, keys vary
            record = {
                "ts": ts,
                "gate": (i % 5) != 0,
                "config": {"lr": 10 ** -(2 + i % 3), "warmup": (i % 4) * 100},
                "metrics": {"accuracy": round(0.72 + (i % 22) / 100, 4)},
                "notes": f"sweep {i}: cosine schedule, seed {i * 13 % 97}",
            }
        runs.append(json.dumps(record))
    return runs


@app.cell(hide_code=True)
def _():
    mo.mermaid(
        """
    erDiagram
        RUNS {
            INTEGER run_id PK
            TEXT ts "hot column"
            INTEGER gate "hot column"
            TEXT payload "the whole record, any shape"
            TEXT fingerprint UK "sha256(payload) - idempotent ingest"
            REAL accuracy "GENERATED from payload"
            REAL lr "GENERATED from payload"
        }
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The naive baseline
    """)
    return


@app.cell
def _():
    # Naive store: same data, no generated columns, no indexes — the baseline.
    conn_naive = sqlite3.connect(":memory:")
    conn_naive.execute("CREATE TABLE runs (payload TEXT NOT NULL)")
    conn_naive.executemany("INSERT INTO runs (payload) VALUES (?)", [(r,) for r in make_runs()])
    return (conn_naive,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The hybrid schema
    """)
    return


@app.cell
def _():
    # Hybrid store. coalesce() across json paths is the shape-normalizer:
    # flat records keep accuracy at $.accuracy, nested ones at $.metrics.accuracy.
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE runs (
            run_id      INTEGER PRIMARY KEY,
            ts          TEXT NOT NULL,
            gate        INTEGER,
            payload     TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            accuracy REAL GENERATED ALWAYS AS (
                coalesce(
                    json_extract(payload, '$.metrics.accuracy'),
                    json_extract(payload, '$.accuracy')
                )
            ) VIRTUAL,
            lr REAL GENERATED ALWAYS AS (json_extract(payload, '$.config.lr')) VIRTUAL
        );
        CREATE INDEX idx_runs_ts ON runs (ts);
        CREATE INDEX idx_runs_accuracy ON runs (accuracy);
        CREATE INDEX idx_runs_failures ON runs (ts) WHERE gate = 0;
        """
    )
    conn.executemany(
        """
        INSERT OR IGNORE INTO runs (ts, gate, payload, fingerprint)
        VALUES (json_extract(?1, '$.ts'), json_extract(?1, '$.gate'), ?1, ?2)
        """,
        [(r, hashlib.sha256(r.encode()).hexdigest()) for r in make_runs()],
    )
    n_runs = conn.execute("SELECT count(*) FROM runs").fetchone()[0]
    return conn, n_runs


@app.cell
def _(conn, n_runs):
    _n_indexed = conn.execute("SELECT count(*) FROM runs WHERE accuracy IS NOT NULL").fetchone()[0]
    mo.hstack(
        [
            mo.stat(value=n_runs, label="runs ingested", bordered=True),
            mo.stat(value=_n_indexed, label="with indexable accuracy", bordered=True),
            mo.stat(value="3", label="record shapes", caption="one schema", bordered=True),
        ],
        gap=1,
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## The payoff: `SCAN` → `SEARCH`

    Same question — *runs with accuracy above a threshold* — against both
    stores. The naive store re-parses JSON for every row; the hybrid store
    walks `idx_runs_accuracy`.
    """)
    return


@app.cell
def _(conn, conn_naive):
    def _plan(c: sqlite3.Connection, sql: str) -> str:
        return "\n".join(row[3] for row in c.execute("EXPLAIN QUERY PLAN " + sql))

    _naive_sql = (
        "SELECT payload FROM runs"
        " WHERE coalesce(json_extract(payload, '$.metrics.accuracy'),"
        " json_extract(payload, '$.accuracy')) > 0.85"
    )
    _hybrid_sql = "SELECT payload FROM runs WHERE accuracy > 0.85"
    mo.hstack(
        [
            mo.vstack(
                [
                    mo.md("**naive** (JSON re-parsed per row)"),
                    mo.plain_text(_plan(conn_naive, _naive_sql)),
                ]
            ),
            mo.vstack(
                [
                    mo.md("**hybrid** (generated column + index)"),
                    mo.plain_text(_plan(conn, _hybrid_sql)),
                ]
            ),
        ],
        gap=2,
        widths="equal",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Query gallery
    """)
    return


@app.cell
def _():
    min_accuracy = mo.ui.slider(0.70, 0.95, step=0.01, value=0.85, label="min accuracy")
    min_accuracy
    return (min_accuracy,)


@app.cell
def _(conn, min_accuracy):
    _rows = conn.execute(
        """
        SELECT run_id, ts, round(accuracy, 3) AS accuracy, lr
        FROM runs WHERE accuracy >= ? ORDER BY accuracy DESC LIMIT 10
        """,
        (min_accuracy.value,),
    ).fetchall()
    mo.vstack(
        [
            mo.md(f"**Top runs at accuracy ≥ {min_accuracy.value:.2f}** (indexed `SEARCH`):"),
            mo.ui.table(
                [dict(zip(("run_id", "ts", "accuracy", "lr"), row, strict=True)) for row in _rows]
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Failure triage
    """)
    return


@app.cell
def _(conn):
    _failures = conn.execute(
        """
        SELECT run_id, ts, json_extract(payload, '$.error') AS error
        FROM runs WHERE gate = 0 AND json_extract(payload, '$.error') IS NOT NULL
        ORDER BY ts DESC LIMIT 8
        """
    ).fetchall()
    mo.vstack(
        [
            mo.md(
                "**Failure triage** — served by the *partial* index"
                " (`WHERE gate = 0`), which only stores the rows you grieve over:"
            ),
            mo.ui.table(
                [dict(zip(("run_id", "ts", "error"), row, strict=True)) for row in _failures]
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "TODO(you): promote one more hot field": mo.md(
                """
    Pick a field you'd actually filter on (e.g. `$.config.warmup` or
    `$.config.batch_size`) and promote it:

    ```sql
    ALTER TABLE runs ADD COLUMN warmup INTEGER
        GENERATED ALWAYS AS (json_extract(payload, '$.config.warmup')) VIRTUAL;
    ```

    Then index it, and prove the promotion with `EXPLAIN QUERY PLAN` —
    no migration of existing rows required (VIRTUAL columns are computed
    on read).
    """
            ),
            "Why a UNIQUE fingerprint?": mo.md(
                """
    `INSERT OR IGNORE` + `sha256(payload)` makes ingest **idempotent**:
    re-running the loader (a reactive re-run, a retried job) cannot
    duplicate runs. The test cell below proves it.
    """
            ),
        }
    )
    return


@app.cell
def test_run_store(conn, n_runs):
    # Idempotent ingest: replaying the same records adds nothing.
    conn.executemany(
        """
        INSERT OR IGNORE INTO runs (ts, gate, payload, fingerprint)
        VALUES (json_extract(?1, '$.ts'), json_extract(?1, '$.gate'), ?1, ?2)
        """,
        [(r, hashlib.sha256(r.encode()).hexdigest()) for r in make_runs()],
    )
    assert conn.execute("SELECT count(*) FROM runs").fetchone()[0] == n_runs
    # The generated column sees BOTH shapes (flat and nested accuracy).
    _shapes = conn.execute(
        """
        SELECT count(DISTINCT json_extract(payload, '$.metrics.accuracy') IS NOT NULL)
        FROM runs WHERE accuracy IS NOT NULL
        """
    ).fetchone()[0]
    assert _shapes == 2, "expected accuracy extracted from two different record shapes"
    # The expression index actually serves the hot query.
    _plan = " ".join(
        row[3]
        for row in conn.execute("EXPLAIN QUERY PLAN SELECT run_id FROM runs WHERE accuracy > 0.9")
    )
    assert "idx_runs_accuracy" in _plan, _plan
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Where this goes next

    - `003_fts5_search.py` — full-text search over the run text you saw in
      failure triage (`bm25()`, `snippet()`, external-content tables)
    - `004_duckdb_analytics.py` — the columnar lens over the same records
    - Design rationale and the options that lost: `notes/storage-design.md`
    """)
    return


if __name__ == "__main__":
    app.run()

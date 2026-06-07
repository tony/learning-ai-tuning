# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
# ]
# ///

"""sqlite FTS5 — full-text search over run text: MATCH, bm25, snippets, shadow tables."""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", app_title="run store: FTS5 search")


with app.setup:
    import sqlite3

    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Full-text search over run text with FTS5

    The run store (002) gave instant *structured* lookups. This notebook adds
    the text half: an **external-content FTS5 table** over run notes and error
    messages — the text lives once in `runs`, the inverted index references it
    and stays in sync via three triggers. Queries get `MATCH` syntax, `bm25()`
    ranking, and `snippet()` highlighting.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source reading

    - Local clone (relative): `../../c/sqlite/ext/fts5/` — `fts5_index.c`
      (the inverted index: in-memory hash flushed to levelled, LSM-like
      immutable segments with incremental merges), `fts5_expr.c` (MATCH
      query parsing), `fts5_main.c` (the virtual-table glue)
    - Architecture corpus: the `sqlite` study's `fts5/inverted-index.md` —
      shadow tables `%_data` (segments), `%_idx` (per-segment b-tree),
      `%_docsize` (per-row token counts feeding bm25)
    - Design rationale: `notes/storage-design.md`
    """)
    return


@app.function
def make_text_runs() -> list[tuple[int, str, str, str]]:
    """Deterministic (run_id, ts, notes, error) rows with searchable text."""
    rows: list[tuple[int, str, str, str]] = []
    schedules = ["cosine schedule", "linear warmup", "constant lr", "one-cycle policy"]
    for i in range(40):
        ts = f"2026-06-{(i % 28) + 1:02d}T{(9 + i % 10):02d}:{i % 60:02d}:00"
        notes = f"sweep {i}: {schedules[i % 4]}, gradient clipping at {1 + i % 3}.0"
        if i % 9 == 4:
            error = "CUDA out of memory while allocating activation buffers at step 412"
        elif i % 9 == 7:
            error = "NaN loss diverged after warmup ended; lowered learning rate"
        else:
            error = ""
        rows.append((i + 1, ts, notes, error))
    return rows


@app.cell
def _():
    fts = sqlite3.connect(":memory:")
    fts.executescript(
        """
        CREATE TABLE runs (
            run_id INTEGER PRIMARY KEY,
            ts     TEXT NOT NULL,
            notes  TEXT NOT NULL,
            error  TEXT NOT NULL
        );

        -- External content: the index points back into runs instead of
        -- storing a second copy of the text. prefix='2 3' adds prefix
        -- indexes so type-ahead ('cos*') is index-served too.
        CREATE VIRTUAL TABLE runs_fts USING fts5(
            notes, error,
            content='runs', content_rowid='run_id',
            prefix='2 3'
        );

        -- The three sync triggers every external-content table needs.
        CREATE TRIGGER runs_ai AFTER INSERT ON runs BEGIN
            INSERT INTO runs_fts(rowid, notes, error)
            VALUES (new.run_id, new.notes, new.error);
        END;
        CREATE TRIGGER runs_ad AFTER DELETE ON runs BEGIN
            INSERT INTO runs_fts(runs_fts, rowid, notes, error)
            VALUES ('delete', old.run_id, old.notes, old.error);
        END;
        CREATE TRIGGER runs_au AFTER UPDATE ON runs BEGIN
            INSERT INTO runs_fts(runs_fts, rowid, notes, error)
            VALUES ('delete', old.run_id, old.notes, old.error);
            INSERT INTO runs_fts(rowid, notes, error)
            VALUES (new.run_id, new.notes, new.error);
        END;
        """
    )
    fts.executemany("INSERT INTO runs VALUES (?, ?, ?, ?)", make_text_runs())
    return (fts,)


@app.cell
def _(fts):
    _n = fts.execute("SELECT count(*) FROM runs").fetchone()[0]
    _errs = fts.execute("SELECT count(*) FROM runs WHERE error != ''").fetchone()[0]
    mo.hstack(
        [
            mo.stat(value=_n, label="runs indexed", bordered=True),
            mo.stat(value=_errs, label="with error text", bordered=True),
            mo.stat(value="notes, error", label="FTS5 columns", bordered=True),
        ],
        gap=1,
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Search it

    `MATCH` syntax: terms imply AND (`cuda memory`), `OR`, `NOT`,
    `NEAR(a b, 5)`, column filters (`error: nan`), and `prefix*`. Results
    rank by `bm25()` (lower = better — it returns the negated score), and
    `snippet()` shows *why* a row matched.
    """)
    return


@app.cell
def _():
    query = mo.ui.text(value="cuda memory", label="MATCH query", full_width=True)
    query
    return (query,)


@app.cell
def _(fts, query):
    _sql = """
        SELECT r.run_id, r.ts,
               round(bm25(runs_fts, 1.0, 2.0), 3) AS score,
               snippet(runs_fts, 0, '[', ']', '…', 8)  AS notes_hit,
               snippet(runs_fts, 1, '[', ']', '…', 8)  AS error_hit
        FROM runs_fts JOIN runs r ON r.run_id = runs_fts.rowid
        WHERE runs_fts MATCH ?
        ORDER BY bm25(runs_fts, 1.0, 2.0)
        LIMIT 10
    """
    try:
        _rows = fts.execute(_sql, (query.value,)).fetchall() if query.value.strip() else []
        _out = (
            mo.ui.table(
                [
                    dict(zip(("run_id", "ts", "bm25", "notes", "error"), row, strict=True))
                    for row in _rows
                ]
            )
            if _rows
            else mo.callout(
                "No matches — try `nan OR diverged`, `cos*`, `error: memory`.", kind="info"
            )
        )
    except sqlite3.OperationalError as _exc:
        _out = mo.callout(f"FTS5 couldn't parse that query: `{_exc}`", kind="warn")
    _out
    return


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "Why the 2.0 weight on the error column?": mo.md(
                """
    `bm25(runs_fts, 1.0, 2.0)` weights matches in `error` twice as heavily
    as matches in `notes` — failure text is what we triage. Per-column
    weighting is free at query time; no reindex.
    """
            ),
            "TODO(you): tune the ranking": mo.md(
                """
    Flip the weights to `(2.0, 1.0)` and find a query whose top result
    changes. Then try `NEAR(memory step, 3)` vs plain `memory step` —
    what does proximity buy here?
    """
            ),
        }
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Under the floorboards: shadow tables

    FTS5 stores the inverted index in ordinary SQLite tables. `%_data` holds
    the levelled segments (an LSM in miniature: writes buffer in memory,
    flush as immutable segments, merge incrementally); `%_idx` is the
    per-segment b-tree; `%_docsize` keeps the token counts `bm25()` needs.
    """)
    return


@app.cell
def _(fts):
    _shadows = fts.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'runs_fts_%' ORDER BY name"
    ).fetchall()
    _segments = fts.execute("SELECT count(*) FROM runs_fts_data").fetchone()[0]
    mo.vstack(
        [
            mo.ui.table([{"shadow table": name} for (name,) in _shadows]),
            mo.md(
                f"`runs_fts_data` currently holds **{_segments}** rows of segment"
                " data. `INSERT INTO runs_fts(runs_fts) VALUES ('optimize')`"
                " merges all segments into one — the same compaction story as"
                " LSM stores, in miniature."
            ),
        ],
        gap=0.5,
    )
    return


@app.cell
def test_fts_ranking(fts):
    # The distinctive failure text must be findable and ranked first.
    _top = fts.execute(
        """
        SELECT r.error FROM runs_fts JOIN runs r ON r.run_id = runs_fts.rowid
        WHERE runs_fts MATCH 'cuda memory' ORDER BY bm25(runs_fts) LIMIT 1
        """
    ).fetchone()
    assert _top is not None and "CUDA out of memory" in _top[0]
    # Prefix index serves type-ahead.
    _n_prefix = fts.execute("SELECT count(*) FROM runs_fts WHERE runs_fts MATCH 'cos*'").fetchone()[
        0
    ]
    assert _n_prefix == 10, _n_prefix  # every 4th run uses the cosine schedule
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Where this goes next

    - `004_duckdb_analytics.py` — the columnar lens over the same records
    - `005_inverted_index_scratch.py` — build the postings + bm25 machinery
      yourself, then race it against this very table
    - Design rationale: `notes/storage-design.md`
    """)
    return


if __name__ == "__main__":
    app.run()

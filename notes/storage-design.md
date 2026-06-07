# Experiment-Store Design — FTS + instant lookups, no matter the shape

The D1 harness needs experiment tracking: every tuning run yields a record
whose **shape varies by experiment** — different hyperparameter configs,
different metric sets — plus free text worth searching (run notes, error
messages, prompt snippets). This doc brainstorms the storage options against
the project's actual access patterns and picks a structure. The notebook
series `notebooks/eval/002–006` implements it.

## The queries we actually run

| Class | Example |
|---|---|
| Point lookup | "show run `2026-06-07T14:31:02`" / "run #1432" |
| Filter | "all runs where `gate = false`" · "accuracy ≥ 0.85" |
| Top-k | "best 5 runs by macro-F1" · "most relevant runs for *oom batch*" |
| Time-series | "accuracy over the last 200 runs" |
| Full-text | "runs whose error mentions *CUDA out of memory*" |
| Ablation group-by | "mean accuracy per `config.lr` bucket" |

## Options matrix

| Option | Normalization | Query fit | Indexes | Access | License | Verdict |
|---|---|---|---|---|---|---|
| **JSONL flat file** (status quo) | none — schema-on-read | append O(1); every query O(N) scan; no FTS | none | stdlib `json` | n/a | keep as the *wire/archive* format, not the query store |
| **Hybrid SQLite: hot columns + JSON payload** | partial — promote hot fields via **generated columns**, keep the rest as JSON | all six classes; point/filter/top-k via B-tree, text via FTS5 | B-tree, **expression**, **partial** (`WHERE gate=0`), covering; FTS5 | stdlib `sqlite3` | public domain | **canonical store** |
| **Fully-normalized EAV** (runs/params/metrics tables) | maximal | flexible but every question becomes self-joins; types collapse to TEXT | per-table B-trees | stdlib `sqlite3` | public domain | rejected — flexibility without queryability |
| **DuckDB columnar** | schema inferred per batch (`read_json_auto`) | aggregations/windows/pivots over many runs; weaker single-row writes | zone maps (min/max per row group) | duckdb | MIT | **analytics lens** over the same data, not the store |
| **tantivy** (Lucene-class engine) | document model | best-in-class relevance: segments, skip lists, block-WAND top-k | inverted index + FST term dictionary | tantivy-py | MIT | the upgrade when BM25 quality/scale outgrows FTS5 |
| **pagefind-style static fragments** | pre-chunked fragments + packed word/filter indexes | client-side/WASM search of *published* results | packed inverted fragments | static files | MIT | mention-only: the "ship the index" angle for static reports |

## Decision

1. **Hybrid SQLite is the canonical store.** One `runs` table: a few hot
   columns (`run_id`, `ts`, `gate`) + a `payload` JSON column holding the
   whole heterogeneous record. "Instant lookups no matter the shape" comes
   from **generated columns** — `accuracy REAL GENERATED ALWAYS AS
   (json_extract(payload, '$.metrics.accuracy'))` — which are *indexable*:
   schema-on-read at write-time cost zero, schema-on-disk only for fields
   promoted to indexes. New shapes need no migration; new hot fields are one
   `ALTER TABLE … ADD COLUMN … GENERATED` away.
2. **FTS5 external-content table for text.** The run text (notes/error/prompt)
   lives once in `runs`; the FTS index references it (`content='runs'`) and is
   kept in sync by three triggers. `MATCH` + `bm25()` + `snippet()` cover the
   full-text class; prefix indexes cover type-ahead.
3. **DuckDB reads, never owns.** `read_json_auto` over the JSONL archive (or
   the sqlite file) gives columnar scans, window functions, and ablation
   pivots — the OLAP half of the workload — without a second source of truth.
4. **EAV rejected**: every filter becomes a self-join pile-up and all values
   degrade to TEXT; generated columns give the same flexibility with real
   types and real indexes.
5. **tantivy is the escape hatch**, not the default: segments + block-WAND
   + FST dictionaries buy ranking quality and scale FTS5 doesn't chase.

## Index taxonomy (what 002/003 demonstrate)

- **B-tree** on hot columns (`ts`) — point lookups, range scans
- **Expression/generated-column indexes** — `CREATE INDEX ON runs(accuracy)`
  where `accuracy` is generated from JSON → `EXPLAIN QUERY PLAN` flips
  `SCAN` → `SEARCH`
- **Partial** — `CREATE INDEX … WHERE gate = 0` (the failures you triage)
- **Covering** — index contains all selected columns; no table lookup
- **FTS5** — inverted index in LSM-like levelled segments (shadow tables
  `%_data`, `%_idx`, `%_docsize`), incremental merges, optional prefix indexes
- contrast: **zone maps** (duckdb/clickhouse) — min/max per block instead of
  per-row pointers; great for scans, useless for point lookups

## Grounding (architecture corpus + clones)

Corpus studies (work-notes, `architecture/<project>/…`): `sqlite` — FTS5
inverted index as levelled LSM segments with incremental merge; JSONB binary
format (~3× faster than re-parsing text). `tantivy` — BM25 (`k1=1.2, b=0.75`,
IDF `ln(1+(N-n+0.5)/(n+0.5))`), postings in 128-doc SIMD-bitpacked blocks,
skip lists carrying block-WAND maxima. `lucene` — tiered merge policy, FST
term dictionaries, impacts for top-k pruning. `clickhouse` — MergeTree parts
with min/max indexes.

Local clones for source-reading cells (siblings, relative): SQLite
`../../c/sqlite` (`ext/fts5/fts5_index.c`, `src/json.c`), DuckDB
`../../c++/duckdb`, tantivy `../../rust/tantivy` (`ARCHITECTURE.md`),
tantivy-py `../../rust-python/tantivy-py`, pagefind `../../rust/pagefind`
(`pagefind/src/index/mod.rs`).

## Notebook map

| Notebook | Teaches | Deps |
|---|---|---|
| `eval/002_jsonl_to_sqlite.py` | hybrid schema, generated columns, expression/partial indexes, EXPLAIN | marimo |
| `eval/003_fts5_search.py` | external-content FTS5, triggers, MATCH/bm25/snippet, shadow tables | marimo |
| `eval/004_duckdb_analytics.py` | columnar lens: inference over shapes, windows, ablation pivots | marimo, duckdb |
| `eval/005_inverted_index_scratch.py` | postings + BM25 by hand, raced against FTS5 | marimo |
| `eval/006_tantivy_engine.py` | a real engine: schema, segments, query types | marimo, tantivy |

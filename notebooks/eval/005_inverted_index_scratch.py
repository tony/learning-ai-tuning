# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
# ]
# ///

"""search internals — an inverted index + BM25 from scratch, raced against FTS5."""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", app_title="search internals: BM25 from scratch")


with app.setup:
    import math
    import re
    import sqlite3

    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # An inverted index + BM25, by hand

    Everything 003 did with `MATCH` reduces to two structures and one
    formula: a **postings map** (term → which docs, how often), per-doc
    lengths, and **BM25**. This notebook builds them in ~40 lines, races the
    result against FTS5's `bm25()` on the same documents, and then tours
    what real engines add on top.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source reading

    - Local clones (relative): `../../rust/tantivy` — `ARCHITECTURE.md`,
      then `src/postings/` (128-doc bitpacked blocks) and `src/query/`
      (Bm25Weight); `../../c/sqlite/ext/fts5/fts5_index.c` for the same
      ideas in C
    - Architecture corpus: the `tantivy` study's `bm25-scoring.md` (the
      exact formula below) and `postings-and-term-info.md`; the `lucene`
      study's `terms-and-postings.md` (FST term dictionaries, impacts)
    - Design rationale: `notes/storage-design.md`
    """)
    return


@app.function
def tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer — the same shape FTS5's unicode61 produces here."""
    return re.findall(r"[a-z0-9]+", text.lower())


@app.class_definition
class TinyIndex:
    """An inverted index with BM25 ranking in ~40 lines.

    postings: term -> {doc_id: term_frequency}; doc_len feeds the BM25
    length normalization. k1 saturates term frequency; b controls how much
    long documents are penalized (tantivy/Lucene defaults: 1.2 and 0.75).
    """

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.postings: dict[str, dict[int, int]] = {}
        self.doc_len: dict[int, int] = {}

    def add(self, doc_id: int, text: str) -> None:
        """Index one document (declare-and-mutate happens in one place)."""
        tokens = tokenize(text)
        self.doc_len[doc_id] = len(tokens)
        for tok in tokens:
            bucket = self.postings.setdefault(tok, {})
            bucket[doc_id] = bucket.get(doc_id, 0) + 1

    def idf(self, term: str) -> float:
        """ln(1 + (N - n + 0.5) / (n + 0.5)) — rare terms weigh more."""
        n_docs, n_term = len(self.doc_len), len(self.postings.get(term, {}))
        return math.log(1 + (n_docs - n_term + 0.5) / (n_term + 0.5))

    def score(self, term: str, doc_id: int) -> float:
        """One term's BM25 contribution to one document."""
        freq = self.postings.get(term, {}).get(doc_id, 0)
        if freq == 0:
            return 0.0
        avgdl = sum(self.doc_len.values()) / len(self.doc_len)
        norm = self.k1 * (1 - self.b + self.b * self.doc_len[doc_id] / avgdl)
        return self.idf(term) * freq / (freq + norm)

    def search(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        """Top-k docs for a bag-of-words query (sum of per-term scores)."""
        terms = tokenize(query)
        candidates = {d for t in terms for d in self.postings.get(t, {})}
        ranked = [(d, sum(self.score(t, d) for t in terms)) for d in candidates]
        return sorted(ranked, key=lambda pair: -pair[1])[:k]


@app.function
def make_docs() -> dict[int, str]:
    """The shared mini-corpus both engines index."""
    return {
        1: "CUDA out of memory while allocating activation buffers at step 412",
        2: "NaN loss diverged after warmup ended lowered the learning rate",
        3: "cosine schedule with gradient clipping converged smoothly",
        4: "checkpoint resumed memory usage stayed flat for the whole sweep",
        5: "linear warmup then constant learning rate baseline run",
        6: "out of disk space while writing checkpoint shards",
        7: "best run so far cosine schedule and small batch size",
        8: "memory fragmentation suspected after long sweep memory pressure grew",
    }


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Tune k1 and b live
    """)
    return


@app.cell
def _():
    k1 = mo.ui.slider(0.5, 2.0, step=0.1, value=1.2, label="k1 (tf saturation)")
    b = mo.ui.slider(0.0, 1.0, step=0.05, value=0.75, label="b (length penalty)")
    mo.hstack([k1, b], gap=2, justify="start")
    return b, k1


@app.cell
def _(b, k1):
    index = TinyIndex(k1=k1.value, b=b.value)
    for _doc_id, _text in make_docs().items():
        index.add(_doc_id, _text)
    return (index,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The postings map
    """)
    return


@app.cell
def _(index):
    mo.vstack(
        [
            mo.md(
                "**The postings map is the whole trick** — `memory` points"
                " straight at its documents (doc → term frequency); nothing"
                " is scanned:"
            ),
            mo.tree(
                {"memory": index.postings.get("memory", {}), "cuda": index.postings.get("cuda", {})}
            ),
            mo.md(
                f"And IDF prices rarity: `idf('cuda')` ="
                f" **{index.idf('cuda'):.3f}** vs `idf('memory')` ="
                f" **{index.idf('memory'):.3f}** — the rarer term is worth more."
            ),
        ],
        gap=0.5,
    )
    return


@app.cell
def _():
    scratch_query = mo.ui.text(value="memory sweep", label="query", full_width=True)
    scratch_query
    return (scratch_query,)


@app.cell
def _(index, scratch_query):
    _docs = make_docs()
    _rows = [
        {"doc": d, "bm25": round(s, 4), "text": _docs[d]}
        for d, s in index.search(scratch_query.value)
        if s > 0
    ]
    mo.ui.table(_rows) if _rows else mo.callout(
        "No hits — try `memory`, `cosine`, `checkpoint`.", kind="info"
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## The race: TinyIndex vs FTS5

    Same documents, same query, two engines. FTS5's `bm25()` returns the
    negated score (lower = better); ours returns it positive. The *order*
    is what matters.
    """)
    return


@app.cell
def _():
    fts_conn = sqlite3.connect(":memory:")
    fts_conn.execute("CREATE VIRTUAL TABLE docs USING fts5(body)")
    fts_conn.executemany("INSERT INTO docs(rowid, body) VALUES (?, ?)", list(make_docs().items()))
    return (fts_conn,)


@app.cell
def _(fts_conn, index, scratch_query):
    _docs = make_docs()
    _scratch = [
        {"rank": i + 1, "doc": d, "engine": "TinyIndex"}
        for i, (d, s) in enumerate(index.search(scratch_query.value, k=3))
        if s > 0
    ]
    try:
        _fts = [
            {"rank": i + 1, "doc": row[0], "engine": "FTS5"}
            for i, row in enumerate(
                fts_conn.execute(
                    "SELECT rowid FROM docs WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT 3",
                    (" OR ".join(tokenize(scratch_query.value)),),
                )
            )
        ]
    except sqlite3.OperationalError:
        _fts = []
    mo.hstack(
        [
            mo.vstack([mo.md("**TinyIndex top-3**"), mo.ui.table(_scratch)]),
            mo.vstack([mo.md("**FTS5 top-3**"), mo.ui.table(_fts)]),
        ],
        gap=2,
        widths="equal",
    )
    return


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "What real engines add on top": mo.md(
                """
    - **Compressed postings**: tantivy packs doc ids in 128-doc,
      delta-encoded, SIMD-bitpacked blocks — not a Python dict.
    - **Skip lists + block-WAND**: each block records its maximum possible
      BM25 contribution, so top-k queries *skip whole blocks* that cannot
      make the cut.
    - **FST term dictionaries** (Lucene): the sorted term list becomes a
      finite-state transducer — prefix-compressed, memory-mapped.
    - **Segments + merges**: writes land in immutable segments merged in
      the background (tiered policy in Lucene, levelled LSM in FTS5) —
      the same compaction story 003's shadow tables showed.
    """
            ),
            "TODO(you): make a rank flip, then explain it": mo.md(
                """
    Slide `b` to 0.0 (no length penalty) and watch the `memory sweep`
    ranking — doc 8 repeats `memory` but is long; doc 4 says it once and is
    short. Why does each setting prefer the doc it prefers? Then push `k1`
    down to 0.5 — what does saturating term frequency do to repeated terms?
    """
            ),
        }
    )
    return


@app.cell
def test_scratch_vs_fts5(fts_conn, index):
    # Both engines agree on the obvious winner for a two-term query.
    _scratch_top = index.search("cuda memory", k=1)[0][0]
    _fts_top = fts_conn.execute(
        "SELECT rowid FROM docs WHERE docs MATCH 'cuda OR memory' ORDER BY bm25(docs) LIMIT 1"
    ).fetchone()[0]
    assert _scratch_top == _fts_top == 1
    # Rarity pricing: 'cuda' (1 doc) must out-weigh 'memory' (3 docs).
    assert index.idf("cuda") > index.idf("memory") > 0
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Where this goes next

    - `006_tantivy_engine.py` — the production end of this spectrum:
      segments, typed schemas, block-WAND for real
    - Design rationale: `notes/storage-design.md`
    """)
    return


if __name__ == "__main__":
    app.run()

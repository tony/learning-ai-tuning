# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
#     "tantivy",
# ]
# ///

"""tantivy — a real search engine: typed schema, segments, BM25 with block-WAND."""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium", app_title="search internals: tantivy")


with app.setup:
    import marimo as mo
    import tantivy


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # The production end of the spectrum: tantivy

    005 built the textbook version; this is what a Lucene-class engine
    (in Rust, with Python bindings) does with the same job: a **typed
    schema**, writes batched into **immutable segments**, postings in
    128-doc bitpacked blocks with skip lists, and **block-WAND** pruning so
    top-k queries skip whole blocks that can't compete. Scores here are
    positive BM25 — same formula as 005, same defaults (k1=1.2, b=0.75).
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Source reading

    - Local clones (relative): `../../rust/tantivy` — read `ARCHITECTURE.md`
      first (the best single document on inverted-index engines), then
      `src/postings/` and `src/query/`; bindings at `../../rust-python/tantivy-py`
    - Architecture corpus: the `tantivy` study (`bm25-scoring.md`,
      `postings-and-term-info.md` — the block-WAND maxima live in the skip
      list) and the `lucene` study (`merging.md` — tiered merges; tantivy
      inherits the design)
    - Design rationale: `notes/storage-design.md` — tantivy is the escape
      hatch when relevance quality or scale outgrows FTS5
    """)
    return


@app.function
def make_docs() -> dict[int, str]:
    """The same mini-corpus 005 used — comparable rankings on purpose."""
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


@app.cell
def _():
    # Typed schema: fields declare up front how they're indexed and stored.
    _builder = tantivy.SchemaBuilder()
    _builder.add_integer_field("doc_id", stored=True, indexed=True)
    _builder.add_text_field("body", stored=True)
    schema = _builder.build()

    index = tantivy.Index(schema)  # RAM directory — no files
    _writer = index.writer()
    for _doc_id, _text in make_docs().items():
        _writer.add_document(tantivy.Document(doc_id=_doc_id, body=_text))
    _writer.commit()  # writes land as an immutable segment
    index.reload()
    searcher = index.searcher()
    return index, searcher


@app.cell
def _(searcher):
    mo.hstack(
        [
            mo.stat(value=searcher.num_docs, label="docs indexed", bordered=True),
            mo.stat(
                value=searcher.num_segments,
                label="segments",
                caption="immutable; merged in background",
                bordered=True,
            ),
            mo.stat(value="BM25", label="scoring", caption="k1=1.2, b=0.75", bordered=True),
        ],
        gap=1,
    )
    return


@app.cell
def _():
    engine_query = mo.ui.text(
        value="cuda memory", label='query (try: "out of memory" as a phrase)', full_width=True
    )
    engine_query
    return (engine_query,)


@app.cell
def _(engine_query, index, searcher):
    _docs = make_docs()
    try:
        _query = index.parse_query(engine_query.value, ["body"])
        _hits = searcher.search(_query, 5).hits
        _rows = [
            {
                "rank": i + 1,
                "score": round(score, 4),
                "doc": searcher.doc(addr)["doc_id"][0],
                "text": searcher.doc(addr)["body"][0],
            }
            for i, (score, addr) in enumerate(_hits)
        ]
        _out = mo.ui.table(_rows) if _rows else mo.callout("No hits.", kind="info")
    except ValueError as _exc:
        _out = mo.callout(f"Query didn't parse: `{_exc}`", kind="warn")
    _out
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Phrase vs bag-of-words

    The query parser understands structure FTS5 spells differently and 005
    couldn't do at all: `"out of memory"` (a *phrase* — positions must be
    adjacent) vs `out of memory` (any term anywhere).
    """)
    return


@app.cell
def _(index, searcher):
    def _top(query_text: str) -> list[dict[str, object]]:
        _q = index.parse_query(query_text, ["body"])
        return [
            {"score": round(s, 3), "doc": searcher.doc(a)["doc_id"][0]}
            for s, a in searcher.search(_q, 3).hits
        ]

    mo.hstack(
        [
            mo.vstack(
                [mo.md('**`"out of memory"`** (phrase)'), mo.ui.table(_top('"out of memory"'))]
            ),
            mo.vstack(
                [mo.md("**`out of memory`** (bag of words)"), mo.ui.table(_top("out of memory"))]
            ),
        ],
        gap=2,
        widths="equal",
    )
    return


@app.cell(hide_code=True)
def _():
    mo.accordion(
        {
            "When to graduate from FTS5 to tantivy": mo.md(
                """
    - **Relevance work**: typed fields, per-field boosts, phrase slop,
      fuzzy terms — a real query language and scoring you can shape.
    - **Scale**: block-WAND turns top-k over millions of docs from
      "score everything" into "skip most blocks" — the skip list stores
      each block's maximum possible contribution.
    - **Throughput**: segments are written lock-free and merged in the
      background (the Lucene tiered-merge design).
    - Until those bite, FTS5 inside the run store (003) is less moving
      parts — one file, no sidecar index to keep consistent.
    """
            ),
            "TODO(you): break the tie": mo.md(
                """
    Add a ninth document engineered so that `cuda memory` ranks it *above*
    doc 1 — without using the word `cuda`. (Hint: think about what document
    length does to BM25, and what repeating `memory` buys before k1
    saturation flattens it.) Verify with the search box.
    """
            ),
        }
    )
    return


@app.cell
def test_tantivy_agrees(index, searcher):
    # Same winner as 005's TinyIndex and 003's FTS5 for the canonical query.
    _q = index.parse_query("cuda memory", ["body"])
    _top_doc = searcher.doc(searcher.search(_q, 1).hits[0][1])["doc_id"][0]
    assert _top_doc == 1
    # Phrase semantics: "out of memory" matches doc 1 only (adjacent positions).
    _phrase = index.parse_query('"out of memory"', ["body"])
    _phrase_docs = {searcher.doc(a)["doc_id"][0] for _, a in searcher.search(_phrase, 10).hits}
    assert _phrase_docs == {1}, _phrase_docs
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Series complete

    The experiment-store design is now implemented end to end:

    - `002` — the canonical store (hybrid schema, generated columns, indexes)
    - `003` — text search inside it (FTS5, bm25, snippets)
    - `004` — the analytics lens (DuckDB over the same archive)
    - `005` — the theory (postings + BM25 by hand)
    - `006` — the production engine (this notebook)

    Rationale and the options that lost: `notes/storage-design.md`.
    """)
    return


if __name__ == "__main__":
    app.run()

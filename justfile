# learning-ai-tuning tasks — thin wrappers over uv/marimo. Every recipe body
# is a plain shell command you can run yourself (see AGENTS.md). Notebook
# arguments are real paths, so your shell tab-completes them by track:
#   just edit notebooks/eval/<TAB>

# Bare `just` lists everything below.
default:
    @just --list

# tree of notebooks by track
[group('notebooks')]
list:
    @fd -e py . notebooks/ | sort

# edit a notebook — prints the URL, does NOT open a browser
[group('notebooks')]
edit nb *args:
    uv run marimo edit --sandbox --headless {{ nb }} {{ args }}

# edit a notebook and open the browser
[group('notebooks')]
open nb *args:
    uv run marimo edit --sandbox {{ nb }} {{ args }}

# run a notebook headlessly as a script (its PEP 723 deps resolve in a sandbox)
[group('notebooks')]
run nb:
    uv run {{ nb }}

# serve a notebook as a read-only app — prints the URL, no browser
[group('notebooks')]
serve nb *args:
    uv run marimo run --sandbox --headless {{ nb }} {{ args }}

# fuzzy-pick a notebook with fzf, then edit it (no browser)
[group('notebooks')]
pick:
    @just edit "$(fd -e py . notebooks/ | fzf)"

# browse all notebooks in marimo's directory gallery (browse-only — sandboxed deps need `just edit`)
[group('notebooks')]
gallery:
    uv run marimo edit --headless notebooks/

# run a notebook's test_* cells (pytest imports the notebook, so pass its deps)
[group('notebooks')]
test nb deps='--with scikit-learn':
    uv run --with pytest {{ deps }} pytest {{ nb }}

# scaffold notebooks/<track>/001_<topic>.py from the sibling repo's template
[group('notebooks')]
new track topic:
    mkdir -p notebooks/{{ track }}
    cp ../learning-notebooks/notes/notebook_template.py notebooks/{{ track }}/001_{{ topic }}.py
    @echo "created notebooks/{{ track }}/001_{{ topic }}.py — now: just edit notebooks/{{ track }}/001_{{ topic }}.py"

# all quality gates (what CI runs)
[group('quality')]
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run ty check
    uv run marimo check --strict notebooks/
    uv run scripts/check_licenses.py

# format the repo
[group('quality')]
fmt:
    uv run ruff format .

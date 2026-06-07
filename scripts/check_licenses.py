#!/usr/bin/env python3
"""Deny-list guard for notebook PEP 723 dependencies.

Scans every marimo notebook's inline script metadata and fails when a
dependency's distribution is on the license deny list (GPL / AGPL / SSPL /
BUSL / RSAL families — see ``notes/taxonomy.md`` "License policy" and the
AGENTS.md quality gates). MPL-2.0 packages are flagged as warnings (they are
acceptable as dev/test dependencies only).

Stdlib-only on purpose: runs under ``uv run`` with zero added dependencies.
"""

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: PyPI distribution name -> (license family, suggested permissive substitute).
#: Encodes the deny list from notes/taxonomy.md; names are matched after
#: PEP 503 normalization, so extras and version specifiers never interfere.
DENY: dict[str, tuple[str, str]] = {
    "pymongo": ("SSPL (MongoDB)", "stdlib sqlite3 or postgres via psycopg [LGPL-free: pg8000]"),
    "mongoengine": ("SSPL (MongoDB)", "sqlalchemy [MIT] + sqlite/postgres"),
    "grafana-client": ("AGPL-3.0 (Grafana)", "opentelemetry-sdk [Apache-2.0]"),
    "minio": ("AGPL-3.0 (MinIO)", "pyarrow.fs or obstore [Apache-2.0]"),
    "elasticsearch": ("Elastic License / SSPL (>= 7.11)", "opensearch-py [Apache-2.0]"),
    "redis": ("RSALv2/SSPL (Redis >= 7.4)", "valkey [BSD]"),
}

#: Flag tier: weak copyleft, acceptable for dev/test use only — warn, don't fail.
FLAG: dict[str, str] = {
    "hypothesis": "MPL-2.0 — fine as a test/dev dependency, flagged per policy",
    "artillery": "MPL-2.0 — prefer locust/vegeta [MIT] for load testing",
}

_BLOCK_RE = re.compile(r"^# /// script\s*$(.*?)^# ///\s*$", re.MULTILINE | re.DOTALL)
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def normalize(name: str) -> str:
    """Normalize a distribution name per PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def dependency_name(requirement: str) -> str:
    """Extract the normalized distribution name from a PEP 508 requirement."""
    match = _NAME_RE.match(requirement.strip())
    return normalize(match.group(0)) if match else ""


def pep723_dependencies(notebook: Path) -> list[str]:
    """Return the ``dependencies`` list from a notebook's PEP 723 block."""
    match = _BLOCK_RE.search(notebook.read_text(encoding="utf-8"))
    if match is None:
        return []
    toml_text = "\n".join(
        line.removeprefix("# ").removeprefix("#") for line in match.group(1).splitlines()
    )
    dependencies = tomllib.loads(toml_text).get("dependencies", [])
    return [str(dep) for dep in dependencies]


def main() -> int:
    """Scan all notebooks; return 1 when any denied dependency is found."""
    notebooks = sorted(REPO_ROOT.glob("notebooks/**/*.py"))
    template = REPO_ROOT / "notes" / "notebook_template.py"
    if template.exists():
        notebooks.append(template)
    denied = 0
    for notebook in notebooks:
        rel = notebook.relative_to(REPO_ROOT)
        for requirement in pep723_dependencies(notebook):
            name = dependency_name(requirement)
            if name in DENY:
                family, substitute = DENY[name]
                print(f"DENY  {rel}: {requirement!r} is {family}; use {substitute}")
                denied += 1
            elif name in FLAG:
                print(f"FLAG  {rel}: {requirement!r} — {FLAG[name]}")
    if denied:
        print(f"License deny-list: {denied} denied dependency(ies) found.")
        return 1
    print(f"License deny-list: OK ({len(notebooks)} notebooks scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

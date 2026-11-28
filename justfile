@_:
  just --list

[group('qa')]
ci: lint typecheck test

[private]
ensure cmd:
  #!/usr/bin/env bash
  command -v {{cmd}} >/dev/null 2>&1 || { echo "{{cmd}} not on PATH. Run 'uv sync --group ci' to install it locally." >&2; exit 1; }

[group('qa')]
lint: (ensure "ruff")
  ruff check
  ruff format --check

[group('qa')]
typecheck: (ensure "basedpyright")
  basedpyright

[group('qa')]
test: (ensure "pytest")
  pytest

[group('qa')]
viz *args:
  uv run python -m tests.visual {{args}}

[group('lifecycle')]
release:
  bash scripts/release.sh

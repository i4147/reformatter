"""Command-line module entry point (``python -m result``)."""

from __future__ import annotations

from result.reformatter import main

if __name__ == "__main__":
    raise SystemExit(main())

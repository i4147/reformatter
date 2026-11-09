"""Public package interface for the Python indentation autofixer."""

from __future__ import annotations

from result.reformatter import (
    BatchStats,
    FileStats,
    ReformatterError,
    ReformatResult,
    StructuralCounts,
    format_stats_report,
    is_compilable_python,
    main,
    reformat_file,
    reformat_paths,
    reformat_source,
)

__all__ = [
    "BatchStats",
    "FileStats",
    "ReformatResult",
    "ReformatterError",
    "StructuralCounts",
    "format_stats_report",
    "is_compilable_python",
    "main",
    "reformat_file",
    "reformat_paths",
    "reformat_source",
]

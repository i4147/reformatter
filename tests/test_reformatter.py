"""Comprehensive pytest suite for the Python indentation autofixer."""

from __future__ import annotations

import ast
import json
import pathlib
import shutil
import subprocess
import textwrap
from typing import Any

import pytest

from result.reformatter import (
    BatchStats,
    ReformatterError,
    is_compilable_python,
    main,
    reformat_file,
    reformat_paths,
    reformat_source,
)

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
INITIAL_COMMIT: str = "4f2c811a2a03a701545cd1a6e6dda2dd1b2dbb0f"

EXPECTED_BROKEN_METRICS: dict[str, tuple[int, int]] = {
    "broken1.py": (39, 5),
    "broken2.py": (20, 5),
    "broken3.py": (29, 6),
    "broken4.py": (12, 2),
    "broken5.py": (12, 3),
    "broken6.py": (29, 4),
    "broken7.py": (17, 1),
    "broken8.py": (12, 0),
    "broken9.py": (16, 3),
    "broken10.py": (19, 6),
    "broken11.py": (23, 4),
    "broken12.py": (37, 4),
    "broken13.py": (36, 4),
}


def _load_original_broken_source(name: str) -> str:
    """Load the original single-line broken file from the initial Git commit."""
    proc = subprocess.run(
        ["git", "show", f"{INITIAL_COMMIT}:{name}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout:
        return proc.stdout
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _collapse_to_single_line(code: str) -> str:
    """Collapse formatted Python code onto a single space-separated line."""
    return " ".join(
        line.strip() for line in code.splitlines() if line.strip()
    ) + "\n"


def _strip_all_indents(code: str) -> str:
    """Strip leading whitespace from every line while keeping newlines."""
    return "\n".join(line.lstrip() for line in code.splitlines()) + "\n"


def _exec_namespace(code: str) -> dict[str, Any]:
    """Execute ``code`` in an isolated namespace and return its globals."""
    ns: dict[str, Any] = {"__name__": "__test__"}
    exec(compile(code, "<exec_test>", "exec"), ns)
    return ns


# ---------------------------------------------------------------------------
# 1. Original Repository broken1.py .. broken13.py Reconstruction Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", list(EXPECTED_BROKEN_METRICS.keys()))
def test_original_broken_files_reconstruct_and_compile(
    filename: str, tmp_path: pathlib.Path
) -> None:
    """Every original broken*.py file reconstructs in-place to valid, idempotent Python."""
    raw = _load_original_broken_source(filename)
    assert raw.count("\n") == 1, f"Expected single-line input for {filename}"

    target = tmp_path / filename
    target.write_text(raw, encoding="utf-8")

    stats = reformat_file(target, in_place=True)
    expected_lines, expected_max_indent = EXPECTED_BROKEN_METRICS[filename]

    assert stats.status == "fixed"
    assert stats.changed is True
    assert stats.was_valid_before is False
    assert stats.is_valid_after is True
    assert stats.original_lines == 1
    assert stats.fixed_lines == expected_lines
    assert stats.max_indent_level == expected_max_indent

    repaired = target.read_text(encoding="utf-8")
    assert is_compilable_python(repaired, filename=filename)

    # Running a second time (both default and --force) must be 100% idempotent
    second = reformat_file(target, in_place=True)
    assert second.status == "unchanged"
    assert second.changed is False
    assert target.read_text(encoding="utf-8") == repaired

    forced = reformat_source(repaired, filename=filename, force=True)
    assert forced.source == repaired


def test_specific_structural_semantics_of_repo_examples() -> None:
    """Verify exact block nesting on the trickiest repo examples."""
    # broken1.py: `elif isinstance(n, ast.ClassDef):` pairs with outer `if isinstance(...)`
    b1 = reformat_source(_load_original_broken_source("broken1.py")).source
    tree1 = ast.parse(b1)
    top_for1 = [n for n in tree1.body if isinstance(n, ast.For)]
    assert len(top_for1) == 1
    # Inside `for f in files:` -> `try` and `for n in ast.walk(t):`
    assert isinstance(top_for1[0].body[0], ast.Try)
    assert isinstance(top_for1[0].body[1], ast.For)
    walk_if = top_for1[0].body[1].body[0]
    assert isinstance(walk_if, ast.If)
    assert len(walk_if.orelse) == 1 and isinstance(walk_if.orelse[0], ast.If)

    # broken5.py: code after `# survey common param...` must NOT be swallowed into comment
    b5 = reformat_source(_load_original_broken_source("broken5.py"))
    assert b5.inline_comments_split == 1
    assert b5.counts.loops == 2
    assert b5.counts.try_blocks == 1

    # broken6.py: `def prep(t):` contains two top-level loops + `t.body = ...` + `return`
    b6 = reformat_source(_load_original_broken_source("broken6.py")).source
    tree6 = ast.parse(b6)
    funcs6 = [n for n in tree6.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs6) == 1 and funcs6[0].name == "prep"
    assert isinstance(funcs6[0].body[-1], ast.Return)

    # broken11-13: shell heredoc bridges preserved as `# [shell]` comments
    for idx in (11, 12, 13):
        res = reformat_source(_load_original_broken_source(f"broken{idx}.py"))
        assert res.shell_bridges_commented == 1
        assert "# [shell] PY cd " in res.source


@pytest.mark.parametrize("filename", list(EXPECTED_BROKEN_METRICS.keys()))
def test_workspace_broken_files_compile_cleanly(
    filename: str, tmp_path: pathlib.Path
) -> None:
    """Workspace broken*.py files compile cleanly after running the autofixer on a copy."""
    src_path = REPO_ROOT / filename
    copied = tmp_path / filename
    shutil.copy2(src_path, copied)

    stats = reformat_file(copied, in_place=True)
    assert stats.is_valid_after is True
    assert is_compilable_python(copied.read_text(encoding="utf-8"), filename=filename)


# ---------------------------------------------------------------------------
# 2. Execution-Equivalence Round-Trip Tests (Single-Line & Stripped-Indent)
# ---------------------------------------------------------------------------


ROUNDTRIP_PROGRAMS: list[str] = [
    # Nested loops, try/except/continue, accumulators, elif/else
    textwrap.dedent(
        """\
        items = ["10", "bad", "25", "-4", "0"]
        pos = 0
        neg = 0
        zero = 0
        errors = 0
        for raw in items:
            try:
                val = int(raw)
            except ValueError:
                errors += 1; continue
            if val > 0:
                pos += val
            elif val < 0:
                neg += val
            else:
                zero += 1
        summary = (pos, neg, zero, errors)
        """
    ),
    # Functions, closures, recursion guard, ternary expressions, comprehensions
    textwrap.dedent(
        """\
        def make_scaler(factor: int):
            def scale(values: list[int]) -> list[int]:
                out = []
                for v in values:
                    adjusted = v * factor if v >= 0 else 0
                    out.append(adjusted)
                return out
            return scale
        scaler = make_scaler(3)
        result = scaler([2, -1, 5])
        """
    ),
    # Dataclass / class with multiple methods, @staticmethod, @property
    textwrap.dedent(
        """\
        class CounterBox:
            \"\"\"Simple bounded counter.\"\"\"
            limit: int
            def __init__(self, limit: int) -> None:
                self.limit = limit
                self._value = 0
            @property
            def value(self) -> int:
                return self._value
            @staticmethod
            def clamp(n: int, hi: int) -> int:
                if n > hi:
                    return hi
                return n
            def add(self, delta: int) -> int:
                self._value = CounterBox.clamp(self._value + delta, self.limit)
                return self._value
        box = CounterBox(10)
        first = box.add(6)
        second = box.add(9)
        """
    ),
    # Structural pattern matching (`match` / `case`) + soft-keyword variable `match`
    textwrap.dedent(
        """\
        def classify(event: tuple[str, int]) -> str:
            match = "unknown"
            match event:
                case ("click", x) if x > 0:
                    return f"pos:{x}"
                case ("click", _):
                    return "nonpos"
                case ("quit", code):
                    return f"bye:{code}"
            return match
        out = [classify(("click", 4)), classify(("click", 0)), classify(("quit", 1))]
        """
    ),
]


@pytest.mark.parametrize("program", ROUNDTRIP_PROGRAMS)
@pytest.mark.parametrize("mode", ["single_line", "stripped_lines"])
def test_execution_equivalence_after_corruption(program: str, mode: str) -> None:
    """Corrupting valid programs and repairing them preserves exact runtime behavior."""
    expected_ns = _exec_namespace(program)

    corrupted = (
        _collapse_to_single_line(program)
        if mode == "single_line"
        else _strip_all_indents(program)
    )
    assert not is_compilable_python(corrupted)

    repaired = reformat_source(corrupted).source
    assert is_compilable_python(repaired)
    actual_ns = _exec_namespace(repaired)

    for key in ("summary", "result", "first", "second", "out"):
        if key in expected_ns:
            assert actual_ns[key] == expected_ns[key]


# ---------------------------------------------------------------------------
# 3. Tricky Grammar, Comment, String, Async, and Matrix-Multiply Edge Cases
# ---------------------------------------------------------------------------


def test_inline_comments_with_python_keywords_and_backticks() -> None:
    """Comments containing `=`, `for`, `with`, `:`, `#`, and backticks split accurately."""
    collapsed = (
        "x = 1 "
        "# issue #42: spacing around = for args with `default` values "
        "y = x + 2 "
        "# --- compute final total --- "
        "total = x + y\n"
    )
    res = reformat_source(collapsed)
    assert res.inline_comments_split == 2
    ns = _exec_namespace(res.source)
    assert ns["total"] == 4
    assert "# issue #42: spacing around = for args with `default` values" in res.source
    assert "# --- compute final total ---" in res.source


def test_multiline_stripped_file_preserves_prose_comments_starting_with_keywords() -> None:
    """Multi-line stripped inputs must NOT split comments like `# now return value`."""
    stripped = (
        "def compute(a: int) -> int:\n"
        "# now return a + 1\n"
        "val = a * 2\n"
        "return val\n"
    )
    res = reformat_source(stripped)
    assert res.inline_comments_split == 0
    ns = _exec_namespace(res.source)
    assert ns["compute"](5) == 10


def test_multiline_docstring_and_multiline_signature_preserved() -> None:
    """Multi-line string literal contents remain byte-identical while signatures re-indent."""
    stripped = (
        "def format_msg(\n"
        "user: str,\n"
        "count: int = 1,\n"
        ") -> str:\n"
        '"""Header line.\n'
        "  Indented doc line.\n"
        '"""\n'
        'return f"{user}:{count}"\n'
    )
    res = reformat_source(stripped)
    ns = _exec_namespace(res.source)
    fn = ns["format_msg"]
    assert fn("alice", 3) == "alice:3"
    assert fn.__doc__ == "Header line.\n  Indented doc line.\n"


def test_async_functions_with_await_async_for_and_async_with() -> None:
    """Async constructs (`async def`, `async with`, `async for`, `await`) indent validly."""
    collapsed = (
        "async def fetch_all(client, urls: list[str]) -> list[str]: "
        "results: list[str] = [] "
        "async with client.session() as sess: "
        "async for body in sess.stream(urls): "
        "data = await body.read() "
        "if data: results.append(data) "
        "return results\n"
    )
    res = reformat_source(collapsed)
    assert is_compilable_python(res.source)
    assert res.counts.functions == 1
    assert res.counts.loops == 1


def test_matrix_multiplication_not_confused_with_decorator() -> None:
    """Binary `@` matrix multiplication before `def` is not misparsed as `@decorator`."""
    collapsed = "c = a @ b def helper(x: int) -> int: return x + 1\n"
    res = reformat_source(collapsed)
    tree = ast.parse(res.source)
    assert len(tree.body) == 2
    assert isinstance(tree.body[0], ast.Assign)
    assert isinstance(tree.body[0].value, ast.BinOp)
    assert isinstance(tree.body[0].value.op, ast.MatMult)
    assert isinstance(tree.body[1], ast.FunctionDef)
    assert tree.body[1].decorator_list == []


def test_main_guard_dedents_to_module_root() -> None:
    """`if __name__ == '__main__':` always dedents out of preceding 0-arg functions."""
    collapsed = (
        'def run() -> None: print("running") '
        'if __name__ == "__main__": run()\n'
    )
    res = reformat_source(collapsed)
    tree = ast.parse(res.source)
    assert len(tree.body) == 2
    assert isinstance(tree.body[0], ast.FunctionDef)
    assert isinstance(tree.body[1], ast.If)


def test_unrecoverable_syntax_raises_reformatter_error() -> None:
    """Genuinely broken non-Python gibberish raises ReformatterError cleanly."""
    with pytest.raises(ReformatterError):
        reformat_source("def (( unclosed_paren = === ???\n")


# ---------------------------------------------------------------------------
# 4. CLI, Batch Discovery, Dry-Run, JSON Output, and Error Handling Tests
# ---------------------------------------------------------------------------


def test_cli_dry_run_and_inplace_and_json(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI supports `--dry-run`, in-place repair, `--json`, and directory scanning."""
    sub = tmp_path / "pkg"
    sub.mkdir()
    f1 = sub / "broken_a.py"
    f2 = sub / "broken_b.py"
    raw_a = "def inc(x: int) -> int: if x > 0: return x + 1 return 0\n"
    raw_b = "vals = [] for i in range(4): vals.append(i * i) total = sum(vals)\n"
    f1.write_text(raw_a, encoding="utf-8")
    f2.write_text(raw_b, encoding="utf-8")

    # Dry-run must not modify files on disk
    rc_dry = main(["--dry-run", str(sub)])
    assert rc_dry == 0
    out_dry = capsys.readouterr().out
    assert "DRY-RUN" in out_dry
    assert f1.read_text(encoding="utf-8") == raw_a

    # In-place with --json modifies files and prints valid JSON BatchStats
    rc_json = main(["--json", str(sub)])
    assert rc_json == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_files"] == 2
    assert payload["fixed_files"] == 2
    assert payload["failed_files"] == 0
    assert is_compilable_python(f1.read_text(encoding="utf-8"))
    assert is_compilable_python(f2.read_text(encoding="utf-8"))

    # Batch API check
    batch: BatchStats = reformat_paths([sub], in_place=False)
    assert batch.unchanged_files == 2


def test_cli_missing_path_and_failed_file_exit_codes(
    tmp_path: pathlib.Path,
) -> None:
    """CLI returns exit code 2 on missing paths and 1 when a file fails to parse."""
    assert main([str(tmp_path / "does_not_exist.py")]) == 2

    bad = tmp_path / "corrupt.py"
    bad.write_text("def ((( ???\n", encoding="utf-8")
    assert main([str(bad)]) == 1


# ---------------------------------------------------------------------------
# 5. Self-Check: Full Type Annotations & Docstrings on result/*
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel_path",
    ["result/reformatter.py", "result/__init__.py", "result/__main__.py"],
)
def test_result_scripts_are_fully_type_annotated_and_documented(
    rel_path: str,
) -> None:
    """Every module, class, function, parameter, and return in `result/` is annotated & documented."""
    source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=rel_path)

    assert ast.get_docstring(tree), f"Missing module docstring in {rel_path}"

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            assert ast.get_docstring(node), (
                f"Missing class docstring on {node.name} in {rel_path}"
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert ast.get_docstring(node), (
                f"Missing docstring on function '{node.name}' in {rel_path}"
            )
            assert node.returns is not None, (
                f"Missing return annotation on {node.name} in {rel_path}"
            )
            args = node.args
            all_params = (
                args.posonlyargs
                + args.args
                + args.kwonlyargs
                + ([args.vararg] if args.vararg is not None else [])
                + ([args.kwarg] if args.kwarg is not None else [])
            )
            for param in all_params:
                if param.arg in ("self", "cls"):
                    continue
                assert param.annotation is not None, (
                    f"Missing annotation on parameter '{param.arg}' "
                    f"of '{node.name}' in {rel_path}"
                )

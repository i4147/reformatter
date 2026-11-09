src = open('infer_annotations.py').read()
def rep(old, new, tag=""):
    global src
    assert old in src, "MISSING: " + (tag or old[:70])
    src = src.replace(old, new, 1)
# 1. NoReturn only for functions whose single terminal statement raises
rep('''def always_raises(body: list[ast.stmt]) -> bool: if not body: return False last = body[-1] if isinstance(last, ast.Raise): return True''','''def always_raises(body: list[ast.stmt]) -> bool: """True when the only way out of the function is an exception.""" if not body or len(body) > 2: return False last = body[-1] if isinstance(last, ast.Raise): return True''', tag="noreturn")
# 2. dict[...] defaults always come from usage
rep(''' container_default = default_type if default_type in ( "list[Any]", "dict[str, Any]", "set[Any]", "tuple[Any, ...]", "frozenset[Any]", ) else ""''',''' container_default = default_type if default_type in ( "list[Any]", "dict[str, Any]", "set[Any]", "tuple[Any, ...]", "frozenset[Any]", "dict[Any, Any]", ) else "" if default_type.startswith("dict[") and default_type != "dict[str, Any]": default_type = ""''', tag="dictdefault")
# 3. visit_<Kind> / leave_<Kind> parameter types for libcst
rep(''' if name in ("original_node", "updated_node") and ctx.has_name("cst") and in_class: return "cst.CSTNode"''',''' if name in ("original_node", "updated_node") and ctx.has_name("cst") and in_class: kind = _visitor_kind(func) return f"cst.{kind}" if kind else "cst.CSTNode" if name == "node" and ctx.has_name("cst") and in_class and _visitor_kind(func): return f"cst.{_visitor_kind(func)}"''', tag="cstkind")
rep(''' if in_class and name == "node" and any("NodeVisitor" in b or "NodeTransformer" in b for b in ctx.class_bases): return "ast.AST"''',''' if in_class and name == "node" and any("NodeVisitor" in b or "NodeTransformer" in b for b in ctx.class_bases): kind = _visitor_kind(func) if kind and ctx.has_name("ast"): return f"ast.{kind}" return "ast.AST"''', tag="astkind")
rep('''def _union_none(ctx: FileCtx, typ: str) -> str:''','''def _visitor_kind(func: ast.AST) -> str: """`visit_FunctionDef` -> `FunctionDef` (the node class of that visitor hook).""" name = getattr(func, "name", "") for prefix in ("visit_", "leave_"): if name.startswith(prefix) and len(name) > len(prefix): kind = name[len(prefix):] if kind[:1].isupper(): return kind return "" def _union_none(ctx: FileCtx, typ: str) -> str:''', tag="cstkind2")
# 4. `str()`-conversion is weak evidence compared to a literal default
rep(''' elif fn in ("str",): ev.add("str", 8, hard=True)''',''' elif fn in ("str",): ev.add("str", 8)''', tag="strweak")
open('infer_annotations.py','w').write(src)
print("ok")

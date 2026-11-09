src = open('infer_annotations.py').read()
start = src.index(' if eq is not None:')
end = src.index(' # return annotation')
block = ''' if eq is not None: # annotate after the name, then keep exactly one space around `=` edits.append(Edit(name_tok.end[0], name_tok.end[1], f": {typ}", "param", f"{func.name}({lookup}): {typ}")) if _char_at(ctx, eq.start[0], eq.start[1] - 1) != " ": edits.append(Edit(eq.start[0], eq.start[1], " ", "param", f"{func.name}({lookup}) spacing")) if _char_at(ctx, eq.end[0], eq.end[1]) not in (" ", "\\t", "\\n", "\\r", ""): edits.append(Edit(eq.end[0], eq.end[1], " ", "param", f"{func.name}({lookup}) spacing")) else: edits.append(Edit(name_tok.end[0], name_tok.end[1], f": {typ}", "param", f"{func.name}({lookup}): {typ}")) '''
src = src[:start] + block + src[end:]
# varargs
old = ''' if default_repr in ("__VARARG__", "__KWARG__"): if name.startswith("_"): return "Any" ev = collect_param_evidence(ctx, func, name) typ = evidence_to_type(ev, ctx) return ctx.request(typ or "Any")'''
new = ''' if default_repr in ("__VARARG__", "__KWARG__"): if name.startswith("_"): return "Any" ev = collect_param_evidence(ctx, func, name) typ = evidence_to_type(ev, ctx) if typ in ("str", "int", "float", "bool", "bytes"): return typ return "Any"'''
assert old in src, "vararg"
src = src.replace(old, new)
# plural path names
old = ''' if lname in ("path", "paths", "p", "src", "dst", "dest", "target", "base_dir", "root", "directory", "dir",'''
new = ''' if lname in ("paths", "dirs", "files", "folders", "repos", "archives", "sources", "destinations"): return "list[Path]" if ctx.has_name("Path") else "list[str]" if lname in ("path", "p", "src", "dst", "dest", "target", "base_dir", "root", "directory", "dir",'''
assert old in src, "plural"
src = src.replace(old, new)
# arity
old = ''' if len(arity) == 1 and arity.pop() >= 2: n = len(shaped[0].value.elts) return "tuple[" + ", ".join(["Any"] * n) + "]"'''
new = ''' arity_n = arity.pop() if arity else 0 if arity_n >= 2: return "tuple[" + ", ".join(["Any"] * arity_n) + "]" if arity_n == 1: return "tuple[Any, ...]"'''
assert old in src, "arity"
src = src.replace(old, new)
open('infer_annotations.py','w').write(src)
print('ok')
# [shell] PY cd /home/user/bin_nov && git checkout -- . && python3 /tmp/ann/infer_annotations.py --write $(cat /tmp/ann/all_files.txt) 2>&1|tail -1 && sed -i 's/^from typing import Final$/from typing import Final, Iterable/' fztrans.py && python3 - <<'EOF'
import ast, pathlib, re
bad=[]
for f in sorted(pathlib.Path('.').glob('*.py')):
    src=f.read_text(); t=ast.parse(src)
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            seg=ast.get_source_segment(src,n) or ""
            head=seg.split(')')[0] if ')' in seg else seg
            for m in re.finditer(r"[A-Za-z_]\w*:[^=,()]+=\S", head):
                bad.append((f.name,n.name,m.group(0)[:40]))
            for m in re.finditer(r"[A-Za-z_]\w*:[^=,()]+\w= ", head):
                bad.append((f.name,n.name,m.group(0)[:40]))
print("spacing issues:", len(bad), bad[:8])

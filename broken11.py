src = open('infer_annotations.py').read()
def rep(old, new, tag=""):
    global src
    assert old in src, "MISSING: " + (tag or old[:70])
    src = src.replace(old, new, 1)
# 1. keep a trailing space after the original `=` when there was none
rep(''' edits.append(Edit(eq.start[0], eq.start[1], f": {typ} ", "param", f"{func.name}({lookup}): {typ}")) if _char_at(ctx, eq.end[0], eq.end[1]) not in (" ", "\\t", "\\n", "\\r", ""): edits.append(Edit(eq.end[0], eq.end[1], " ", "param", f"{func.name}({lookup}) spacing"))''',''' edits.append(Edit(eq.start[0], eq.start[1], f": {typ}", "param", f"{func.name}({lookup}): {typ}")) if _char_at(ctx, eq.end[0], eq.end[1]) not in (" ", "\\t", "\\n", "\\r", ""): edits.append(Edit(eq.end[0], eq.end[1], " ", "param", f"{func.name}({lookup}) spacing"))''', tag="eqspace")
# 2. multi-line signatures: never insert before a comma that starts the next line
rep(''' eq = next((t for t in seg_tokens[j + 1:] if t.type == tokenize.OP and t.string == "="), None) if eq is not None: if _char_at(ctx, eq.start[0], eq.start[1] - 1) == " ":''',''' eq = next((t for t in seg_tokens[j + 1:] if t.type == tokenize.OP and t.string == "="), None) next_tok = seg_tokens[-1] if seg_tokens else name_tok if next_tok.start[0] != name_tok.start[0] or next_tok is name_tok: # the parameter is spread over several lines; the edit is still safe pass if eq is not None and eq.start[0] != name_tok.start[0]: # `x` and `= default` on different lines: annotate after the name edits.append(Edit(name_tok.end[0], name_tok.end[1], f": {typ}", "param", f"{func.name}({lookup}): {typ}")) continue if eq is not None: if _char_at(ctx, eq.start[0], eq.start[1] - 1) == " ":''', tag="multiline")
open('infer_annotations.py','w').write(src)
print('ok')
# [shell] PY cd /home/user/bin_nov && git checkout -- . && python3 /tmp/ann/infer_annotations.py --write $(cat /tmp/ann/all_files.txt) 2>&1|tail -1 && sed -i 's/^from typing import Final$/from typing import Final, Iterable/' fztrans.py && python3 - <<'EOF'
import ast, pathlib, re
glued=[]
for f in sorted(pathlib.Path('.').glob('*.py')):
    src=f.read_text(); t=ast.parse(src)
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            seg=ast.get_source_segment(src,n) or ""
            head=seg.split(')')[0] if ')' in seg else seg
            for m in re.finditer(r"[A-Za-z_]\w*: [^=,)]+=[^ \n]", head):
                glued.append((f.name, n.name, m.group(0)[:50]))
print("glued:", len(glued), glued[:6])

import ast, pathlib
rows=[]
for f in sorted(pathlib.Path('.').glob('*.py')):
    t=ast.parse(f.read_text())
    miss=0; ret=0; funcs=0
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            funcs+=1
            a=n.args
            for p in a.posonlyargs+a.args+a.kwonlyargs+([a.vararg] if a.vararg else [])+([a.kwarg] if a.kwarg else []):
                if p.annotation is None:
                    miss+=1
            if n.returns is None:
                ret+=1
    if miss or ret:
        rows.append((miss+ret,miss,ret,funcs,f.name))
rows.sort(reverse=True)
for r in rows[:40]:
    print(r)
print("files needing work:", len(rows))

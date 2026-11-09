import ast, pathlib, collections
kinds=collections.Counter(); names=collections.Counter(); examples=collections.defaultdict(list)
retnone=0; retother=0
files=0
for f in sorted(pathlib.Path('.').glob('*.py')):
    src=f.read_text(); t=ast.parse(src)
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            positional_all = n.args.posonlyargs+n.args.args
            is_method = positional_all and positional_all[0].arg in ("self","cls")
            for p in n.args.posonlyargs+n.args.args+n.args.kwonlyargs:
                if p.annotation is None:
                    if is_method and p is positional_all[0] and p is n.args.args[0] if n.args.args else False:
                        kinds["self/cls"]+=1
                    else:
                        names[p.arg]+=1; kinds["other"]+=1
            if n.args.vararg and n.args.vararg.annotation is None:
                kinds["*args"]+=1; names["*"+n.args.vararg.arg]+=1
            if n.args.kwarg and n.args.kwarg.annotation is None:
                kinds["**kwargs"]+=1; names["**"+n.args.kwarg.arg]+=1
            if n.returns is None:
                # does the function only return bare/None?
                rets=[r for r in ast.walk(n) if isinstance(r,ast.Return)]
                if all(r.value is None or (isinstance(r.value,ast.Constant) and r.value.value is None) for r in rets):
                    retnone+=1
                else:
                    retother+=1
print(kinds); print("top missing param names:", names.most_common(40))
print("funcs missing return, always None:", retnone, "return values:", retother)

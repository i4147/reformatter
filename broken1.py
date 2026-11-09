import ast, pathlib, collections, re
files = sorted(pathlib.Path('.').glob('*.py'))
print("files:", len(files), "total bytes:", sum(f.stat().st_size for f in files))
tot=ann_params=un_params=ann_ret=un_ret=funcs=classes=0
errors=[]
for f in files:
    try:
        t=ast.parse(f.read_text())
    except Exception as e:
        errors.append((f.name,str(e))); continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            funcs+=1
            a=n.args
            ps=a.posonlyargs+a.args+a.kwonlyargs
            for p in ps:
                tot+=1
                if p.annotation is not None:
                    ann_params+=1
                else:
                    un_params+=1
            if a.vararg:
                if a.vararg.annotation is not None:
                    ann_params+=1
                else:
                    un_params+=1
            if a.kwarg:
                if a.kwarg.annotation is not None:
                    ann_params+=1
                else:
                    un_params+=1
            if n.returns is not None:
                ann_ret+=1
            else:
                un_ret+=1
        elif isinstance(n, ast.ClassDef):
            classes+=1
print("funcs",funcs,"classes",classes,"params",tot,"annotated params",ann_params,"missing",un_params,"annotated returns",ann_ret,"missing returns",un_ret)
print("parse errors", len(errors), errors[:10])

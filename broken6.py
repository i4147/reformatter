import sys, ast, copy
sys.path.insert(0,'.')
import infer_annotations as A
from pathlib import Path
p=Path('/home/user/bin_nov/valhtml.py')
ctx=A.load_ctx(p)
text, edits, imports = A.annotate_source(ctx)
open('/tmp/ann/valhtml_new.py','w').write(text)
# find diff between stripped dumps
def prep(t):
    t=copy.deepcopy(t)
    for n in ast.walk(t):
        if hasattr(n,'annotation'):
            n.annotation=None
        if hasattr(n,'returns'):
            n.returns=None
    for parent in ast.walk(t):
        for f in ('body','orelse','finalbody'):
            b=getattr(parent,f,None)
            if isinstance(b,list) and b:
                setattr(parent,f,[s for s in b if not (isinstance(s,ast.AnnAssign) and s.value is None)])
    t.body=[s for s in t.body if not isinstance(s,(ast.Import,ast.ImportFrom))]
    return ast.dump(t,annotate_fields=False,include_attributes=False)
a=prep(ctx.tree); b=prep(ast.parse(text))
print(len(a),len(b))
import difflib
for i,s in enumerate(difflib.ndiff(a.split(','), b.split(','))):
    if s[0] in '+-':
        print(i, s)

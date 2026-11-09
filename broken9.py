import ast, sys
sys.path.insert(0,'/tmp/ann')
import infer_annotations as A
from pathlib import Path
import glob
f=[p for p in glob.glob('/home/user/bin_nov/*.py') if 'create_setup_py' in Path(p).read_text().split('def create_setup_py')[0][-3000:]+'def create_setup_py' or 'create_setup_py' in Path(p).read_text()]
for p in f[:3]:
    src=Path(p).read_text()
    if 'def create_setup_py' not in src:
        continue
    t=ast.parse(src)
    for n in ast.walk(t):
        if isinstance(n,ast.FunctionDef) and n.name=='create_setup_py':
            print(p)
            print(ast.get_source_segment(src,n)[:600])
            break

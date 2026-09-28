"""Small generator used to write append_*.py answer scripts from a dict."""
import os, sys
COMMON = {28:(7,"high",""),29:(3,"high",""),30:(7,"medium","No intersecting-road crossing facility visible"),
          32:(1,"high",""),36:(1,"high",""),37:(6,"high",""),38:(4,"high",""),39:(1,"high",""),
          40:(4,"high",""),41:(3,"high",""),14:(1,"high",""),15:(4,"medium",""),16:(4,"medium",""),
          11:(1,"high",""),9:(2,"high",""),24:(1,"high","")}

def emit(fname, batch, road, name, d):
    full = dict(COMMON); full.update(d)
    lines = []
    for q in range(1, 42):
        code, conf, note = full[q]
        c = '""' if code == "" else code
        lines.append(f'    {q}: ({c}, "{conf}", "{note}"),')
    src = f'''import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vqa_helper import append_batch

b = {{
{chr(10).join(lines)}
}}
append_batch("{batch}", "{road}", "{name}", b)
'''
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, fname), "w", encoding="utf-8").write(src)
    os.system(f'python "{os.path.join(here, fname)}"')

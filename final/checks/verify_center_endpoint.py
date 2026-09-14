"""Scan existing full-grid endpoint fields; no PDE recomputation."""
from pathlib import Path
import json
import numpy as np
root=Path(__file__).resolve().parent
archive=Path.home()/'Documents'/'A题计算工作记录_20260910'/'程序与验证'
out={}
for tag in ['q23_s2560','q4_s2560']:
    with np.load(archive/(tag+'.npz')) as z:
        x=z['x']; cs=z['tableC']; ts=z['tabletimes']
        c=cs[-1]
        out[tag]={
            'time_s':float(ts[-1]),'nodes':len(c),
            'center_C':float(c[0]),'maximum_C':float(c.max()),
            'argmax_x':float(x[c.argmax()]),'surface_C':float(c[-1]),
            'largest_noncentral_C':float(c[1:].max()),
            'nodes_above_threshold_plus_1e_12':int(np.sum(c>.15+1e-12)),
            'max_excess_over_center':float((c-c[0]).max()),
            'table_times_center_is_max':bool(np.all(cs.max(axis=1)-cs[:,0]<1e-12))
        }
(root/'center_endpoint_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))

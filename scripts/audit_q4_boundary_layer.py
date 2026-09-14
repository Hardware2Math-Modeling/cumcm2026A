"""不重算：分别核验Q4全部材料节点与题目指定的固定物理输出位置。"""
import json
import numpy as np
from _bootstrap import setup
setup()
from common import export, paths
from common.problem_spec import Q4
from common.solution import Solution


def main():
    report=json.loads((paths.RESULTS_DIR/"validation/latent.json").read_text(encoding="utf-8"))
    rows=[];previous=None
    for row in [g for g in report['grid'] if g['q']=='q4']:
        n=row['n'];s=None
        for path in (paths.OUTPUTS_CACHE/"latent_validation").glob(f"q4_grid{n}_*.npz"):
            with np.load(path) as f:
                meta=json.loads(str(f['meta']))
                if abs(meta['event_time_s']-row['event_s'])<1e-7:
                    s=Solution(f['t'],f['r'],f['T'],f['C'],meta)
                    break
        if s is None:
            raise FileNotFoundError(f"缺少当前验证q4 {n}的精确缓存")
        if previous is not None:
            material=np.array([np.interp(previous.r,s.r,a) for a in s.C])
            error=abs(material-previous.C);i,j=np.unravel_index(np.argmax(error),error.shape)
            output=export.result_sheets(s,Q4)['Sheet1'].iloc[:,1:].to_numpy()
            old=export.result_sheets(previous,Q4)['Sheet1'].iloc[:,1:].to_numpy()
            rows.append({'coarse_n':previous.n_r,'fine_n':n,'material_max_C_difference':float(error[i,j]),
                         'at_time_s':float(s.t[i]),'at_xi':float(previous.r[j]/Q4.geometry.radius0),
                         'surface_distance_m':float((1-previous.r[j]/Q4.geometry.radius0)*s.meta['R'][i]),
                         'physical_output_max_C_difference':float(np.nanmax(abs(output-old))),
                         'surface_max_C_difference':float(np.max(abs(s.C[:,-1]-previous.C[:,-1])))})
        previous=s
    out={'rows':rows,'limitation':'Maximum material-field differences occur in an unresolved submicron surface layer. The delivered fixed physical positions and explicit surface value converge separately; no uniform four-decimal field accuracy is claimed.'}
    (paths.RESULTS_DIR/'validation/q4_boundary_layer.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(out,indent=2),flush=True)


if __name__=='__main__':
    main()

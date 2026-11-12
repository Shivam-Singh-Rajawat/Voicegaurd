$job = @'
#!/bin/bash
#PBS -N vg_indicresp
#PBS -q workq
#PBS -l select=1:ncpus=4:mem=12gb
#PBS -l walltime=00:30:00
#PBS -j oe
set -euo pipefail
cd "$HOME/voicegaurd"
export PYTHONPATH="$HOME/voicegaurd" CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
exec > "logs/indic_response_${PBS_JOBID}.log" 2>&1
.venv/bin/python - <<'PY'
import os,json
from pathlib import Path
import numpy as np,pandas as pd,soundfile as sf,sqlite3
from scipy.signal import resample_poly
from math import gcd
from voicegaurd_runtime.inference import Detector
r=Path.cwd();db=sqlite3.connect((r/'reports/voicegaurd_preprocessing/preprocessing.sqlite3').as_uri()+'?mode=ro',uri=True);files=[Path(row[0]) for row in db.execute("SELECT path FROM files WHERE dataset='indicvoices' AND status='ok' ORDER BY path")];db.close();rng=np.random.default_rng(20261109);chosen=[files[i] for i in sorted(rng.choice(len(files),min(100,len(files)),replace=False))];out=r/'reports'/('hinglish_response_'+os.environ['PBS_JOBID']);out.mkdir(exist_ok=False)
models={'synthetic':Detector(r/'checkpoints/v3_wavlm_attn_20_fixed/best.pt'),'replay':Detector(r/'checkpoints/v3_pa_wavlm/best.pt')};rows=[]
for i,path in enumerate(chosen,1):
 with sf.SoundFile(path) as f:
  n=int(round(f.samplerate*4.0375))
  for fraction in [.1,.5,.9]:
   start=int(max(0,f.frames-n)*fraction);f.seek(start);x=f.read(n,dtype='float32',always_2d=True).mean(axis=1)
   if f.samplerate!=16000:
    g=gcd(f.samplerate,16000);x=resample_poly(x,16000//g,f.samplerate//g)
   assert x.size and np.isfinite(x).all();row={'path':str(path),'offset_seconds':start/f.samplerate,'source_duration':f.frames/f.samplerate,'rms':float(np.sqrt(np.mean(x*x))),'language_source':'Local IndicVoices corpus; per-file language unverified','spoof_ground_truth':'unavailable'}
   for name,model in models.items():row[name+'_score']=model.score(x)['score']
   rows.append(row)
 if i%10==0:print('Files',i,'/',len(chosen),flush=True)
df=pd.DataFrame(rows);df.to_csv(out/'window_scores.csv',index=False);summary={'source':'local datasets/indicvoices; official provenance review pending','license':'unverified; no training or redistribution','sample_seed':20261109,'files':len(chosen),'windows':len(df),'scope':'Corpus response audit only;no spoof-labeled evaluation,language-specific EER or FPR claim. Fixed10/50/90percent offsets,no VAD;inspect RMS for silent windows. Original files unchanged.','score_quantiles':{name:df[name+'_score'].quantile([0,.25,.5,.75,.95,1]).to_dict() for name in models}}
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
PY

'@
$job | ssh -i "$env:USERPROFILE\.ssh\voicegaurd_codex" -o BatchMode=yes -o ConnectTimeout=12 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 shivam.15279@10.16.1.50 'tr -d ''\015'' | /opt/pbs/bin/qsub'
exit $LASTEXITCODE

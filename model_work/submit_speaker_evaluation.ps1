$job = @'
#!/bin/bash
#PBS -N vg_spkeval
#PBS -q workq
#PBS -l select=1:ncpus=4:mem=12gb
#PBS -l walltime=01:00:00
#PBS -j oe
set -euo pipefail
cd "$HOME/voicegaurd"
export PYTHONPATH="$HOME/voicegaurd/.speaker-deps:$HOME/voicegaurd" CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 HF_HUB_OFFLINE=1
exec > "logs/speaker_evaluation_${PBS_JOBID}.log" 2>&1
.venv/bin/python - <<'PY'
from pathlib import Path
import os,json,time
import numpy as np,pandas as pd,torch
from sklearn.metrics import roc_curve
from speechbrain.inference.speaker import EncoderClassifier
from voicegaurd_runtime.audio import load_audio
r=Path.cwd();base=r/'datasets/asvspoof2019/extracted/LA';protocol=base/'ASVspoof2019_LA_asv_protocols';out=r/'reports'/('speaker_evaluation_'+os.environ['PBS_JOBID']);out.mkdir(exist_ok=False)
files={p.stem:p for p in base.rglob('*.flac')};enroll={}
for p in sorted(protocol.glob('*dev*.trn.txt')):
 for line in p.read_text().splitlines():
  speaker,ids=line.split();assert speaker not in enroll;enroll[speaker]=ids.split(',')
speakers=sorted(enroll);assert len(speakers)==10
parts={'calibration':set(speakers[:5]),'assessment':set(speakers[5:])}
cm=pd.read_csv(r/'manifests/asv2019_la_dev.csv');actual={Path(row.audio_path).stem:str(row.speaker_id) for row in cm.itertuples() if str(row.label).lower()=='bonafide'}
background=sorted(set(actual.values())-set(speakers));assert len(background)==10
parts['calibration'].update(background[:5]);parts['assessment'].update(background[5:])
trials=[]
for line in (protocol/'ASVspoof2019.LA.asv.dev.gi.trl.txt').read_text().splitlines():
 claimed,uid,kind,label=line.split()
 if kind!='bonafide':continue
 assert label in ['target','nontarget']
 for split,group in parts.items():
  if claimed in group and actual.get(uid) in group:trials.append(dict(split=split,claimed=claimed,uid=uid,target=int(label=='target')))
assert trials; ids=set(x['uid'] for x in trials);enrollids={u for v in enroll.values() for u in v};assert not ids&enrollids
for split in parts:assert {x['target'] for x in trials if x['split']==split}=={0,1}
model=EncoderClassifier.from_hparams(source=str(r/'pretrained/speaker_assets'),savedir=str(out/'model'),overrides={'pretrained_path':str(r/'pretrained/speaker_assets')},run_opts={'device':'cpu'})
cache={}
for i,uid in enumerate(sorted(ids|enrollids),1):
 x,_=load_audio(files[uid]);z=model.encode_batch(torch.from_numpy(x[:96000]).unsqueeze(0)).detach().reshape(-1);assert z.numel()==192 and torch.isfinite(z).all();cache[uid]=torch.nn.functional.normalize(z,dim=0)
 if i%100==0:print('Embedded',i,flush=True)
np.savez_compressed(out/'embeddings.npz',**{k:v.numpy() for k,v in cache.items()})
templates={s:torch.nn.functional.normalize(torch.stack([cache[u] for u in ids]).mean(0),dim=0) for s,ids in enroll.items()}
for trial in trials:trial['score']=float(templates[trial['claimed']]@cache[trial['uid']])
df=pd.DataFrame(trials);df.to_csv(out/'trials.csv',index=False);cal=df[df.split=='calibration'];test=df[df.split=='assessment'];threshold=float(np.quantile(cal.loc[cal.target==0,'score'],.99,method='higher'))
summary={'calibration_threshold':threshold,'partitions':{k:sorted(v) for k,v in parts.items()},'scope':'ASVspoof LA development genuine trials; per partition 5 enrolled plus 5 background impostor speakers, all identities disjoint; not independent benchmark or spoof protection','crop_seconds':6,'metrics':{}}
for name,d in [('calibration',cal),('assessment',test)]:
 fpr,tpr,_=roc_curve(d.target,d.score);fnr=1-tpr;idx=np.argmin(abs(fpr-fnr));pred=d.score>threshold
 summary['metrics'][name]={'trials':len(d),'eer_percent':float((fpr[idx]+fnr[idx])*50),'fmr':float(pred[d.target==0].mean()),'fnmr':float((~pred[d.target==1]).mean())}
(out/'results.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
PY

'@
$job | ssh -i "$env:USERPROFILE\.ssh\voicegaurd_codex" -o BatchMode=yes -o ConnectTimeout=12 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 shivam.15279@10.16.1.50 'tr -d ''\015'' | /opt/pbs/bin/qsub'
exit $LASTEXITCODE

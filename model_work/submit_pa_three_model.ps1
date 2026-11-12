$job = @'
#!/bin/bash
#PBS -N vg_pafusion3
#PBS -q workq
#PBS -l select=1:ncpus=2:mem=4gb
#PBS -l walltime=00:15:00
#PBS -j oe
set -euo pipefail
cd "$HOME/voicegaurd"
exec > "logs/pa_three_model_${PBS_JOBID}.log" 2>&1
.venv/bin/python - <<'PY'
from pathlib import Path
import os,json
import numpy as np,pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_curve,roc_auc_score
r=Path.cwd();d=pd.read_csv(r/'manifests/asv2019_pa_dev.csv').rename(columns={'audio_path':'path'});d['truth']=d.label.astype(str).str.lower().map({'bonafide':0,'spoof':1});assert d.truth.notna().all() and len(d)==29700 and d.path.is_unique
for name,file in [('attention','scores/v3_pa_auto/attention_dev.csv'),('cnn','scores/v3_pa_auto/cnn_dev.csv'),('focused','scores/v3_pa_focus_dev/focused_attention_dev.csv')]:
 s=pd.read_csv(r/file);assert len(s)==29700 and s.path.is_unique
 d=d.merge(s[['path','score']].rename(columns={'score':name}),on='path',how='left',validate='one_to_one');assert np.isfinite(d[name]).all() and d[name].between(0,1).all()
d['mean_baseline']=d[['attention','cnn']].mean(axis=1);d['mean_attention_focused']=d[['attention','focused']].mean(axis=1);d['mean_three']=d[['attention','cnn','focused']].mean(axis=1)
names=['attention','cnn','focused','mean_baseline','mean_attention_focused','mean_three'];folds=[];predictions=[]
for fold,(train,test) in enumerate(GroupKFold(5).split(d,groups=d.speaker_id)):
 cal=d.iloc[train];part=d.iloc[test];assert set(cal.speaker_id).isdisjoint(part.speaker_id)
 for name in names:
  threshold=float(np.quantile(cal.loc[cal.truth==0,name],.99,method='higher'));y=part.truth.to_numpy();score=part[name].to_numpy();fpr,tpr,_=roc_curve(y,score);fnr=1-tpr;i=np.argmin(abs(fpr-fnr));pred=score>threshold
  folds.append(dict(fold=fold,model=name,eer_percent=float((fpr[i]+fnr[i])*50),auc=roc_auc_score(y,score),fpr=float(pred[y==0].mean()),recall=float(pred[y==1].mean())))
  p=part[['path','speaker_id','attack_id','truth']].copy();p['model']=name;p['prediction']=pred;p['fold']=fold;predictions.append(p)
out=r/'reports'/('pa_three_model_'+os.environ['PBS_JOBID']);out.mkdir(exist_ok=False);f=pd.DataFrame(folds);f.to_csv(out/'fold_metrics.csv',index=False);summary=f.groupby('model')[['eer_percent','auc','fpr','recall']].mean();summary.to_csv(out/'summary.csv');p=pd.concat(predictions);p.to_csv(out/'oof_predictions.csv',index=False);p[p.truth==1].groupby(['model','attack_id']).prediction.agg(['size','mean']).to_csv(out/'per_attack.csv');(out/'SCOPE.txt').write_text('Exploratory development-only fixed fusion candidates. Checkpoints already selected on development data. No independent test tuning; no generalization claim.');print(summary.to_string())
PY

'@
$job | ssh -i "$env:USERPROFILE\.ssh\voicegaurd_codex" -o BatchMode=yes -o ConnectTimeout=12 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 shivam.15279@10.16.1.50 'tr -d ''\015'' | /opt/pbs/bin/qsub'
exit $LASTEXITCODE

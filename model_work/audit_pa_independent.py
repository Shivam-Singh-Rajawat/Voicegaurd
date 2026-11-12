import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss

def logits(p):
    p = np.asarray(p, dtype=float)
    assert np.isfinite(p).all() and ((0 <= p) & (p <= 1)).all()
    q = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(q / (1 - q)).reshape(-1, 1)

dev = pd.read_csv("reports/v3_pa_stabilization/phase3/grouped_cv_predictions.csv")
assert len(dev) == 29700 and dev.path.is_unique and dev.speaker_id.notna().all()
assert set(dev.label) == {0, 1}
fit = LogisticRegression().fit(logits(dev.score_attention), dev.label)
print("Frozen candidate", json.dumps({"slope":fit.coef_[0,0], "intercept":fit.intercept_[0]}), flush=True)

manifest = pd.read_csv("manifests/asv2019_pa_eval.csv")
train = pd.read_csv("manifests/asv2019_pa_train.csv")
assert manifest.speaker_id.notna().all() and train.speaker_id.notna().all()
assert not set(manifest.speaker_id) & (set(dev.speaker_id) | set(train.speaker_id))
protocol = pd.read_csv("datasets/asvspoof2019/extracted/PA/ASVspoof2019_PA_cm_protocols/ASVspoof2019.PA.cm.eval.trl.txt",
                       sep=r"\s+", header=None, names=["speaker","audio_id","condition","attack","truth"])
m = manifest.merge(protocol, on="audio_id", validate="one_to_one")
assert len(m) == len(manifest) == len(protocol) == 134730
assert m.speaker_id.eq(m.speaker).all() and m.label.eq(m.truth).all() and m.attack_id.eq(m.attack).all()
source = Path("scores/v3_pa_auto/selected_pa_eval.csv")
print("Score SHA256", hashlib.sha256(source.read_bytes()).hexdigest())
scores = pd.read_csv(source)
d = m.merge(scores[["path","score"]], left_on="audio_path", right_on="path", validate="one_to_one")
assert len(d) == len(m) == len(scores) and set(d.binary_label) == {0, 1}
d["candidate"] = fit.predict_proba(logits(d.score))[:,1]
cutoff = json.loads(Path("reports/v3_pa_auto/selected_model.json").read_text())["frozen_threshold"]
assert cutoff == 0.9364579916000366
d["flag"] = d.score > cutoff
def show(name, g):
    y = g.binary_label
    genuine = g[~y.astype(bool)]
    spoof = g[y.astype(bool)]
    print(name,len(g),*[round(v,6) for v in (
        log_loss(y,g.score,labels=[0,1]),log_loss(y,g.candidate,labels=[0,1]),
        brier_score_loss(y,g.score),brier_score_loss(y,g.candidate))],
        "false_alarms",int(genuine.flag.sum()),len(genuine),"detected",int(spoof.flag.sum()),len(spoof))
show("overall", d)
for key in ("condition","attack_id"):
    for value, group in d.groupby(key, dropna=False):
        show(f"{key}={value}",group)

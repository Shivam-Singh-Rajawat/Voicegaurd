import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss
d=pd.read_csv("reports/v3_pa_stabilization/phase3/grouped_cv_predictions.csv")
if (d.empty or d[["path", "speaker_id", "fold", "label", "score_attention"]].isna().any().any()
        or not d.path.is_unique or d.groupby("speaker_id").fold.nunique().max() != 1
        or d.fold.nunique() < 2 or not d.label.isin([0, 1]).all()
        or not d.score_attention.between(0, 1).all()):
    raise ValueError("Expected unique labeled PA scores with speaker-disjoint folds")
p=d.score_attention.to_numpy()
y=d.label.to_numpy()
q=np.clip(p,1e-7,1-1e-7)
x=np.log(q/(1-q)).reshape(-1,1)
out=np.empty(len(d))
for fold in sorted(d.fold.unique()):
    test=(d.fold==fold).to_numpy()
    model=LogisticRegression().fit(x[~test],y[~test])
    out[test]=model.predict_proba(x[test])[:,1]
    print(fold,model.coef_[0,0],log_loss(y[test],p[test]),log_loss(y[test],out[test]))
print("overall",log_loss(y,p),log_loss(y,out),brier_score_loss(y,p),brier_score_loss(y,out))

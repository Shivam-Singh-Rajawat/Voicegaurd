# Next bounded model audit

Read actual official LA/PA train, dev and eval manifests, and v3 LA/ASV5 select
and calib manifests. Report pairwise path and known-speaker intersections,
record counts and missing identity metadata. Evaluate split integrity before
retraining. Run via CPU PBS with a new reports directory and no source mutation.

Do not assume split_dev.py produced speaker-disjoint manifests: it has a fallback.
Do not use eval scores for choosing epochs or thresholds. Collect learning curves
from history.jsonl and report per-domain dev loss/EER and train loss by epoch.
Loss differences with sampled/augmented training are not directly comparable.

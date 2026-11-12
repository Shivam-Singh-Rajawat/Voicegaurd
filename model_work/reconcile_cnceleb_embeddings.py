"""Verify complete shard coverage and combine embeddings without rescoring."""
import csv
from collections import Counter
import hashlib
from pathlib import Path
import sys

import numpy as np

manifest, output, *shards = map(Path, sys.argv[1:])
if hashlib.sha256(manifest.read_bytes()).hexdigest() != "effb9f5f8fafd46c042938c1a8e28e2808c1010b615f3be8d5464beb08f7e9fa":
    raise ValueError("Unexpected manifest digest")
with manifest.open(newline="") as handle:
    rows = list(csv.DictReader(handle))
if len(shards) != 12 or len(set(shards)) != 12:
    raise ValueError("Provide the 12 completed shard directories")

outcomes = {}
embeddings = {}
for shard in shards:
    scored = set()
    with (shard / "coverage.csv").open(newline="") as handle:
        for record in csv.DictReader(handle):
            index = int(record["index"])
            if (not 0 <= index < len(rows) or index in outcomes
                    or rows[index]["path"] != record["path"]
                    or record["status"] not in {"scored", "abstained", "failed"}):
                raise ValueError(f"Invalid or duplicate coverage in {shard}: {index}")
            outcomes[index] = record["status"]
            if record["status"] == "scored":
                scored.add(index)
    with np.load(shard / "embeddings.npz", allow_pickle=False) as data:
        indices = data["indices"].tolist()
        vectors = data["vectors"]
        if (set(indices) != scored or len(indices) != len(scored)
                or len(vectors) != len(indices) or not np.isfinite(vectors).all()):
            raise ValueError(f"Embedding/coverage mismatch in {shard}")
        embeddings.update(zip(indices, vectors))

if len(outcomes) != len(rows):
    raise ValueError(f"Missing coverage for {len(rows) - len(outcomes)} recordings")
indices = sorted(embeddings)
with output.open("xb") as handle:
    np.savez(handle, indices=np.asarray(indices, dtype=np.int64),
             vectors=np.asarray([embeddings[index] for index in indices]))
print(f"Planned {len(rows)}. Outcomes: {dict(Counter(outcomes.values()))}")

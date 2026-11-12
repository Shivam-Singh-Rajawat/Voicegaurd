"""Freeze enrollment and all eligible probes from unused development speakers."""
import csv
from collections import Counter, defaultdict
from pathlib import Path
import random
import re
import sys

root = Path(sys.argv[1])
archive = root / "CN-Celeb_flac"
development = set((archive / "dev/dev.lst").read_text().split())
evaluation = {
    Path(line.split()[-1]).stem.split("-")[0]
    for name in ("enroll.lst", "test.lst")
    for line in (archive / "eval/lists" / name).read_text().splitlines()
    if line.strip()
}
if development & evaluation:
    raise ValueError("Development and evaluation speaker IDs overlap")
with (root / "speaker_dev_v1.csv").open(newline="") as previous:
    excluded = {row["speaker"] for row in csv.DictReader(previous)}
sessions = defaultdict(lambda: defaultdict(set))
pattern = re.compile(r"CN-Celeb_flac/data/(id\d+)/(\w+)-(\d+)-\d+\.flac")
for path in (root / "archive.inventory.txt").read_text(encoding="utf-8-sig").splitlines():
    match = pattern.fullmatch(path)
    if match and match[1] in development - excluded:
        sessions[match[1]][match[2], match[3]].add(path)

speakers = sorted(s for s, groups in sessions.items() if len(groups) >= 3)
rng = random.Random(20261112)
rng.shuffle(speakers)
counts = Counter()
with (root / "speaker_dev_full_v1.csv").open("x", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(("split", "speaker", "role", "genre", "session", "path"))
    for index, speaker in enumerate(speakers):
        split = "calibration" if index < len(speakers) // 2 else "validation"
        counts[split, "speakers"] += 1
        groups = sessions[speaker]
        refs = rng.sample(sorted(groups), 2)
        for key in sorted(groups):
            files = sorted(groups[key])
            if key in refs:
                role = "reference_" + "ab"[refs.index(key)]
                counts[split, "excluded_enrollment_session"] += len(files) - 1
                files = [rng.choice(files)]
            else:
                role = "probe"
            for path in files:
                writer.writerow((split, speaker, role, *key, path))
            counts[split, role] += len(files)
print(dict(counts))

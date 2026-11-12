"""Select speaker-disjoint development trials without opening assessment scores."""
import csv
import random
import re
from collections import defaultdict
from pathlib import Path
import sys

inventory, identities, output, *previous = map(Path, sys.argv[1:])
allowed = set(identities.read_text().split())
if previous:
    with previous[0].open(newline="", encoding="utf-8") as handle:
        allowed.difference_update(row["speaker"] for row in csv.DictReader(handle))
sessions = defaultdict(lambda: defaultdict(list))
member = re.compile(r"CN-Celeb_flac/data/(id\d+)/([\w]+)-(\d+)-\d+\.flac")
for path in inventory.read_text(encoding="utf-8-sig").splitlines():
    match = member.fullmatch(path)
    if match and match[1] in allowed:
        sessions[match[1]][match[2], match[3]].append(path)

rng = random.Random(20261111 if previous else 20261110)
eligible = sorted(speaker for speaker in sessions if len(sessions[speaker]) >= 3)
if len(eligible) < 80:
    raise ValueError("Need at least 80 development identities with three session keys")
selected = rng.sample(eligible, 80)
with output.open("x", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(("split", "speaker", "reference_a", "reference_b", "probe", "probe_genre"))
    for index, speaker in enumerate(selected):
        keys = rng.sample(sorted(sessions[speaker]), 3)
        paths = [rng.choice(sorted(sessions[speaker][key])) for key in keys]
        writer.writerow(("calibration" if index < 40 else "validation", speaker, *paths, keys[2][0]))
print(f"{len(eligible)} eligible identities; 40 calibration, 40 validation, 240 planned files")

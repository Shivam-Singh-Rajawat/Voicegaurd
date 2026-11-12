"""Freeze a bounded CN-Celeb1 evaluation cohort before scoring."""
import csv
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
import random
import sys


def session_key(stem):
    return tuple(stem.rsplit("-", 1)[0].split("-"))


lists, destination = map(Path, sys.argv[1:])
enrollments = dict(line.split() for line in (lists / "enroll.lst").read_text().splitlines())
sessions = {}
for line in (lists / "enroll.map").read_text().splitlines():
    claim, *sources = line.split()
    assert sources and claim not in sessions
    sessions[claim] = {session_key(PurePosixPath(source).stem) for source in sources}
assert enrollments.keys() == sessions.keys()

rng = random.Random(20261110)
counts = Counter()
samples = defaultdict(list)
with (lists / "trials.lst").open() as trials:
    for line in trials:
        claim, probe, label = line.split()
        path = PurePosixPath(probe)
        actual, genre, session = session_key(path.stem)
        actual_claim = actual + "-enroll"
        assert claim in enrollments
        assert label in {"0", "1"} and (label == "1") == (actual_claim == claim)
        if actual_claim not in sessions:
            counts["excluded_missing_enrollment_metadata_" + label] += 1
            continue
        if (genre, session) in sessions[actual_claim]:
            counts["excluded_" + label] += 1
            continue
        key = claim, label
        counts[key] += 1
        row = (claim, str(PurePosixPath(enrollments[claim]).with_suffix(".flac")),
               str(path.with_suffix(".flac")), actual, genre, session, label)
        bucket = samples[key]
        if len(bucket) < 12:
            bucket.append(row)
        else:
            index = rng.randrange(counts[key])
            if index < 12:
                bucket[index] = row

with destination.open("x", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(("claim", "enrollment", "probe", "actual", "genre", "session", "target"))
    for claim in sorted(enrollments):
        genuine = samples.get((claim, "1"), [])
        impostor = samples.get((claim, "0"), [])
        size = min(len(genuine), len(impostor))
        writer.writerows(genuine[:size] + impostor[:size])
print({key: value for key, value in counts.items() if isinstance(key, str)})

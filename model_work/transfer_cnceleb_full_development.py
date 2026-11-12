"""Resume the frozen CN-Celeb bundle over SSH under the HPC write lock."""
import re
import shlex
import subprocess
import sys
from pathlib import Path

bundle = Path(sys.argv[1])
digest = bundle.with_suffix(".sha256.txt").read_text(encoding="utf-8-sig").strip().lower()
if not re.fullmatch(r"[0-9a-f]{64}", digest):
    raise ValueError("Invalid completed bundle digest")
size = bundle.stat().st_size
ssh = [
    "ssh", "-i", str(Path.home() / ".ssh" / "voicegaurd_codex"),
    "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
    "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
    "shivam.15279@10.16.1.50",
]
prefix = "cd ~/voicegaurd && umask 077 && flock -n -E 75 .automation-write.lock bash -ec "
paths = 'f=datasets/cnceleb1_official/speaker_dev_full_v1.verified.tar; p="$f.part"; '
offset_check = 'n=0; if test -f "$p"; then n=$(stat -c %s "$p"); fi; '
probe = subprocess.check_output(ssh + [
    prefix + "'" + paths + 'if test -f "$f"; then echo finalized; exit; fi; ' + offset_check + 'echo "$n"' + "'"
], stdin=subprocess.DEVNULL, text=True, timeout=45).strip()
if probe == "finalized":
    sys.exit(subprocess.call(ssh + [
        prefix + "'" + paths + f'echo "{digest}  $f" | sha256sum -c -' + "'"
    ]))
offset = int(probe)
if not 0 <= offset <= size:
    raise ValueError("Remote partial size is inconsistent")
receiver = """import os, select, sys
while True:
    if not select.select([0], [], [], 180)[0]:
        sys.exit("Upload idle for 180 seconds; partial file preserved")
    data = os.read(0, 1024 * 1024)
    if not data:
        break
    sys.stdout.buffer.write(data)
"""
receive = prefix + shlex.quote(
    paths + 'test ! -e "$f"; ' + offset_check
    + f'test "$n" = {offset}; python3 -c {shlex.quote(receiver)} >> "$p"; '
    + f'test "$(stat -c %s "$p")" = {size}; '
    + f'echo "{digest}  $p" | sha256sum -c -; mv -n "$p" "$f"'
)
print(f"Uploading from byte {offset} of {size}", flush=True)
with bundle.open("rb") as source:
    source.seek(offset)
    sys.exit(subprocess.call(ssh + [receive], stdin=source))

from pathlib import Path
import subprocess
import sys

bundle = Path(sys.argv[1])
digest = "8efa60e71be5b9d7f2932c1ff625739dadaf96d33418c872b28e3e7b618da39f"
remote = """cd ~/voicegaurd && umask 077 && flock -n -E 75 .automation-write.lock bash -ec 'f=datasets/cnceleb1_official/speaker_dev_v1.tar; test ! -e "$f"; test ! -e "$f.part"; cat > "$f.part"; printf "%s  %s\\n" DIGEST "$f.part" | sha256sum -c -; mv -n "$f.part" "$f"'""".replace("DIGEST", digest)
with bundle.open("rb") as source:
    sys.exit(subprocess.call([
        "ssh", "-i", str(Path.home() / ".ssh" / "voicegaurd_codex"),
        "-o", "BatchMode=yes", "-o", "ConnectTimeout=6",
        "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
        "shivam.15279@10.16.1.50", remote,
    ], stdin=source))

$jobText=Get-Content -Raw model_work/cnceleb_development.pbs
$pre=@'
set -euo pipefail
pbs=/opt/pbs/bin
active=$("$pbs/qstat" -u "$USER")
status=reports/PROJECT_STATUS.md
if printf '%s\n' "$active" | grep -q vg_cndev1 || grep -qF 'CN-Celeb development pilot submitted as' "$status"; then exit 0; fi
d=datasets/cnceleb1_official
stage="$d/speaker_dev_v1"
verify() {
  printf '%s  %s\n' 0560d1d4c0eb8df284dadbf0922d2226cfa070c2c855293d6515573b228c2d0e "$1/speaker_dev_v1.csv" | sha256sum -c -
  test "$(find "$1/CN-Celeb_flac/data" -type f -name '*.flac' -size +0c | wc -l)" = 240
}
if ! test -e "$stage"; then
  tmp=$(mktemp -d "$d/speaker_dev_v1.extract.XXXXXX")
  tar -xf "$d/speaker_dev_v1.tar" -C "$tmp"
  verify "$tmp"
  mv -T "$tmp" "$stage"
fi
verify "$stage"
job=$("$pbs/qsub" <<'PBS_JOB'
'@
$post=@'
PBS_JOB
)
printf '\nCN-Celeb development pilot submitted as %s. Separate 40/40 speaker splits.\n' "$job" >> "$status"
printf '%s\n' "$job"
'@
& .\model_work\Invoke-VoicegaurdHpcWrite.ps1 -BashScript ($pre+"`n"+$jobText.TrimEnd()+"`n"+$post)
exit $LASTEXITCODE

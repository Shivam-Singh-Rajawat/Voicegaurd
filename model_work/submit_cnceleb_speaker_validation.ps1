param()
$pbsText = Get-Content -Raw (Join-Path $PSScriptRoot 'cnceleb_speaker_validation.pbs')
$pre = @'
set -euo pipefail
pbs=/opt/pbs/bin
active=$("$pbs/qstat" -u "$USER")
status=reports/PROJECT_STATUS.md
if printf '%s\n' "$active" | grep -q vg_cnspkv1 || grep -qF 'CN-Celeb1 bounded-decode retry submitted as' "$status"; then exit 0; fi
previous=$("$pbs/qstat" -xf 46188.mgmt01)
printf '%s\n' "$previous" | grep -q 'job_state = F'
printf '%s\n' "$previous" | grep -q 'Exit_status = 1'
test ! -e reports/cnceleb_speaker_46188.mgmt01/summary.json
d=datasets/cnceleb1_official
bundle="$d/session_disjoint_v1.tar"
stage="$d/session_disjoint_v1"
test "$(stat -c %s "$bundle")" = 705869312
verify() {
  printf '%s  %s\n' df6324bcf1787878dd416c178a36564098ba207f2b620d9e3b61789d2dc264ad "$1/session_disjoint_v1.csv" | sha256sum -c -
  test "$(find "$1/CN-Celeb_flac/eval" -type f -name '*.flac' -size +0c | wc -l)" = 3286
}
if ! test -e "$stage"; then
  tmp=$(mktemp -d "$d/session_disjoint_v1.extract.XXXXXX")
  tar -xf "$bundle" -C "$tmp"
  verify "$tmp"
  mv -T "$tmp" "$stage"
fi
verify "$stage"
job=$("$pbs/qsub" <<'CN_PBS'
'@
$post = @'
CN_PBS
)
printf '\nCN-Celeb1 bounded-decode retry submitted as %s after 46188 duration guard failure. Same frozen 3634 trials and cutoff.\n' "$job" >> "$status"
printf '%s\n' "$job"
'@
$script = $pre + "`n" + $pbsText.TrimEnd() + "`n" + $post
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript $script
exit $LASTEXITCODE

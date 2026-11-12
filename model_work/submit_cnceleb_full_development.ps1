$ErrorActionPreference = "Stop"
$worker = Get-Content -Raw (Join-Path $PSScriptRoot 'encode_cnceleb_full_development.py')
$arrayJob = Get-Content -Raw (Join-Path $PSScriptRoot 'cnceleb_full_development.pbs')
$pre = @'
set -euo pipefail
pbs=/opt/pbs/bin
root=datasets/cnceleb1_official
bundle="$root/speaker_dev_full_v1.verified.tar"
status=reports/PROJECT_STATUS.md
active=$("$pbs/qstat" -u "$USER")
if grep -Eq 'vg_cnfull|vg_cnstage' <<< "$active"; then exit 0; fi
if grep -Eq 'CN-Celeb full staging submitted as|CN-Celeb full array submitted as' "$status"; then
  echo 'Prior submission recorded. Reconcile PBS history before retrying.' >&2
  exit 1
fi
test "$(stat -c %s "$bundle")" = 9508900864
test ! -e "$bundle.part"
worker="$root/encode_cnceleb_full_development.py"
test ! -e "$worker"
cat > "$worker" <<'PY_WORKER'
'@
$stage = @'
PY_WORKER
stage_job=$("$pbs/qsub" <<'STAGE_JOB'
#!/bin/bash
#PBS -N vg_cnstage
#PBS -q workq
#PBS -l select=1:ncpus=1:mem=2gb
#PBS -l walltime=01:00:00
#PBS -j oe
set -euo pipefail
cd "$HOME/voicegaurd"
exec > "logs/cnceleb_full_stage_${PBS_JOBID}.log" 2>&1
root=datasets/cnceleb1_official
stage="$root/speaker_dev_full_v1"
test ! -e "$stage"
tmp=$(mktemp -d "$root/speaker_dev_full_v1.extract.XXXXXX")
tar -xf "$root/speaker_dev_full_v1.verified.tar" -C "$tmp"
printf '%s  %s\n' effb9f5f8fafd46c042938c1a8e28e2808c1010b615f3be8d5464beb08f7e9fa "$tmp/speaker_dev_full_v1.csv" | sha256sum -c -
test "$(find "$tmp/CN-Celeb_flac/data" -type f -name '*.flac' -size +0c | wc -l)" = 60189
cp "$root/encode_cnceleb_full_development.py" "$tmp/"
mv -T "$tmp" "$stage"
STAGE_JOB
)
printf '\nCN-Celeb full staging submitted as %s.\n' "$stage_job" >> "$status"
printf '%s\n' "$stage_job"
array_job=$("$pbs/qsub" -W "depend=afterok:$stage_job" <<'ARRAY_JOB'
'@
$post = @'
ARRAY_JOB
)
printf '\nCN-Celeb full array submitted as %s after staging %s.\n' "$array_job" "$stage_job" >> "$status"
printf '%s\n' "$array_job"
'@
$script = $pre + "`n" + $worker.TrimEnd() + "`n" + $stage + "`n" + $arrayJob.TrimEnd() + "`n" + $post
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript $script
exit $LASTEXITCODE

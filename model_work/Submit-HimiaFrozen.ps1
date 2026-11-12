$ErrorActionPreference = 'Stop'
$bytes = [IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'himia_frozen.pbs'))
$encoded = [Convert]::ToBase64String($bytes)
$remote = @'
set -eu
jobs=$(/opt/pbs/bin/qstat -u shivam.15279)
if printf '%s\n' "$jobs" | grep -q vg_himia_eval; then
    printf '%s\n' "$jobs"
    exit 0
fi
if compgen -G 'reports/himia_frozen_*/summary.json' >/dev/null; then
    echo 'Existing HI-MIA result'
    exit 0
fi
test -s datasets/himia_openslr85/test_v2.tar.gz
test -s datasets/himia_openslr85/archive.list
printf '%s' '__PAYLOAD__' | base64 -d | tr -d '\015' | /opt/pbs/bin/qsub
'@
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript ($remote.Replace('__PAYLOAD__', $encoded))
exit $LASTEXITCODE

$ErrorActionPreference = 'Stop'
$payload = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'jspaw_audit.pbs')))
$remote = @'
set -eu
test -s datasets/jspaw_interspeech/jspaw.zip
jobs=$(/opt/pbs/bin/qstat -u shivam.15279)
if printf '%s\n' "$jobs" | grep -q vg_jspaw_audit; then
    printf '%s\n' "$jobs"
    exit 0
fi
if compgen -G 'reports/jspaw_audit_*/summary.json' >/dev/null; then
    printf '%s\n' reports/jspaw_audit_*/summary.json
    exit 0
fi
printf '%s' '__PAYLOAD__' | base64 -d | tr -d '\015' | /opt/pbs/bin/qsub
'@
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript ($remote.Replace('__PAYLOAD__', $payload))
exit $LASTEXITCODE

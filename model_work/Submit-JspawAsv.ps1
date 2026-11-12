$ErrorActionPreference = 'Stop'
$payload = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'jspaw_frozen_asv.pbs')))
$remote = @'
set -eu
jobs=$(/opt/pbs/bin/qstat -u shivam.15279)
if printf '%s\n' "$jobs" | grep -q vg_jspaw_as; then printf '%s\n' "$jobs"; exit 0; fi
if compgen -G 'reports/jspaw_asv_*/summary.json' >/dev/null; then printf '%s\n' reports/jspaw_asv_*/summary.json; exit 0; fi
audit=$(/opt/pbs/bin/qstat -xf 46561.mgmt01)
if printf '%s\n' "$audit" | grep -q 'job_state = F'; then
    test -s reports/jspaw_audit_46561.mgmt01/summary.json
    printf '%s\n' "$audit" | grep -q 'Exit_status = 0$'
    printf '%s' '__PAYLOAD__' | base64 -d | tr -d '\015' | /opt/pbs/bin/qsub
else
    printf '%s' '__PAYLOAD__' | base64 -d | tr -d '\015' | /opt/pbs/bin/qsub -W depend=afterok:46561.mgmt01
fi
'@
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript ($remote.Replace('__PAYLOAD__', $payload))
exit $LASTEXITCODE

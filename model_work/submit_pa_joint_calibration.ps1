$job = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'pa_joint_calibration.pbs') -Raw).TrimEnd()
$remote = @'
if /opt/pbs/bin/qstat -u "$USER" | grep -q vg_pajoin || compgen -G 'reports/pa_joint_*/summary.json' >/dev/null; then
    echo "PA joint calibration already present"
    exit 76
fi
test -f reports/pa_partition_46093.mgmt01/summary.json
test -f reports/pa_partition_46093.mgmt01/trials.csv
test -f reports/pa_partition_46093.mgmt01/enrollment.json
id=$(/opt/pbs/bin/qsub <<'PAJOB'
__JOB__
PAJOB
)
echo "$id"
printf '\nQueued %s for PA/ECAPA joint development pilot in preregistered aaa/bbb/ccc enrollment environments, preserving 46093 speaker partitions. Compare frozen PA plus calibration-derived PA speaker cutoff against descriptive fusion at the stated priors. Report abstention.\n' "$id" >> reports/PROJECT_STATUS.md
'@
$remote = $remote.Replace('__JOB__', $job)
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript $remote
exit $LASTEXITCODE

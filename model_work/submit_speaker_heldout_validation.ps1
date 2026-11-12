$job = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'speaker_heldout_validation.pbs') -Raw).TrimEnd()
$remote = @'
if /opt/pbs/bin/qstat -u "$USER" | grep -q vg_spkhol || compgen -G 'reports/speaker_heldout_*/summary.json' >/dev/null; then
    echo "Held-out speaker evaluation already present"
    exit 76
fi
test -f reports/speaker_evaluation_46018.mgmt01/results.json
id=$(/opt/pbs/bin/qsub <<'HOLDJOB'
__JOB__
HOLDJOB
)
echo "$id"
printf '\n46108 finished Exit_status0 and37 tests passed. Queued %s for one-time held-out ASVspoof LA evaluation speaker check using frozen LA-dev cosine cutoff .4769288897514343 and deterministic target/impostor sampling. No threshold fitting. Validate identity and enrollment disjointness before interpreting.\n' "$id" >> reports/PROJECT_STATUS.md
'@
$remote = $remote.Replace('__JOB__',$job)
& (Join-Path $PSScriptRoot 'Invoke-VoicegaurdHpcWrite.ps1') -BashScript $remote
exit $LASTEXITCODE

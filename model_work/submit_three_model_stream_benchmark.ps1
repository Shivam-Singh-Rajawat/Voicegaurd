$job = (Get-Content -LiteralPath model_work/three_model_stream_benchmark.pbs -Raw).TrimEnd()
$remote = @'
if /opt/pbs/bin/qstat -u "$USER" | grep -q vg_streamb || compgen -G 'reports/stream_benchmark_*/summary.json' >/dev/null; then
    echo "Three-model streaming benchmark already present"
    exit 76
fi
test -f reports/multievidence_46071.mgmt01/summary.json
id=$(/opt/pbs/bin/qsub <<'STREAMJOB'
__JOB__
STREAMJOB
)
echo "$id"
printf '\n46099 Exit_status0,36 HPC tests passed. Queued %s for three-model CPU streaming on 60 seconds of authorized LA development probes with two chunk schedules, edge-window batch parity, p50/p95 latency and peak RSS. Timing only.\n' "$id" >> reports/PROJECT_STATUS.md
'@
$remote = $remote.Replace('__JOB__',$job)
& .\model_work\Invoke-VoicegaurdHpcWrite.ps1 -BashScript $remote
exit $LASTEXITCODE

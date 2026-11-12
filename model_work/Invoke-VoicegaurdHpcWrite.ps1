param(
    [Parameter(Mandatory = $true)]
    [string]$BashScript
)

# Run the scheduler preflight and mutation together under this lock.
# flock releases the lock when the command exits. Leave the lock file in place.
$remoteCommand = 'cd "$HOME/voicegaurd" && umask 077 && tr -d ''\015'' | flock -n -E 75 .automation-write.lock bash -se'
$BashScript | ssh -i "$env:USERPROFILE\.ssh\voicegaurd_codex" -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 shivam.15279@10.16.1.50 $remoteCommand
exit $LASTEXITCODE

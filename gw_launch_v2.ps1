# Launch the OMEGA-CORE v2 sweep and its watchdog completely detached from
# the calling process tree.
#
# Why this exists: two sweeps died with no forensic trail. The second one lost
# its harness shell record (/api/shell/<id>/output -> 404) and its process tree
# went with it, so the stdout pipe broke and no evidence survived. Running the
# launcher from Windows Task Scheduler puts the python processes in a different
# job object entirely, so harness teardown cannot reach them.
#
# The watchdog is started by this script (not by the agent shell) so that it
# outlives the launcher and can record the target's death time and last
# CPU/memory state.

$ErrorActionPreference = "Stop"

$py   = "C:\Python314\python.exe"
$dir  = "C:\Users\usER\oracle-toe\GUINAND_WEIL"
$log  = Join-Path $dir "omega_core_v2_run.log"
$out  = Join-Path $dir "omega_core_v2_results.json"
$hb   = Join-Path $dir "omega_core_v2_heartbeat.json"
$pidf = Join-Path $dir "omega_v2_pid.txt"
$wdl  = Join-Path $dir "omega_core_v2_watchdog.log"

Set-Location $dir

# A previous heartbeat must not masquerade as a live one.
Remove-Item $hb -ErrorAction SilentlyContinue

$sweep = Start-Process -FilePath $py `
    -ArgumentList @(
        "gw_omega_core_v2.py",
        "--c", "100",
        "--dims", "400", "800",
        "--prec", "9000",
        "--escalations", "3",
        "--log", $log,
        "--heartbeat", $hb,
        "--out", $out
    ) `
    -WorkingDirectory $dir `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $dir "omega_v2_stdout.txt") `
    -RedirectStandardError  (Join-Path $dir "omega_v2_stderr.txt") `
    -PassThru

$sweep.Id | Out-File -FilePath $pidf -Encoding ascii

Start-Sleep -Seconds 8

if (-not (Get-Process -Id $sweep.Id -ErrorAction SilentlyContinue)) {
    Write-Output "LAUNCH-FAILED: sweep pid $($sweep.Id) already gone"
    Get-Content (Join-Path $dir "omega_v2_stderr.txt") -ErrorAction SilentlyContinue
    exit 1
}

Start-Process -FilePath $py `
    -ArgumentList @(
        "gw_watchdog.py",
        "--pid", "$($sweep.Id)",
        "--heartbeat", $hb,
        "--out", $wdl,
        "--interval", "60"
    ) `
    -WorkingDirectory $dir `
    -WindowStyle Hidden

Write-Output "LAUNCHED sweep_pid=$($sweep.Id) at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
exit 0

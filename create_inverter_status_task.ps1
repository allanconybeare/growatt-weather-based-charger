# create_inverter_status_task.ps1
# Run as Administrator
#
# Creates a Windows Scheduled Task that checks the Growatt inverter status
# every 2 hours between 06:00 and 22:00.
#
# Exit code from the Python script:
#   0  = Inverter online and healthy (task succeeds)
#   1  = Inverter offline / faulted  (task records a failure you can alert on)
#   2  = Script/config error
#
# To receive an email alert when the task fails you can configure a
# Windows Task Scheduler action to send an email (or use the optional
# toast notification block inside run_inverter_status_check.bat).

$taskName = "GrowattInverterStatusCheck"
$taskDescription = "Checks every 2 hours whether the Growatt inverter is online and operating normally. Exit code 1 means inverter is offline or faulted."

$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$batchPath = Join-Path $scriptPath "run_inverter_status_check.bat"

if (-not (Test-Path $batchPath)) {
    Write-Host "Batch file not found at: $batchPath" -ForegroundColor Red
    exit 1
}

# Check for Administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script needs to be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell"
    Write-Host "2. Select 'Run as Administrator'"
    Write-Host "3. Navigate to the script directory"
    Write-Host "4. Run: .\create_inverter_status_task.ps1"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed existing task '$taskName'."
}

# Build task XML.
# Trigger: daily from 06:00, repeating every 2 hours, stopping at 22:00.
# StartWhenAvailable = true so a missed check runs as soon as the PC wakes up.
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>$taskDescription</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T06:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT2H</Interval>
        <Duration>PT16H</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERNAME</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$batchPath</Command>
      <WorkingDirectory>$scriptPath</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$tmp = Join-Path $env:TEMP "$taskName.xml"
$xml | Set-Content -Encoding Unicode $tmp

try {
    schtasks /create /tn $taskName /xml $tmp /f | Out-Null
    Remove-Item $tmp
    Write-Host ""
    Write-Host "SUCCESS: Scheduled task '$taskName' created." -ForegroundColor Green
    Write-Host ""
    Write-Host "Schedule  : Every 2 hours, 06:00 - 22:00 daily" -ForegroundColor Cyan
    Write-Host "Log file  : $scriptPath\logs\inverter_status_check.log" -ForegroundColor Cyan
    Write-Host "CSV output: $scriptPath\output\inverter_status_checks.csv" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Test a manual run:  Start-ScheduledTask -TaskName '$taskName'"
    Write-Host "2. Check task status:  Get-ScheduledTaskInfo -TaskName '$taskName'"
    Write-Host "3. Open Task Scheduler to configure email alerts on task failure: taskschd.msc"
    Write-Host ""
    Write-Host "Tip: To get a Windows toast notification when the inverter goes offline," -ForegroundColor Yellow
    Write-Host "     uncomment the notification block in run_inverter_status_check.bat" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Remove-Item $tmp -ErrorAction SilentlyContinue
    Write-Host "ERROR: Failed to create task" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

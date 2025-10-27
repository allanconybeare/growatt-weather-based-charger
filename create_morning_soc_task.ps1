# create_morning_soc_task.ps1
# Run as Administrator

# =====================================================
# Create Morning SOC Check Scheduled Task (DST Safe)
# =====================================================

# Task configuration
$taskName = "GrowattMorningSocCheck"
$taskDescription = "Checks battery SOC at 05:00 after overnight charging to measure charge efficiency"

$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$batchPath = Join-Path $scriptPath "run_morning_soc_check.bat"

if (-not (Test-Path $batchPath)) {
    Write-Host "Batch file not found at: $batchPath" -ForegroundColor Red
    exit 1
}

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script needs to be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell"
    Write-Host "2. Select 'Run as Administrator'"
    Write-Host "3. Navigate to the script directory"
    Write-Host "4. Run: .\create_morning_soc_task.ps1"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Build clean XML for the task
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>$taskDescription</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-10-27T05:00:00</StartBoundary>
      <Enabled>true</Enabled>
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
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
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
    Write-Host "SUCCESS: Scheduled task '$taskName' created." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. View in Task Scheduler: taskschd.msc"
    Write-Host "2. Test run now with: Start-ScheduledTask -TaskName '$taskName'"
    Write-Host "3. Check history: Get-ScheduledTaskInfo -TaskName '$taskName'"
    Write-Host ""
} catch {
    Write-Host "ERROR: Failed to create task" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

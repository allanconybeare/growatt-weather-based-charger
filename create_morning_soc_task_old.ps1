# =====================================================
# Create Morning SOC Check Scheduled Task (DST Safe)
# =====================================================

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

# Get the true path for the script directory
$scriptPath = (Get-Item -LiteralPath (Resolve-Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path))).FullName
$batchPath = Join-Path $scriptPath "run_morning_soc_check.bat"

# Verify batch file exists
if (-not (Test-Path $batchPath)) {
    Write-Host "ERROR: Batch file not found at: $batchPath" -ForegroundColor Red
    exit 1
}

# Task configuration
$taskName = "GrowattMorningSocCheck"
$taskDescription = "Checks battery SOC at 05:00 after overnight charging to measure charge efficiency"

Write-Host "Creating scheduled task: $taskName" -ForegroundColor Cyan
Write-Host "Batch file: $batchPath" -ForegroundColor Gray

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the task action
$action = New-ScheduledTaskAction `
    -Execute $batchPath `
    -WorkingDirectory $scriptPath

# Create daily trigger at 05:00 local time
$trigger = New-ScheduledTaskTrigger -Daily -At "05:00"

# Disable synchronization across time zones (only works in XML)
# But if you don't manually touch the XML, leave it out and the trigger stays local DST-aware

# Task settings
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Principal
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType S4U `
    -RunLevel Highest

# Register the scheduled task
try {
    # Register task
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description $taskDescription `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Force

    Write-Host ""
    Write-Host "SUCCESS: Scheduled task created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name: $taskName"
    Write-Host "  Schedule: Daily at 05:00 local (DST safe)"
    Write-Host "  Wake computer: Yes"
    Write-Host "  Run if missed: Yes"
    Write-Host "  Execution limit: 1 hour"
    Write-Host ""
    
    # Show task status
    $task = Get-ScheduledTask -TaskName $taskName
    Write-Host "Task Status: $($task.State)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. View in Task Scheduler: taskschd.msc"
    Write-Host "2. Test run now with: Start-ScheduledTask -TaskName '$taskName'"
    Write-Host "3. Check history: Get-ScheduledTaskInfo -TaskName '$taskName'"
    Write-Host ""
    
    # Optional test run
    $testRun = Read-Host "Would you like to test run the task now? (y/n)"
    if ($testRun -eq "y" -or $testRun -eq "Y") {
        Write-Host "Starting task..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 2
        Write-Host "Task started. Check the logs folder for results." -ForegroundColor Green
    }

} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

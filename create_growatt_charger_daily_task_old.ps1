# Check if running as administrator FIRST
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script needs to be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell"
    Write-Host "2. Select 'Run as Administrator'"
    Write-Host "3. Navigate to the script directory"
    Write-Host "4. Run: .\create_scheduled_task.ps1"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Get the current directory where the script is located
$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$batchPath = Join-Path $scriptPath "run_growatt_charger.bat"

# Verify batch file exists
if (-not (Test-Path $batchPath)) {
    Write-Host "ERROR: Batch file not found at: $batchPath" -ForegroundColor Red
    exit 1
}

# Task configuration
$taskName = "GrowattChargerDaily"
$taskDescription = "Runs Growatt Weather Based Charger daily at 22:00 to update charge settings based on weather forecast"

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

# Create the task trigger (daily at 22:00)
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "22:00"

# Set task settings with wake and retry options
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Get current user for task principal
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Create principal with highest privileges
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType S4U `
    -RunLevel Highest

# Register the scheduled task
try {
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
    Write-Host "  Schedule: Daily at 22:00"
    Write-Host "  Wake computer: Yes"
    Write-Host "  Run if missed: Yes"
    Write-Host "  Execution limit: 1 hour"
    Write-Host ""
    
    # Test if task can be retrieved
    $task = Get-ScheduledTask -TaskName $taskName
    Write-Host "Task Status: $($task.State)" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. View in Task Scheduler: taskschd.msc"
    Write-Host "2. Test run now with: Start-ScheduledTask -TaskName '$taskName'"
    Write-Host "3. Check history: Get-ScheduledTaskInfo -TaskName '$taskName'"
    Write-Host ""
    
    # Ask if user wants to test run now
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
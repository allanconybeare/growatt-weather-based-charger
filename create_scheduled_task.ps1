# Get the current directory where the script is located
$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$batchPath = Join-Path $scriptPath "run_growatt_charger.bat"

# Create the scheduled task
$taskName = "GrowattChargerDaily"
$taskDescription = "Runs Growatt Weather Based Charger daily at 23:00 to update charge settings based on weather forecast"

# Create the task action
$action = New-ScheduledTaskAction `
    -Execute $batchPath

# Create the task trigger (daily at 23:00)
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "23:00"

# Set task settings
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -WakeToRun

# Get current user for task principal
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Register the scheduled task
Register-ScheduledTask `
    -TaskName $taskName `
    -Description $taskDescription `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -User $currentUser `
    -RunLevel Highest

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script needs to be run as Administrator to create scheduled tasks." -ForegroundColor Red
    Write-Host "Please:"
    Write-Host "1. Right-click on PowerShell"
    Write-Host "2. Select 'Run as Administrator'"
    Write-Host "3. Navigate to the script directory"
    Write-Host "4. Run: .\create_scheduled_task.ps1"
    exit 1
}

Write-Host "Scheduled task '$taskName' has been created successfully."
Write-Host "The task will run daily at 23:00."
Write-Host "You can view and modify the task in Task Scheduler."
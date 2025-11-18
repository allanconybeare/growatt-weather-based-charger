# create_afternoon_peak_check_task.ps1
# Run as Administrator

# =====================================================
# Create Afternoon Peak-Window Check Task (Daily)
# =====================================================
# This script:
# 1. Reads check_time from config/growatt-charger.ini [peak_window] section
# 2. Creates a scheduled task to run at that time
# 3. Validates that the task time matches the config

$taskName = "GrowattAfternoonPeakCheck"
$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$configPath = Join-Path $scriptPath "conf\growatt-charger.ini"
$batchPath = Join-Path $scriptPath "run_afternoon_peak_check.bat"

# Function to read check_time from config
function Get-CheckTimeFromConfig {
    param([string]$ConfigPath)

    if (-not (Test-Path $ConfigPath)) {
        Write-Host "Error: Config file not found at: $ConfigPath" -ForegroundColor Red
        exit 1
    }

    try {
        $config = @{}
        $currentSection = $null

        Get-Content $ConfigPath | ForEach-Object {
            $line = $_.Trim()

            # Skip comments and empty lines
            if ($line.StartsWith(";") -or $line.StartsWith("#") -or $line -eq "") {
                return
            }

            # Check for section headers
            if ($line -match '^\[(.+)\]$') {
                $currentSection = $matches[1]
                $config[$currentSection] = @{}
            }
            # Parse key=value pairs
            elseif ($line -match '^(.+?)\s*=\s*(.+)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                if ($currentSection) {
                    $config[$currentSection][$key] = $value
                }
            }
        }

        if ($config.ContainsKey("peak_window") -and $config["peak_window"].ContainsKey("check_time")) {
            return $config["peak_window"]["check_time"]
        } else {
            Write-Host "Error: [peak_window] check_time not found in config" -ForegroundColor Red
            Write-Host "Please ensure conf/growatt-charger.ini has [peak_window] section with check_time setting" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "Error reading config file: $_" -ForegroundColor Red
        exit 1
    }
}

# Validate files exist
if (-not (Test-Path $batchPath)) {
    Write-Host "Error: Batch file not found at: $batchPath" -ForegroundColor Red
    exit 1
}

# Read check_time from config
Write-Host "Reading check_time from config..." -ForegroundColor Cyan
$checkTime = Get-CheckTimeFromConfig -ConfigPath $configPath
Write-Host "  ✓ Found check_time: $checkTime" -ForegroundColor Green

# Validate time format
if ($checkTime -notmatch '^\d{2}:\d{2}$') {
    Write-Host "Error: Invalid time format '$checkTime'. Expected HH:MM format" -ForegroundColor Red
    exit 1
}

# Create task description with actual check time
$taskDescription = "Runs Growatt Afternoon Peak Check daily at $checkTime to decide if battery boost is needed for peak pricing window"

# Parse time for scheduling
$timeParts = $checkTime -split ':'
$hour = [int]$timeParts[0]
$minute = [int]$timeParts[1]

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
    Write-Host "4. Run: .\create_afternoon_peak_check_task.ps1"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Format time for XML (today at specified time)
$today = Get-Date -Format "yyyy-MM-dd"
$startBoundary = "{0}T{1:D2}:{2:D2}:00" -f $today, $hour, $minute

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task: $taskName" -ForegroundColor Yellow
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
      <StartBoundary>$startBoundary</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERNAME</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>5</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$batchPath</Command>
      <WorkingDirectory>$scriptPath</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Register the task
try {
    Register-ScheduledTask -Xml $xml -TaskName $taskName -ErrorAction Stop | Out-Null
    Write-Host "✓ Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name:        $taskName"
    Write-Host "  Schedule:    Daily at $checkTime (from config)"
    Write-Host "  User:        $env:USERNAME"
    Write-Host "  Batch File:  $batchPath"
    Write-Host "  Config:      $configPath"
    Write-Host ""
    Write-Host "To verify task creation, run:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName '$taskName'"
    Write-Host ""
} catch {
    Write-Host "✗ Failed to create task: $_" -ForegroundColor Red
    exit 1
}

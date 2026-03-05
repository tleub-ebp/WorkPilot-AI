#!/usr/bin/env pwsh

<#
.SYNOPSIS
    Merge upstream changes from WorkPilot AI into your fork
    
.DESCRIPTION
    This script syncs your fork with the official WorkPilot AI upstream repository.
    It handles multiple branches and includes safety checks.
    
.PARAMETER Branch
    Branch to sync (default: 'main'). Can also use 'develop' or any other branch
    
.PARAMETER SkipPush
    Skip pushing changes after merge. Useful for reviewing changes first
    
.EXAMPLE
    .\merge-upstream.ps1
    .\merge-upstream.ps1 -Branch develop
    .\merge-upstream.ps1 -SkipPush
    .\merge-upstream.ps1 -Branch develop -SkipPush
    
.NOTES
    Requires git to be installed and configured
    Your fork must have 'upstream' remote configured
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Branch = "main",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$script:HasErrors = $false

# Colors
$Green = "`e[32m"
$Red = "`e[31m"
$Yellow = "`e[33m"
$Cyan = "`e[36m"
$Reset = "`e[0m"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $prefix = switch ($Level) {
        "SUCCESS" { "$Green✓$Reset" }
        "ERROR" { "$Red✗$Reset" }
        "WARNING" { "$Yellow⚠$Reset" }
        "INFO" { "$Cyan•$Reset" }
        default { "$Cyan•$Reset" }
    }
    
    Write-Host "$prefix $Message"
}

function Test-GitAvailable {
    try {
        $null = git --version
        return $true
    } catch {
        Write-Log "Git is not installed or not in PATH" "ERROR"
        return $false
    }
}

function Get-CurrentBranch {
    try {
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        return $branch
    } catch {
        Write-Log "Could not determine current branch" "ERROR"
        return $null
    }
}

function Test-RemoteExists {
    param([string]$Remote)
    
    try {
        $remotes = git remote -v
        return $remotes -match "^$Remote\s"
    } catch {
        return $false
    }
}

function Invoke-GitCommand {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command,
        
        [Parameter(Mandatory=$false)]
        [string]$Description
    )
    
    if ($Description) {
        Write-Log $Description
    }
    
    try {
        $output = Invoke-Expression "git $Command" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Failed: $Command" "ERROR"
            Write-Log $output "ERROR"
            $script:HasErrors = $true
            return $false
        }
        return $true
    } catch {
        Write-Log "Error executing: $Command" "ERROR"
        Write-Log $_.Exception.Message "ERROR"
        $script:HasErrors = $true
        return $false
    }
}

# Main execution
Write-Host ""
Write-Host "$Cyan════════════════════════════════════════$Reset"
Write-Host "$Cyan  WorkPilot AI Upstream Merge Tool$Reset"
Write-Host "$Cyan════════════════════════════════════════$Reset"
Write-Host ""

# Pre-flight checks
Write-Log "Performing pre-flight checks..." "INFO"
Write-Host ""

if (-not (Test-GitAvailable)) {
    exit 1
}
Write-Log "Git is available" "SUCCESS"

$currentBranch = Get-CurrentBranch
if (-not $currentBranch) {
    exit 1
}
Write-Log "Current branch: $currentBranch" "SUCCESS"

if (-not (Test-RemoteExists "upstream")) {
    Write-Log "Upstream remote not found. Configuring..." "WARNING"
    if (Invoke-GitCommand "remote add upstream https://github.com/AndyMik90/Auto-Claude.git" "Adding upstream remote") {
        Write-Log "Upstream remote configured" "SUCCESS"
    } else {
        Write-Log "Could not configure upstream remote" "ERROR"
        exit 1
    }
} else {
    Write-Log "Upstream remote exists" "SUCCESS"
}

# Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Log "⚠ Working directory has uncommitted changes:" "WARNING"
    Write-Host $status
    Write-Host ""
    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Log "Merge cancelled" "INFO"
        exit 0
    }
}

Write-Host ""

# Fetch upstream
Write-Log "Fetching latest changes from upstream..." "INFO"
if (-not (Invoke-GitCommand "fetch upstream" "")) {
    exit 1
}
Write-Log "Fetch complete" "SUCCESS"
Write-Host ""

# Switch to target branch if needed
if ($currentBranch -ne $Branch) {
    Write-Log "Switching to branch: $Branch" "INFO"
    if (-not (Invoke-GitCommand "checkout $Branch" "")) {
        Write-Log "Could not switch to branch: $Branch" "ERROR"
        exit 1
    }
    Write-Log "Switched to $Branch" "SUCCESS"
}

# Merge upstream
Write-Log "Merging upstream/$Branch into local $Branch..." "INFO"
if (-not (Invoke-GitCommand "merge upstream/$Branch" "")) {
    Write-Log "Merge failed. Resolve conflicts and try again." "ERROR"
    exit 1
}
Write-Log "Merge successful" "SUCCESS"
Write-Host ""

# Push to origin if not skipped
if (-not $SkipPush) {
    Write-Log "Pushing changes to origin/$Branch..." "INFO"
    if (-not (Invoke-GitCommand "push origin $Branch" "")) {
        Write-Log "Push failed. Check your network and permissions." "ERROR"
        exit 1
    }
    Write-Log "Push successful" "SUCCESS"
} else {
    Write-Log "Skipped pushing changes. Review your merge and push manually:" "WARNING"
    Write-Host "  git push origin $Branch"
}

Write-Host ""
Write-Host "$Green════════════════════════════════════════$Reset"
Write-Log "Upstream merge complete!" "SUCCESS"
Write-Host "$Green════════════════════════════════════════$Reset"
Write-Host ""

exit 0

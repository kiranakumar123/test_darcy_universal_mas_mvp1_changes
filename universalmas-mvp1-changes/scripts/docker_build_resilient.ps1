# Docker Build Script with Network Resilience (PowerShell)
# Handles build failures due to network connectivity issues

param(
    [string]$Dockerfile = "Dockerfile",
    [string]$Tag = "universalmas:latest",
    [switch]$Dev,
    [int]$MaxRetries = 3,
    [int]$DelaySeconds = 10
)

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    
    $color = switch ($Type) {
        "Success" { "Green" }
        "Error" { "Red" }
        "Warning" { "Yellow" }
        default { "White" }
    }
    
    Write-Host $Message -ForegroundColor $color
}

function Invoke-CommandWithRetry {
    param(
        [string[]]$Command,
        [int]$MaxRetries = 3,
        [int]$Delay = 5
    )
    
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            Write-Status "🔄 Attempt $attempt/$MaxRetries : $($Command -join ' ')"
            
            $result = & $Command[0] $Command[1..($Command.Length-1)]
            
            if ($LASTEXITCODE -eq 0) {
                Write-Status "✅ Command succeeded on attempt $attempt" "Success"
                return $true
            } else {
                throw "Command failed with exit code $LASTEXITCODE"
            }
        }
        catch {
            Write-Status "❌ Attempt $attempt failed: $($_.Exception.Message)" "Error"
            
            if ($attempt -lt $MaxRetries) {
                Write-Status "⏳ Waiting $Delay seconds before retry..." "Warning"
                Start-Sleep -Seconds $Delay
            } else {
                Write-Status "🚫 All $MaxRetries attempts failed" "Error"
                return $false
            }
        }
    }
}

function Build-DockerImage {
    param(
        [string]$DockerfilePath,
        [string]$ImageTag,
        [hashtable]$BuildArgs = @{}
    )
    
    Write-Status "🚀 Starting Docker build with network resilience..."
    
    # Build command array
    $cmd = @("docker", "build", "-f", $DockerfilePath, "-t", $ImageTag)
    
    # Add build args
    foreach ($arg in $BuildArgs.GetEnumerator()) {
        $cmd += "--build-arg"
        $cmd += "$($arg.Key)=$($arg.Value)"
    }
    
    $cmd += "."
    
    # Try build with retry logic
    if (Invoke-CommandWithRetry -Command $cmd -MaxRetries $MaxRetries -Delay $DelaySeconds) {
        Write-Status "✅ Successfully built $ImageTag" "Success"
        return $true
    }
    
    # Try alternative strategy
    Write-Status "🔄 Attempting alternative build strategy..." "Warning"
    return Build-WithAlternativeStrategy -DockerfilePath $DockerfilePath -ImageTag $ImageTag -BuildArgs $BuildArgs
}

function Build-WithAlternativeStrategy {
    param(
        [string]$DockerfilePath,
        [string]$ImageTag,
        [hashtable]$BuildArgs = @{}
    )
    
    Write-Status "🔧 Using alternative build strategy with BuildKit disabled..." "Warning"
    
    # Set environment variable to disable BuildKit
    $env:DOCKER_BUILDKIT = "0"
    
    $cmd = @("docker", "build", "--no-cache", "-f", $DockerfilePath, "-t", $ImageTag)
    
    foreach ($arg in $BuildArgs.GetEnumerator()) {
        $cmd += "--build-arg"
        $cmd += "$($arg.Key)=$($arg.Value)"
    }
    
    $cmd += "."
    
    try {
        Write-Status "🔄 Running alternative build: $($cmd -join ' ')"
        & $cmd[0] $cmd[1..($cmd.Length-1)]
        
        if ($LASTEXITCODE -eq 0) {
            Write-Status "✅ Alternative build succeeded for $ImageTag" "Success"
            return $true
        } else {
            Write-Status "❌ Alternative build also failed with exit code $LASTEXITCODE" "Error"
            return $false
        }
    }
    catch {
        Write-Status "❌ Alternative build failed: $($_.Exception.Message)" "Error"
        return $false
    }
    finally {
        # Clean up environment variable
        Remove-Item env:DOCKER_BUILDKIT -ErrorAction SilentlyContinue
    }
}

# Main execution
Write-Status "🐳 Universal MAS Framework - Docker Build Script (PowerShell)"
Write-Status ("=" * 50)

# Check if Dockerfile exists
if (-not (Test-Path $Dockerfile)) {
    Write-Status "❌ Dockerfile '$Dockerfile' not found in current directory" "Error"
    exit 1
}

# Build production image
Write-Status "📦 Building production image..."
if (-not (Build-DockerImage -DockerfilePath $Dockerfile -ImageTag $Tag)) {
    Write-Status "❌ Production build failed" "Error"
    exit 1
}

# Build development image if requested
if ($Dev -and (Test-Path "Dockerfile.dev")) {
    Write-Status "📦 Building development image..."
    if (-not (Build-DockerImage -DockerfilePath "Dockerfile.dev" -ImageTag "universalmas:dev")) {
        Write-Status "❌ Development build failed" "Error"
        exit 1
    }
}

Write-Status "🎉 All Docker builds completed successfully!" "Success"

# Show image information
try {
    Write-Status "`n📋 Built images:"
    & docker images universalmas
}
catch {
    Write-Status "⚠️ Could not list Docker images" "Warning"
}

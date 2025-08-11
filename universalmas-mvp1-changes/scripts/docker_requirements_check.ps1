#!/usr/bin/env powershell
<#
.SYNOPSIS
Docker Desktop System Requirements Checker for Windows

.DESCRIPTION
Comprehensive system check to verify Docker Desktop compatibility.
Checks all hardware and software requirements for Docker Desktop on Windows.

.NOTES
Based on official Docker Desktop requirements:
https://docs.docker.com/desktop/install/windows-install/
#>

Write-Host "🐳 Docker Desktop System Requirements Checker" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# Get system information
$computerInfo = Get-ComputerInfo
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$processorInfo = Get-CimInstance -ClassName Win32_Processor

Write-Host "`n📋 SYSTEM INFORMATION" -ForegroundColor Yellow
Write-Host "-" * 25 -ForegroundColor Yellow

# 1. Windows Version Check
Write-Host "`n🔍 Windows Version Requirements:" -ForegroundColor White
$osName = $osInfo.Caption
$osVersion = $osInfo.Version
$osBuild = $osInfo.BuildNumber

Write-Host "Current OS: $osName" -ForegroundColor Green
Write-Host "Version: $osVersion (Build $osBuild)" -ForegroundColor Green

# Check if Windows version meets requirements
$meetsWindowsReq = $false
if ($osName -match "Windows 11") {
    if ($osBuild -ge 22621) {  # 22H2 or higher
        Write-Host "✅ Windows 11 22H2+ detected - MEETS REQUIREMENT" -ForegroundColor Green
        $meetsWindowsReq = $true
    } else {
        Write-Host "❌ Windows 11 detected but build $osBuild < 22621 (22H2)" -ForegroundColor Red
        Write-Host "   Required: Windows 11 22H2 (build 22621) or higher" -ForegroundColor Red
    }
} elseif ($osName -match "Windows 10") {
    if ($osBuild -ge 19045) {  # 22H2 or higher
        Write-Host "✅ Windows 10 22H2+ detected - MEETS REQUIREMENT" -ForegroundColor Green
        $meetsWindowsReq = $true
    } else {
        Write-Host "❌ Windows 10 detected but build $osBuild < 19045 (22H2)" -ForegroundColor Red
        Write-Host "   Required: Windows 10 22H2 (build 19045) or higher" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Unsupported Windows version" -ForegroundColor Red
    Write-Host "   Required: Windows 10/11 22H2 or higher" -ForegroundColor Red
}

# 2. Memory Check
Write-Host "`n🧠 Memory Requirements:" -ForegroundColor White
$totalMemoryGB = [math]::Round($osInfo.TotalVisibleMemorySize / 1MB, 2)
Write-Host "Total Physical Memory: $totalMemoryGB GB" -ForegroundColor Green

if ($totalMemoryGB -ge 4) {
    Write-Host "✅ Memory requirement met (≥4GB)" -ForegroundColor Green
    $meetsMemoryReq = $true
} else {
    Write-Host "❌ Insufficient memory: $totalMemoryGB GB < 4GB required" -ForegroundColor Red
    $meetsMemoryReq = $false
}

# 3. Processor Architecture Check
Write-Host "`n💾 Processor Requirements:" -ForegroundColor White
$architecture = $processorInfo.Architecture
$is64Bit = $osInfo.OSArchitecture -eq "64-bit"

Write-Host "Processor: $($processorInfo.Name)" -ForegroundColor Green
Write-Host "Architecture: $($osInfo.OSArchitecture)" -ForegroundColor Green

if ($is64Bit) {
    Write-Host "✅ 64-bit processor detected - MEETS REQUIREMENT" -ForegroundColor Green
    $meetsArchReq = $true
} else {
    Write-Host "❌ 32-bit processor detected - Docker requires 64-bit" -ForegroundColor Red
    $meetsArchReq = $false
}

# 4. SLAT (Second Level Address Translation) Check
Write-Host "`n🔧 Hardware Virtualization (SLAT) Check:" -ForegroundColor White
try {
    # Check if Hyper-V is available (indicates SLAT support)
    $hyperV = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction SilentlyContinue
    $hyperVPlatform = Get-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -ErrorAction SilentlyContinue
    
    if ($hyperV -or $hyperVPlatform) {
        Write-Host "✅ Hardware virtualization (SLAT) appears to be supported" -ForegroundColor Green
        $meetsSLATReq = $true
    } else {
        Write-Host "⚠️ Cannot verify SLAT support - check BIOS settings" -ForegroundColor Yellow
        $meetsSLATReq = $null
    }
} catch {
    Write-Host "⚠️ Cannot check SLAT support automatically" -ForegroundColor Yellow
    $meetsSLATReq = $null
}

# 5. WSL 2 Check
Write-Host "`n🐧 WSL 2 Requirements:" -ForegroundColor White
try {
    $wslVersion = wsl --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "WSL Version Output:" -ForegroundColor Green
        Write-Host $wslVersion -ForegroundColor Green
        
        # Check for WSL 2.1.5+
        if ($wslVersion -match "WSL version: (\d+\.\d+\.\d+)") {
            $version = [version]$matches[1]
            $requiredVersion = [version]"2.1.5"
            
            if ($version -ge $requiredVersion) {
                Write-Host "✅ WSL version $version meets requirement (≥2.1.5)" -ForegroundColor Green
                $meetsWSLReq = $true
            } else {
                Write-Host "❌ WSL version $version < 2.1.5 required" -ForegroundColor Red
                $meetsWSLReq = $false
            }
        } else {
            Write-Host "⚠️ Could not parse WSL version" -ForegroundColor Yellow
            $meetsWSLReq = $null
        }
    } else {
        Write-Host "❌ WSL not installed or not working" -ForegroundColor Red
        $meetsWSLReq = $false
    }
} catch {
    Write-Host "❌ WSL check failed" -ForegroundColor Red
    $meetsWSLReq = $false
}

# 6. Virtualization in BIOS Check
Write-Host "`n⚙️ Virtualization Settings:" -ForegroundColor White
try {
    # Check if virtualization is enabled
    $vmx = Get-CimInstance -ClassName Win32_Processor | Select-Object -ExpandProperty VirtualizationFirmwareEnabled
    if ($vmx -contains $true) {
        Write-Host "✅ Hardware virtualization enabled in BIOS" -ForegroundColor Green
        $meetsVirtReq = $true
    } else {
        Write-Host "❌ Hardware virtualization disabled in BIOS" -ForegroundColor Red
        Write-Host "   Enable VT-x/AMD-V in BIOS settings" -ForegroundColor Red
        $meetsVirtReq = $false
    }
} catch {
    Write-Host "⚠️ Cannot check virtualization settings automatically" -ForegroundColor Yellow
    $meetsVirtReq = $null
}

# Summary
Write-Host "`n📊 REQUIREMENTS SUMMARY" -ForegroundColor Yellow
Write-Host "-" * 25 -ForegroundColor Yellow

$requirements = @(
    @{Name="Windows Version"; Status=$meetsWindowsReq; Required="Windows 10/11 22H2+"},
    @{Name="Memory"; Status=$meetsMemoryReq; Required="4GB RAM"},
    @{Name="Architecture"; Status=$meetsArchReq; Required="64-bit processor"},
    @{Name="SLAT Support"; Status=$meetsSLATReq; Required="Hardware virtualization"},
    @{Name="WSL 2"; Status=$meetsWSLReq; Required="WSL 2.1.5+"},
    @{Name="BIOS Virtualization"; Status=$meetsVirtReq; Required="VT-x/AMD-V enabled"}
)

$allMet = $true
foreach ($req in $requirements) {
    $status = switch ($req.Status) {
        $true { "✅ PASS"; $color = "Green" }
        $false { "❌ FAIL"; $allMet = $false; $color = "Red" }
        $null { "⚠️ UNKNOWN"; $color = "Yellow" }
    }
    Write-Host "$($req.Name): $status ($($req.Required))" -ForegroundColor $color
}

Write-Host "`n🎯 FINAL VERDICT" -ForegroundColor Yellow
Write-Host "-" * 15 -ForegroundColor Yellow

if ($allMet -and ($requirements | Where-Object {$_.Status -eq $null}).Count -eq 0) {
    Write-Host "🎉 YOUR SYSTEM MEETS ALL DOCKER DESKTOP REQUIREMENTS!" -ForegroundColor Green
    Write-Host "You can proceed with Docker Desktop installation." -ForegroundColor Green
} elseif ($allMet) {
    Write-Host "⚠️ System likely compatible but some checks inconclusive." -ForegroundColor Yellow
    Write-Host "Try installing Docker Desktop - it should work." -ForegroundColor Yellow
} else {
    Write-Host "❌ SYSTEM DOES NOT MEET DOCKER DESKTOP REQUIREMENTS" -ForegroundColor Red
    Write-Host "`nTo fix these issues:" -ForegroundColor Yellow
    
    if (-not $meetsWindowsReq) {
        Write-Host "• Update Windows to 22H2 or later" -ForegroundColor Yellow
    }
    if (-not $meetsMemoryReq) {
        Write-Host "• Add more RAM (minimum 4GB required)" -ForegroundColor Yellow
    }
    if (-not $meetsArchReq) {
        Write-Host "• Upgrade to 64-bit hardware" -ForegroundColor Yellow
    }
    if ($meetsWSLReq -eq $false) {
        Write-Host "• Install/update WSL 2: Run 'wsl --install' as administrator" -ForegroundColor Yellow
    }
    if ($meetsVirtReq -eq $false) {
        Write-Host "• Enable virtualization in BIOS/UEFI settings" -ForegroundColor Yellow
    }
}

Write-Host "`n💡 ALTERNATIVE SOLUTIONS" -ForegroundColor Cyan
Write-Host "-" * 25 -ForegroundColor Cyan

if (-not $allMet) {
    Write-Host "If your system doesn't meet requirements, you can still:" -ForegroundColor White
    Write-Host "• Use our Docker-free LangGraph development server" -ForegroundColor Green
    Write-Host "• Generate static workflow visualizations" -ForegroundColor Green
    Write-Host "• Use VS Code Mermaid Preview for diagrams" -ForegroundColor Green
    Write-Host "• Run workflows without Docker visualization" -ForegroundColor Green
} else {
    Write-Host "Your system is ready for Docker Desktop!" -ForegroundColor Green
    Write-Host "• Full LangGraph Studio with interactive UI" -ForegroundColor Green
    Write-Host "• Complete workflow debugging and visualization" -ForegroundColor Green
    Write-Host "• Container-based development environment" -ForegroundColor Green
}

Write-Host "`nNext steps in our conversation..." -ForegroundColor Cyan

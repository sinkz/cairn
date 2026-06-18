param(
    [string]$Version = $env:CAIRN_VERSION,
    [string]$InstallDir = $env:CAIRN_INSTALL_DIR,
    [string]$Repo = $env:CAIRN_REPO
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = "sinkz/cairn"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = "latest"
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\Cairn\bin"
}

if ($env:PROCESSOR_ARCHITECTURE -notin @("AMD64", "x86_64")) {
    throw "Unsupported Windows architecture: $env:PROCESSOR_ARCHITECTURE. Cairn currently publishes a Windows x64 binary."
}

$Asset = "cairn-windows-x64.zip"

if ($Version -eq "latest") {
    $BaseUrl = "https://github.com/$Repo/releases/latest/download"
} else {
    if ($Version.StartsWith("v")) {
        $Tag = $Version
    } else {
        $Tag = "v$Version"
    }
    $BaseUrl = "https://github.com/$Repo/releases/download/$Tag"
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cairn-install-" + [System.Guid]::NewGuid().ToString("N"))
$Archive = Join-Path $TempDir $Asset
$Checksums = Join-Path $TempDir "checksums.txt"

try {
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

    Write-Host "Downloading $Asset from $BaseUrl"
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/$Asset" -OutFile $Archive
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/checksums.txt" -OutFile $Checksums

    $ExpectedLine = Get-Content $Checksums | Where-Object { $_ -match "\s+$([regex]::Escape($Asset))$" } | Select-Object -First 1
    if (-not $ExpectedLine) {
        throw "Checksum for $Asset was not found in checksums.txt."
    }

    $ExpectedHash = ($ExpectedLine -split "\s+")[0].ToLowerInvariant()
    $ActualHash = (Get-FileHash -Algorithm SHA256 -Path $Archive).Hash.ToLowerInvariant()
    if ($ExpectedHash -ne $ActualHash) {
        throw "Checksum mismatch for $Asset. Expected $ExpectedHash but got $ActualHash."
    }

    Expand-Archive -Force -Path $Archive -DestinationPath $TempDir
    $Binary = Get-ChildItem -Path $TempDir -Filter "cairn.exe" -Recurse | Select-Object -First 1
    if (-not $Binary) {
        throw "Release archive did not contain cairn.exe."
    }

    $Target = Join-Path $InstallDir "cairn.exe"
    Copy-Item -Force -Path $Binary.FullName -Destination $Target

    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $PathParts = @()
    if (-not [string]::IsNullOrWhiteSpace($UserPath)) {
        $PathParts = $UserPath -split [IO.Path]::PathSeparator
    }

    if ($PathParts -notcontains $InstallDir) {
        $NewUserPath = if ([string]::IsNullOrWhiteSpace($UserPath)) {
            $InstallDir
        } else {
            "$UserPath$([IO.Path]::PathSeparator)$InstallDir"
        }
        [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
        Write-Host "Added $InstallDir to the user PATH. Restart your terminal if 'cairn' is not found."
    }

    if (($env:Path -split [IO.Path]::PathSeparator) -notcontains $InstallDir) {
        $env:Path = "$InstallDir$([IO.Path]::PathSeparator)$env:Path"
    }

    & $Target --version
    Write-Host "Installed Cairn at $Target"
} finally {
    Remove-Item -Recurse -Force -Path $TempDir -ErrorAction SilentlyContinue
}

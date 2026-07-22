param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{64}$')]
    [string]$ExpectedManifestSha256
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifestPath = Join-Path $root 'Q_MANIFEST.json'
$actualManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
if ($actualManifestHash -ne $ExpectedManifestSha256) {
    throw "Manifest hash mismatch: expected $ExpectedManifestSha256, got $actualManifestHash"
}

$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$allowed = @('FRAMING_INPUT.json', 'Q_MANIFEST.json', 'TASK_PROMPT.md', 'VERIFY_MANIFEST.ps1', 'report')
$actual = @(Get-ChildItem -Force -LiteralPath $root | Sort-Object Name | ForEach-Object Name)
if ((Compare-Object ($allowed | Sort-Object) $actual).Count -ne 0) {
    throw "Unexpected root inventory: $($actual -join ', ')"
}
if (@(Get-ChildItem -Force -LiteralPath (Join-Path $root 'report')).Count -ne 0) {
    throw 'report directory is not empty before the cold read'
}

foreach ($entry in $manifest.files) {
    $path = Join-Path $root $entry.name
    $item = Get-Item -LiteralPath $path
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    if ($item.Length -ne $entry.bytes -or $hash -ne $entry.sha256) {
        throw "File mismatch: $($entry.name)"
    }
}

Write-Output "Q_MANIFEST_OK $actualManifestHash"

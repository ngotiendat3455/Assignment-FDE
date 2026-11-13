$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ResultsDir = Join-Path $RepoRoot "tests\manual\results"
$TracesDir = Join-Path $ResultsDir "traces"
$LogFile = Join-Path $ResultsDir "latest-run.log"
$SummaryFile = Join-Path $ResultsDir "summary.md"
$ContractsXml = Join-Path $ResultsDir "contracts-junit.xml"

New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null
if (Test-Path $TracesDir) {
    Remove-Item -Recurse -Force $TracesDir
}
New-Item -ItemType Directory -Force -Path $TracesDir | Out-Null
"" | Set-Content -Path $LogFile -Encoding UTF8

function Write-GateLog {
    param([string]$Message)
    Write-Host $Message
    Add-Content -Path $LogFile -Value $Message -Encoding UTF8
}

$Timestamp = (Get-Date).ToString("o")
Write-GateLog "=== Feature 08 Quality Gate: Tier 1 Contracts + Tier 2 Playwright E2E ==="
Write-GateLog "Started at: $Timestamp"

function Invoke-NativeStep {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    Write-GateLog ""
    Write-GateLog $Label
    $prevPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $Command 2>&1
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prevPref
    }
    foreach ($line in $output) {
        Write-GateLog "$line"
    }
    if ($code -ne 0) {
        Write-GateLog "[FAIL-FAST] $Label failed with exit code $code."
        exit $code
    }
}

Push-Location $RepoRoot
try {
    Invoke-NativeStep "[Tier 1] Running Backend Contract Tests (pytest)..." {
        python -m pytest backend/tests/contracts/ -v -s "--junitxml=$ContractsXml"
    }

    Set-Location (Join-Path $RepoRoot "frontend")
    Invoke-NativeStep "[Tier 2] Running Playwright E2E Suite (PW-01..PW-09)..." {
        npx.cmd playwright test
    }

    $FinishedAt = (Get-Date).ToString("o")
    Write-GateLog ""
    Write-GateLog "[PASS] Quality Gate completed at $FinishedAt"
    Write-GateLog "Flow Contract Report: $(Join-Path $TracesDir '_FLOW_COVERAGE_REPORT.md')"

    @"
# Feature 08 Quality Gate Summary

- **Status:** PASS
- **Started:** $Timestamp
- **Finished:** $FinishedAt
- **Tier 1 (Contracts):** PASS (``tests/manual/results/contracts-junit.xml``)
- **Tier 2 (Playwright E2E):** PASS (``tests/manual/results/playwright-results.json``, ``frontend/playwright-report/index.html``)
- **Flow Contract Report:** ``tests/manual/results/traces/_FLOW_COVERAGE_REPORT.md`` & ``tests/manual/results/traces/*.md``
"@ | Set-Content -Path $SummaryFile -Encoding UTF8
}
finally {
    Pop-Location
}


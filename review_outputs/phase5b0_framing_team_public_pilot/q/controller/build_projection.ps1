param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Output
)

$transaction = Get-Content -Raw -Encoding UTF8 -LiteralPath $Source | ConvertFrom-Json
$questions = @(
    $transaction.operations |
        Where-Object { $_.op -eq 'entity.create' -and $_.entity.entity_type -eq 'ResearchQuestion' }
)
$benchmarks = @(
    $transaction.operations |
        Where-Object { $_.op -eq 'entity.create' -and $_.entity.entity_type -eq 'BenchmarkSet' }
)

if ($questions.Count -ne 1) {
    throw "Expected exactly one ResearchQuestion; found $($questions.Count)"
}
if ($benchmarks.Count -ne 1) {
    throw "Expected exactly one BenchmarkSet; found $($benchmarks.Count)"
}

$question = $questions[0].entity
$benchmark = $benchmarks[0].entity
$projection = [ordered]@{
    projection_schema = 'economic-theory-frame/cold-read/v1'
    research_question = [ordered]@{
        title = $question.title
        summary = $question.summary
        economic_interpretation = $question.facets.economic_interpretation.payload
    }
    benchmark_set = [ordered]@{
        title = $benchmark.title
        summary = $benchmark.summary
        economic_interpretation = $benchmark.facets.economic_interpretation.payload
    }
}

$json = $projection | ConvertTo-Json -Depth 100
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Output, $json + [Environment]::NewLine, $utf8NoBom)

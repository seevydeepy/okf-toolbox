param([string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path)
$data = Get-Content -Raw (Join-Path $Root 'evals\skill-triggers.json') | ConvertFrom-Json
$fields = 'id','skill','prompt','expected_invocation','expected_phase','authority_required','notes'
$phases = 'none','read-only','planning','implementation','external-write-preview'
$authority = 'none','implementation','explicit-external-write-approval','saved-plan-approval'
if ($data.schema_version -ne 1) { throw 'schema_version must be 1' }
foreach ($case in $data.cases) {
  if ((Compare-Object $fields @($case.PSObject.Properties.Name)) -or $case.expected_invocation -isnot [bool] -or $case.expected_phase -notin $phases -or $case.authority_required -notin $authority -or -not (Test-Path (Join-Path $Root "skills\$($case.skill)\SKILL.md"))) { throw "Invalid trigger case: $($case.id)" }
}
Write-Host '[PASS] skill trigger corpus'

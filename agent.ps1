param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$scriptPath = Join-Path $PSScriptRoot "scripts\agent_hub.py"
& python $scriptPath @ArgsList

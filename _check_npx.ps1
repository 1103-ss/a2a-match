# Check where clawhub is and if it has a skip-sync option
$clawhub = (Get-Command npx -ErrorAction SilentlyContinue).Source
Write-Host "npx at: $clawhub"

# Try: run node directly with clawhub
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
Write-Host "node at: $node"

# Read the clawhub publish script
$npmRoot = npm root -ErrorAction SilentlyContinue
Write-Host "npm root: $npmRoot"

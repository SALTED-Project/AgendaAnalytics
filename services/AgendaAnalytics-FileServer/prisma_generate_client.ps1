# Go to the script's directory
$path = $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Path "$path" -Parent)

$Env:PRISMA_PY_DEBUG=1
$Env:DEBUG='*'

# Generate the schema in the project's Python virtual environment (venv) using Poetry
Set-Location app
poetry run python -m prisma generate --schema .\schemas\schema.prisma

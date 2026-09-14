$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'First XeLaTeX pass failed.' }
    xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Second XeLaTeX pass failed.' }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'main.pdf') -Destination (Join-Path $PSScriptRoot 'A题_药材烘干_数模论文.pdf') -Force
} finally {
    Pop-Location
}

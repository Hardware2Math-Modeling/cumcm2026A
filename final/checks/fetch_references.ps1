$ErrorActionPreference = 'Stop'
$queries = @(
 'Fritsch Carlson Monotone Piecewise Cubic Interpolation',
 'Shampine Reichelt The MATLAB ODE Suite',
 'Martins Sturdza Alonso The complex-step derivative approximation',
 'Virtanen SciPy 1.0 fundamental algorithms scientific computing',
 'Crank The Mathematics of Diffusion 1975',
 'Carslaw Jaeger Conduction of Heat in Solids 1959',
 'Patankar Numerical Heat Transfer and Fluid Flow 1980',
 'Mujumdar Handbook of Industrial Drying fourth edition 2014',
 'Mayor Sereno Modelling shrinkage during convective drying of food materials review 2004',
 'Defraeye Advanced computational modelling for drying processes review 2014',
 'Huang Russell Adaptive Moving Mesh Methods 2011',
 'Whitaker simultaneous heat mass transfer porous media theory drying 1977'
)
$out = @()
foreach ($q in $queries) {
 try {
  $url='https://api.crossref.org/works?rows=2&query.bibliographic='+[uri]::EscapeDataString($q)
  $r=Invoke-RestMethod -Uri $url -TimeoutSec 25
  $items=@($r.message.items | ForEach-Object { @{
   title=$_.title; author=$_.author; published=$_.published; container=$_.'container-title'
   volume=$_.volume; issue=$_.issue; page=$_.page; DOI=$_.DOI; publisher=$_.publisher
  } })
  $out+=@{query=$q;items=$items}
  Write-Output ($q + ' => ' + $items[0].title + ' | ' + $items[0].DOI)
 } catch { $out+=@{query=$q;error=$_.Exception.Message}; Write-Output $_.Exception.Message }
}
$out | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot 'references_verified.json')

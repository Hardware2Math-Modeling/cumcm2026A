$ErrorActionPreference='Stop'
$dois=@('10.1038/s41592-019-0686-2','10.1145/838250.838251','10.1137/0717021','10.1137/S1064827594276424','10.1201/b17208','10.1201/9781482234213','10.1016/S0260-8774(03)00144-4','10.1016/j.apenergy.2014.06.027','10.1007/978-1-4419-7916-2','10.1016/S0065-2717(08)70223-5')
$out=@()
foreach($doi in $dois){
 try{
  $m=(Invoke-RestMethod -Uri ('https://api.crossref.org/works/'+$doi) -TimeoutSec 25).message
  $item=@{title=$m.title;author=$m.author;published=$m.published;container=$m.'container-title';volume=$m.volume;issue=$m.issue;page=$m.page;DOI=$m.DOI;publisher=$m.publisher}
  $out+=$item
  Write-Output ($item.title + ' | '+$item.volume+' | '+$item.page+' | '+$item.DOI)
 }catch{Write-Output $_.Exception.Message}
}
$out|ConvertTo-Json -Depth 12|Set-Content -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot 'doi_metadata.json')

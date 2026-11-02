param([string]$in, [string]$out)
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($in, $true, $false, $false)
$pres.SaveAs($out, 32)
$pres.Close()
$app.Quit()

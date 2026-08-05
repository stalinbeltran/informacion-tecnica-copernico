# Convierte un .doc heredado (OLE2) a .docx usando Word, para poder extraerlo
# con el mismo flujo que el resto. Uso:  powershell -File tools\convert_doc.ps1 "archivo.doc"
param([Parameter(Mandatory=$true)][string]$Path)

$src = (Resolve-Path $Path).Path
$dst = [IO.Path]::ChangeExtension($src, ".docx")

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($src, $false, $true)   # ReadOnly
    $doc.SaveAs2($dst, 16)                             # 16 = wdFormatDocumentDefault (.docx)
    $doc.Close($false)
    Write-Output "convertido: $dst"
} finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}

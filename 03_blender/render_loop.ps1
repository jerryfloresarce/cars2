# Bucle DESATENDIDO de render: relanza render_frames.py (reanudable) hasta que no
# quede ningun fotograma pendiente de su bloque. Se lanza desacoplado con
# Start-Process para que no lo mate el limite de tiempo de las herramientas.
#   powershell -File render_loop.ps1 -ChunkId 0 -ChunkOf 3
param([int]$ChunkId = 0, [int]$ChunkOf = 1)
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$base = "E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender"
$logs = Join-Path $base "renders\logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$env:CHUNK_ID = "$ChunkId"
$env:CHUNK_OF = "$ChunkOf"
$env:PRESUPUESTO_S = "3000"
$log = Join-Path $logs ("render_{0}.log" -f $ChunkId)
for ($vuelta = 0; $vuelta -lt 60; $vuelta++) {
    $salida = & $blender --background --factory-startup --python (Join-Path $base "render_frames.py") 2>$null | Select-String -Pattern "RESUMEN|TODOS_LOS_FRAMES_LISTOS|Traceback|Error:"
    Add-Content -Path $log -Value ("[{0}] vuelta {1}: {2}" -f (Get-Date -Format "HH:mm:ss"), $vuelta, ($salida -join " | "))
    if ($salida -match "TODOS_LOS_FRAMES_LISTOS") { break }
    if ($salida -match "pendientes=0") { break }
}
Add-Content -Path $log -Value ("[{0}] FIN bloque {1}" -f (Get-Date -Format "HH:mm:ss"), $ChunkId)

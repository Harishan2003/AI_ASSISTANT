
$ErrorActionPreference = 'SilentlyContinue'
$vc = Get-CimInstance Win32_VideoController | Select-Object Name, VideoProcessor, DriverVersion, AdapterRAM, Status, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, VideoModeDescription, InstalledDisplayDrivers, PNPDeviceID | ConvertTo-Json
Write-Output "=== CONTROLLERS ==="
Write-Output $vc

# Query GPU Engine counters
$gpuEngines = Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction SilentlyContinue
if ($gpuEngines) {
    Write-Output "=== GPU ENGINES SAMPLES ==="
    $active = $gpuEngines.CounterSamples | Where-Object { $_.CookedValue -gt 0 }
    $active | Select-Object -Property InstanceName, CookedValue | ConvertTo-Json
}

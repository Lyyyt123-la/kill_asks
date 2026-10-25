Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);' -Name Win -Namespace Native
$p = Get-Process chrome | Where-Object { $_.MainWindowTitle -eq 'AskData Demo - Google Chrome' } | Select-Object -First 1
if ($p) {
  [Native.Win]::SetWindowPos($p.MainWindowHandle, [IntPtr]::new(-1), 0, 0, 1600, 1000, 0x0040) | Out-Null
  'topmost ok'
} else {
  'no window'
}

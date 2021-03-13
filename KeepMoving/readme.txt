1. Open "Windows PowerShell" application
2. Copy and paste below line
	Add-Type -AssemblyName System.Windows.Forms; [int] $mins = Read-Host -Prompt 'Input the minutes you want to keep moving'; For ($i=$mins; $i -gt 0; $i--) { Write-Host "$i minutes left"; Start-Sleep -Seconds 60; [System.Windows.Forms.SendKeys]::SendWait('{RIGHT}'); }
3. Prese enter to run
4. The script will send A RIGHT ARROW key per minute, and it can be stopped by closing "Windows PowerShell" application anytime.

See example at https://github.com/wkdadao/tools/blob/master/KeepMoving/example.png

@echo off
set ROOT=C:\Users\fyyou\Desktop\projectFile\Apix-Version_2.1

start "Agent"  powershell -NoExit -Command "$env:PYTHONIOENCODING='utf-8'; cd '%ROOT%\AGENT\agent_module'; Write-Host '=== Agent Starting... ==='; .venv\Scripts\python.exe main.py"
start "Memory" powershell -NoExit -Command "$env:PYTHONIOENCODING='utf-8'; cd '%ROOT%\MEMORY\memory_module'; Write-Host '=== Memory Starting... ==='; .venv\Scripts\python.exe main.py"
start "File"   powershell -NoExit -Command "$env:PYTHONIOENCODING='utf-8'; cd '%ROOT%\FILE\file_service'; Write-Host '=== File Starting... ==='; .venv\Scripts\python.exe main.py"
start "Task"   powershell -NoExit -Command "$env:PYTHONIOENCODING='utf-8'; cd '%ROOT%\TASK\task_flow_module'; Write-Host '=== Task Starting... ==='; .venv\Scripts\python.exe main.py"

echo All 4 services started!
pause

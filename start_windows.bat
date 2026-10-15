@echo off
setlocal
cd /d "%~dp0"
if "%OPENAI_API_KEY%"=="" (
  echo.
  echo Optional: enter your OpenAI API key to enable AI chat.
  echo Leave blank to use the built-in local style matcher.
  set /p OPENAI_API_KEY=OpenAI API key: 
)
python app_server.py
if errorlevel 1 (
  echo.
  echo Could not start. Please install Python 3 and ensure 'python' works in Command Prompt.
  pause
)

@echo off
setlocal
cd /d "%~dp0"
echo Installing build tools...
python -m pip install -r requirements.txt pyinstaller || goto :error
echo Building SecureBank AI for Windows...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SecureBankAI ^
  --icon "icon.ico" --add-data "icon.ico;." --add-data "icon.png;." ^
  --add-data "login_security_bg_presentation.jpg;." ^
  --collect-submodules sklearn --hidden-import matplotlib.backends.backend_qtagg ^
  --exclude-module tkinter main.py || goto :error
echo.
copy /Y "securebank.db" "dist\securebank.db" >nul || goto :error
copy /Y ".env.example" "dist\.env.example" >nul || goto :error
echo SUCCESS: dist\SecureBankAI.exe
echo On first launch, the application copies the packaged database into %%LOCALAPPDATA%%\SecureBankAI.
echo Private environment settings are loaded from %%LOCALAPPDATA%%\SecureBankAI\.env.
echo Keep the database private. Never distribute a real .env file.
pause
exit /b 0
:error
echo BUILD FAILED - review the error messages above.
pause
exit /b 1

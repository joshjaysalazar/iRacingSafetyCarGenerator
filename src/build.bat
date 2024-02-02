@ECHO OFF
:: This batch file builds a Windows binary executable
ECHO Building binary. Please wait...
:: Build new binary
pyinstaller --noconfirm --log-level=FATAL --noconsole --onefile main.py

ECHO Copying files to dist...
:: Copy settings.ini to dist
COPY settings.ini dist\settings.ini
:: Copy README.md to dist
COPY ..\README.md dist\README.md
:: Copy LICENSE to dist
COPY ..\LICENSE dist\LICENSE
@ECHO OFF
:: This batch file builds a Windows binary executable
ECHO Building binary. Please wait...
:: Import pywinauto before building to avoid missing library error
python -c "import pywinauto"
:: Build new binary
pyinstaller --noconfirm --log-level=FATAL --noconsole --onefile --hidden-import=comtypes.gen.UIAutomationClient --hidden-import=pywinauto.application --name=iRSCG main.py

ECHO Copying files to dist...
:: Copy all assets to dist  
ROBOCOPY assets dist\assets /E 
:: Copy settings.ini to dist
COPY settings.ini dist\settings.ini
:: Copy logging.json to dist
COPY logging.json dist\logging.json
:: Copy README.md to dist
COPY ..\README.md dist\README.md
:: Copy LICENSE to dist
COPY ..\LICENSE dist\LICENSE
:: Copy tooltips.json to dist
COPY tooltips_text.json dist\tooltips_text.json
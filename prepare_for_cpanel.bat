@echo off
echo Preparing LedgerBook for cPanel deployment...

REM Create a temporary directory
set TEMP_DIR=ledgerbook_cpanel_deploy
if exist %TEMP_DIR% rmdir /s /q %TEMP_DIR%
mkdir %TEMP_DIR%

echo Copying application files...
copy app.py %TEMP_DIR%\
copy models.py %TEMP_DIR%\
copy requirements.txt %TEMP_DIR%\
xcopy /E /I /Y templates %TEMP_DIR%\templates
xcopy /E /I /Y static %TEMP_DIR%\static
copy passenger_wsgi.py %TEMP_DIR%\
copy .htaccess %TEMP_DIR%\
copy setup_cpanel.sh %TEMP_DIR%\
copy check_app.py %TEMP_DIR%\
copy DEPLOY_TO_CPANEL.md %TEMP_DIR%\

echo Creating instance directory...
mkdir %TEMP_DIR%\instance

echo Creating README for deployment...
(
echo # LedgerBook cPanel Deployment
echo.
echo This package contains all files needed to deploy LedgerBook to cPanel.
echo.
echo ## Quick Start
echo.
echo 1. Upload all files to your chosen directory on your cPanel account
echo 2. Run setup_cpanel.sh to set up the environment
echo 3. Update the .htaccess file with your actual path
echo 4. Configure the Python application in cPanel
echo 5. Visit your site to start using LedgerBook
echo.
echo For detailed instructions, see DEPLOY_TO_CPANEL.md
echo.
echo ## Testing
echo.
echo Run `python check_app.py` to verify the setup is working correctly.
) > %TEMP_DIR%\README.md

echo Creating deployment zip file...
powershell Compress-Archive -Path %TEMP_DIR%\* -DestinationPath ledgerbook_cpanel_deploy.zip -Force

echo Cleaning up...
rmdir /s /q %TEMP_DIR%

echo Deployment package created: ledgerbook_cpanel_deploy.zip
echo Upload this file to your cPanel account and follow the instructions in DEPLOY_TO_CPANEL.md

echo Press any key to exit...
pause > nul 
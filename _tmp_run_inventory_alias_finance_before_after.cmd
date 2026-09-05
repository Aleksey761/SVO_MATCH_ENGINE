@echo off
cd /d f:\SVO\AI\SVO_MATCH_ENGINE

set "PY=f:\SVO\AI\SVO_MATCH_ENGINE\.venv\Scripts\python.exe"
set "FIN_LOG=output\FINANCE_RUN_LOG.txt"
set "FIN_ERR=output\FINANCE_RUN_ERR.txt"
set "FIN_STATUS=output\FINANCE_RUN_STATUS.txt"
set "CMP_LOG=output\INVENTORY_ALIAS_FINANCE_BEFORE_AFTER.log"
set "CMP_ERR=output\INVENTORY_ALIAS_FINANCE_BEFORE_AFTER.err.txt"
set "CMP_STATUS=output\INVENTORY_ALIAS_FINANCE_BEFORE_AFTER.status.txt"

del "%FIN_LOG%" "%FIN_ERR%" "%FIN_STATUS%" "%CMP_LOG%" "%CMP_ERR%" "%CMP_STATUS%" 2>nul

"%PY%" runner.py --mode finance --master data/MASTER.xlsx --price output/price_match.xlsx --sales output/SALES_MATCH_06.04.2026.xlsx --inventory "data/06.04.26 инвентаризация(полн).xlsx" --output output/FINANCE_RESULT.xlsx 1>"%FIN_LOG%" 2>"%FIN_ERR%"
echo EXIT=%ERRORLEVEL%>"%FIN_STATUS%"
if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%

"%PY%" _tmp_build_inventory_alias_finance_before_after.py 1>"%CMP_LOG%" 2>"%CMP_ERR%"
echo EXIT=%ERRORLEVEL%>"%CMP_STATUS%"
exit /b %ERRORLEVEL%
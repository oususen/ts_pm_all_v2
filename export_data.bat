@echo off
chcp 65001 >nul
echo =====================================
echo MySQLデータエクスポートツール
echo =====================================
echo.

REM 日付を取得（YYYYMMDD形式）
set dt=%date:~0,4%%date:~5,2%%date:~8,2%

echo データをエクスポートしています...
echo ファイル名: mysql_backup_%dt%.sql
echo.

docker exec ts_pm_mysql mysqldump -u root -p --all-databases > mysql_backup_%dt%.sql

if %errorlevel% equ 0 (
    echo.
    echo =====================================
    echo エクスポート完了！
    echo =====================================
    echo.
    echo 出力ファイル: mysql_backup_%dt%.sql
    echo このファイルを他のPCにコピーしてください
    echo.
) else (
    echo.
    echo エラー: エクスポートに失敗しました
    echo - Dockerが起動しているか確認してください
    echo - MySQLコンテナが起動しているか確認してください
    echo.
)

pause

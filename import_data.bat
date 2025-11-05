@echo off
chcp 65001 >nul
echo =====================================
echo MySQLデータインポートツール
echo =====================================
echo.

REM ダンプファイルを検索
echo 利用可能なダンプファイル:
echo.
dir /b mysql_backup*.sql 2>nul
if %errorlevel% neq 0 (
    echo エラー: ダンプファイルが見つかりません
    echo mysql_backup*.sql ファイルをこのディレクトリに配置してください
    echo.
    pause
    exit /b 1
)
echo.

set /p filename="インポートするファイル名を入力してください: "

if not exist "%filename%" (
    echo.
    echo エラー: ファイル '%filename%' が見つかりません
    echo.
    pause
    exit /b 1
)

echo.
echo ファイル '%filename%' をインポートしています...
echo パスワードを入力してください（.env の PRIMARY_DB_PASSWORD）
echo.

docker exec -i ts_pm_mysql mysql -u root -p < "%filename%"

if %errorlevel% equ 0 (
    echo.
    echo =====================================
    echo インポート完了！
    echo =====================================
    echo.
    echo データベースが正常にインポートされました
    echo ブラウザで http://localhost:8501 にアクセスしてアプリを確認してください
    echo.
) else (
    echo.
    echo エラー: インポートに失敗しました
    echo - Dockerが起動しているか確認してください
    echo - MySQLコンテナが起動しているか確認してください
    echo - パスワードが正しいか確認してください
    echo.
)

pause

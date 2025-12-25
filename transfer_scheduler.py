"""
PDF自動転送スクリプト（Windows ホスト専用）
output/transfer_queue から Zドライブに PDFファイルを自動転送
"""
import time
import shutil
import os
from pathlib import Path
from datetime import datetime

# --- 設定 ---
PROJECT_ROOT = Path(r"c:\PST\ts_pm_all_v2")
SOURCE_DIR = PROJECT_ROOT / "output" / "transfer_queue"
TARGET_DIR = Path(r"Z:\D-業務\業務\B-各担当別\横井\06_Kubota\05_集荷予定表\集荷依頼書_(枚方)")
CHECK_INTERVAL = 60  # チェック間隔（秒）
LOG_FILE = PROJECT_ROOT / "transfer_log.txt"
# ------------

def log(message):
    """ログ出力（コンソール＋ファイル）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception as e:
        print(f"Log write error: {e}")

def transfer_files():
    """PDFファイルを転送"""
    # ソースディレクトリチェック
    if not SOURCE_DIR.exists():
        return

    # ターゲットディレクトリチェック
    if not TARGET_DIR.exists():
        log(f"Error: Target directory not accessible: {TARGET_DIR}")
        return

    # PDFファイルを検索
    pdf_files = list(SOURCE_DIR.glob("*.pdf"))
    if not pdf_files:
        return

    # 各ファイルを転送
    for file_path in pdf_files:
        try:
            target_path = TARGET_DIR / file_path.name
            log(f"Transferring: {file_path.name} -> Z: Drive")

            # コピー
            shutil.copy2(file_path, target_path)

            # 転送成功したら元ファイルを削除
            os.remove(file_path)
            log(f"Success: {file_path.name}")

        except Exception as e:
            log(f"Error transferring {file_path.name}: {e}")

if __name__ == "__main__":
    log("=== PDF Transfer Scheduler Started ===")
    log(f"Source: {SOURCE_DIR}")
    log(f"Target: {TARGET_DIR}")

    try:
        while True:
            transfer_files()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        log("Scheduler stopped by user")

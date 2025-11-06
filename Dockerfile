# Python 3.11 をベースイメージとして使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新と必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmariadb-dev \
    curl \
    pkg-config \
    fonts-ipafont-gothic \
    fonts-takao-gothic \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt をコピー
COPY requirements.txt .

# pywin32 を除外して依存関係をインストール
# sedを使用してpywin32を含む行をコメントアウト
RUN sed '/pywin32/s/^/#/' requirements.txt > requirements_docker.txt && \
    pip install --no-cache-dir -r requirements_docker.txt && \
    rm requirements_docker.txt

# アプリケーションのソースコードをコピー
COPY . .

# Streamlit のポート（デフォルト: 8501）を公開
EXPOSE 8501

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Streamlit アプリケーションを起動
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

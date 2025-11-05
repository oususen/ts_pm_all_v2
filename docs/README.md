# プロジェクトドキュメント

このディレクトリには、プロジェクトの各種ドキュメントが格納されています。

## 📚 ドキュメント一覧

### 🔧 技術ドキュメント（開発者・管理者向け）

#### [README_DOCKER.md](README_DOCKER.md)

**対象**: 開発者・管理者
**内容**: Docker環境の構築・運用ガイド
**用途**:

- Docker環境のセットアップ
- コンテナの起動・停止
- データベース初期化
- トラブルシューティング

---

#### [SETUP_GUIDE.md](SETUP_GUIDE.md)

**対象**: 開発者
**内容**: 開発環境セットアップ手順
**用途**:

- ローカル開発環境の構築
- Python仮想環境の設定
- 依存パッケージのインストール
- 初回セットアップ手順

---

#### [CUSTOMER_SWITCHING_GUIDE.md](CUSTOMER_SWITCHING_GUIDE.md)

**対象**: 開発者
**内容**: 顧客別データベース切り替え実装ガイド
**用途**:

- 顧客別DB設計の理解
- 新規顧客追加手順
- DB切り替えロジックの実装
- スキーマコピー方法

---

#### [USER_AUTH_README.md](USER_AUTH_README.md)

**対象**: 開発者
**内容**: ユーザー認証・権限管理システム説明
**用途**:

- 認証システムの仕組み
- ロール・権限の設定
- ユーザー管理機能
- セキュリティ設計

---

#### [TIERA_IMPLEMENTATION_SUMMARY.md](TIERA_IMPLEMENTATION_SUMMARY.md)

**対象**: 開発者
**内容**: ティエラ様対応実装サマリー
**用途**:

- ティエラ様固有の要件
- 実装した機能一覧
- 久保田様との差分
- 設計判断の記録

---

### 👥 エンドユーザー向けドキュメント

#### [SETUP_FOR_USERS.md](SETUP_FOR_USERS.md)

**対象**: エンドユーザー
**内容**: エンドユーザー向けセットアップ手順
**用途**:

- アプリケーションの起動方法
- 初回ログイン手順
- 基本的な使い方
- よくある質問

---

#### [GYOMU_USER_MANUAL.md](GYOMU_USER_MANUAL.md)

**対象**: 配送管理者（業務担当者）
**内容**: 配送計画システム操作マニュアル（約1,300行）
**用途**:

- 各機能の詳細な使い方
- 画面操作手順
- データ入力方法
- 業務フロー

---

## 🗂️ ドキュメントの分類

### セットアップ関連

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - 開発者向け
- [SETUP_FOR_USERS.md](SETUP_FOR_USERS.md) - エンドユーザー向け
- [README_DOCKER.md](README_DOCKER.md) - Docker環境

### システム設計・実装

- [CUSTOMER_SWITCHING_GUIDE.md](CUSTOMER_SWITCHING_GUIDE.md) - 顧客別DB
- [USER_AUTH_README.md](USER_AUTH_README.md) - 認証システム
- [TIERA_IMPLEMENTATION_SUMMARY.md](TIERA_IMPLEMENTATION_SUMMARY.md) - ティエラ実装

### 操作マニュアル

- [GYOMU_USER_MANUAL.md](GYOMU_USER_MANUAL.md) - 配送管理者向け

---

## 📖 ドキュメント閲覧の推奨順序

### 新規開発者向け

1. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - まず開発環境をセットアップ
2. **[README_DOCKER.md](README_DOCKER.md)** - Docker環境を理解
3. **[USER_AUTH_README.md](USER_AUTH_README.md)** - 認証システムを理解
4. **[CUSTOMER_SWITCHING_GUIDE.md](CUSTOMER_SWITCHING_GUIDE.md)** - 顧客別実装を理解

### 新規エンドユーザー向け

1. **[SETUP_FOR_USERS.md](SETUP_FOR_USERS.md)** - まずアプリを起動
2. **[GYOMU_USER_MANUAL.md](GYOMU_USER_MANUAL.md)** - 業務操作を学習

### 保守・拡張作業向け

1. **[TIERA_IMPLEMENTATION_SUMMARY.md](TIERA_IMPLEMENTATION_SUMMARY.md)** - 既存実装を確認
2. **[CUSTOMER_SWITCHING_GUIDE.md](CUSTOMER_SWITCHING_GUIDE.md)** - 顧客追加方法を確認
3. 該当する技術ドキュメント

---

## 🔍 ドキュメント検索のヒント

### Docker関連

→ [README_DOCKER.md](README_DOCKER.md)

### セットアップ・インストール

→ [SETUP_GUIDE.md](SETUP_GUIDE.md)（開発者）
→ [SETUP_FOR_USERS.md](SETUP_FOR_USERS.md)（エンドユーザー）

### ユーザー管理・権限

→ [USER_AUTH_README.md](USER_AUTH_README.md)

### 顧客別対応・DB切り替え

→ [CUSTOMER_SWITCHING_GUIDE.md](CUSTOMER_SWITCHING_GUIDE.md)

### ティエラ様の要件・実装

→ [TIERA_IMPLEMENTATION_SUMMARY.md](TIERA_IMPLEMENTATION_SUMMARY.md)

### 業務操作方法

→ [GYOMU_USER_MANUAL.md](GYOMU_USER_MANUAL.md)

---

## 📝 ドキュメント更新ガイドライン

### 更新が必要なタイミング

1. **機能追加時**
   - 該当するドキュメントに新機能の説明を追加
   - GYOMU_USER_MANUAL.mdに操作手順を追加

2. **設定変更時**
   - SETUP_GUIDE.mdやREADME_DOCKER.mdを更新
   - 環境変数の変更はすべての該当ドキュメントに反映

3. **新規顧客追加時**
   - CUSTOMER_SWITCHING_GUIDE.mdに事例を追加
   - 顧客固有の実装サマリーを作成（TIERA_IMPLEMENTATION_SUMMARY.mdを参考）

### ドキュメント作成の原則

- **わかりやすさ**: 専門用語は説明を添える
- **具体性**: コマンド例、画面例を豊富に記載
- **最新性**: コードと同時に更新する
- **構造化**: 見出し・リストを活用し、読みやすく

---

## 🌐 関連リソース

### プロジェクト全体の構造

→ [../README.md](../README.md) - プロジェクトルートのREADME

### SQL関連

→ [../sql/README.md](../sql/README.md) - SQLスクリプト説明

### スクリプト関連

→ [../scripts/README.md](../scripts/README.md) - ユーティリティスクリプト説明

---

## ⚠️ 注意事項

1. **機密情報の記載禁止**
   - パスワード、APIキー、データベース接続情報などは記載しない
   - `.env.example` を参考にするよう案内

2. **スクリーンショットの管理**
   - 個人情報や機密データが映り込まないよう注意
   - 必要に応じて画像は別ディレクトリで管理

3. **バージョン管理**
   - ドキュメントもGitで管理
   - 重要な変更はコミットメッセージに記載

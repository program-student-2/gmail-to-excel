# 就活メール → Excel 自動転記システム

就活のマイページ登録完了メールから、**企業名・ログインID・パスワード・ログインURL** を
自動で読み取り、管理用のExcelに転記するツールです。

- **メール取得**：Gmail API
- **情報抽出**：Claude API（メールの書式がバラバラでもAIが読み取る）
- **転記先**：既存のExcel管理表（企業名で照合し、空欄を補完／新規企業は追記）
- **実行**：`run.bat` をダブルクリック

## 特長

- 企業名の表記ゆれ（例：`野村證券`＝`野村証券`、`トヨタ`＝`トヨタ自動車`）を吸収し、重複行を作らない
- 既存データは上書きせず、空欄だけを補完（設定で変更可）
- 処理済みメールにはGmailラベルを付け、二重処理を防止

## セットアップ

詳しい手順は **[セットアップ手順.md](セットアップ手順.md)** を参照してください。概要：

1. `config.example.json` を `config.json` にコピーし、Excelのパスを設定
2. `.env.example` を `.env` にコピーし、Anthropic APIキーを記入
3. Google Cloud で Gmail API を有効化し、OAuthクライアントの `credentials.json` を配置
4. `run.bat` を実行

## 必要なもの

- Python 3.10 以上
- Anthropic API キー（[console.anthropic.com](https://console.anthropic.com/)）
- Google Cloud の OAuth クライアント（Gmail API 有効化）

## ⚠️ 公開・共有時の注意

次のファイルには秘密情報が含まれます。**絶対にコミット・共有しないでください**
（`.gitignore` で除外済み）：

- `.env`（APIキー）
- `credentials.json`（OAuthクライアントシークレット）
- `token.json`（アクセストークン）
- `config.json`（個人のローカルパス）

## ライセンス

MIT License

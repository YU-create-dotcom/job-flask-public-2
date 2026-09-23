# job-flask-app-service

複数の利用者が、それぞれ独立した就職活動データを管理するFlaskサービスです。

## 主な機能

- 管理者による利用者ID発行
- 利用者ごとのデータ完全分離
- サイト内カレンダーへの予定登録
- 今日・今週の予定、ES・適性検査締切、選考中企業への自動反映
- 利用者ごとのメール用Googleスプレッドシート連携
- GD・面接ログとAIフィードバック
- 自己分析項目の追加・削除
- 企業分析
- 利用者ごとのAIモデル選択
- 初期5ドルの内部AI残高と実トークン使用量による控除
- 管理者による残高、モデル、パスワード、利用可否の管理

## データについて

初回起動時、個人データは一切入っていません。管理者アカウントのみ環境変数から作成されます。
利用者ごとのログインが必要です。管理者画面は管理者アカウントだけが開けます。
管理者パスワードは初回作成時にのみ `ADMIN_PASSWORD` から設定されます。既存アカウントのパスワードを変更する場合は管理者画面または設定画面を使ってください。

本番環境ではRender PostgreSQLを使用してください。SQLiteは再デプロイ時にデータが消える可能性があります。

## ローカル起動

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
venv\Scripts\python app.py
```

## Render設定

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Health Check Path: `/login`

必要な環境変数は `.env.example` を参照してください。

`OPENAI_API_KEY` はデプロイ直前まで未設定でも、AI以外の機能は利用できます。

## メール連携

1. 利用者へ `docs/gmail_to_sheet.gs` を渡します。
2. 利用者が自分のGoogleスプレッドシートとGASへID・シート名を設定します。
3. 利用者がGASを一度実行してGmail権限を許可し、1時間ごとのトリガーを作成します。
4. 利用者がスプレッドシートをサービスアカウントへ「閲覧者」として共有します。
5. サービスの設定画面へスプレッドシートIDとシート名を入力します。

## AI料金計算

料金表は2026年6月19日時点のOpenAI公式標準料金です。

- GPT-5.4 mini: Input $0.75 / 1M tokens, Output $4.50 / 1M tokens
- GPT-5.5: Input $5.00 / 1M tokens, Output $30.00 / 1M tokens

実際のAPI応答に含まれるinput/output token数から利用額を計算し、利用者の内部残高から差し引きます。

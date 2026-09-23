# Renderデプロイ直前チェックリスト

## 1. GitHub

空のPrivateリポジトリ `job-flask-app-service` を作成します。

- Add README: Off
- Add .gitignore: No .gitignore
- Add license: No license

ローカルリポジトリへGitHubのURLを登録してpushします。

## 2. Render Blueprint

Renderで `New +` → `Blueprint` を選び、GitHubの `job-flask-app-service` を接続します。

`render.yaml` によりWeb ServiceとPostgreSQLが作成されます。

## 3. Render環境変数

Blueprint作成時に以下を入力します。

- `ADMIN_LOGIN_ID`: 管理者のログインID
- `ADMIN_PASSWORD`: 管理者の強力な初期パスワード（8文字以上）
- `OPENAI_API_KEY`: 最後に作成するOpenAI APIキー
- `GOOGLE_CREDENTIALS_BASE64`: GoogleサービスアカウントJSONのBase64
- `GOOGLE_SERVICE_ACCOUNT_EMAIL`: 上記サービスアカウントのメールアドレス

`SECRET_KEY` と `DATABASE_URL` はBlueprintから自動設定されます。

## 4. 初回確認

1. `/login` で管理者ログイン
2. 「利用者管理」でテスト利用者を作成
3. テスト利用者の初期残高が `$5.00` であることを確認
4. 予定登録がダッシュボード4領域へ反映されることを確認
5. 設定画面でスプレッドシートID・シート名を保存
6. AIモデルを選択
7. GDログを作り、AIフィードバック後に残高が減ることを確認

## OpenAIキー未設定時

ログイン、カレンダー、メールシート、GDログ、自己分析、企業分析は利用できます。
AIフィードバックだけがエラー表示になります。

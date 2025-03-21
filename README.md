# 病院自動呼び出し番号確認システム

病院の自動音声案内システムに定期的に電話をかけ、現在の呼び出し番号を取得・記録するスクリプトです。

## 必要条件

- Python 3.8以上
- Twilioアカウント
- OpenAIアカウント

## セットアップ

1. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

2. 環境変数の設定:
- `.env.example`を`.env`にコピー
- 必要な認証情報を入力
  - Twilio認証情報（ACCOUNT_SID, AUTH_TOKEN, PHONE_NUMBER）
  - OpenAI API Key
  - 問い合わせ先電話番号

## 使用方法

スクリプトを実行:
```bash
python auto_call.py
```

- 10分ごとに自動で電話をかけ、現在の呼び出し番号を取得します
- 結果はコンソールに表示され、ログファイルにも記録されます

## ログ

- ログは`call_log.txt`（デフォルト）に記録されます
- 日次でローテーションされ、7日分保持されます

## エラーハンドリング

- 通話失敗、録音失敗、音声認識エラーなどは適切にログに記録されます
- エラー発生時は次回の実行時に再試行されます

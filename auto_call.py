import os
import time
import schedule
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client
import openai
from loguru import logger
import platform
import subprocess

# 環境変数の読み込み
load_dotenv()

# ログの設定
log_file = os.getenv("LOG_FILE", "call_log.txt")
logger.add(log_file, rotation="1 day", retention="7 days")

# Twilio設定
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# OpenAI設定
openai.api_key = os.getenv("OPENAI_API_KEY")

def notify_user():
    """ユーザーに通知を送る"""
    if platform.system() == "Darwin":  # macOS
        subprocess.run(["osascript", "-e", 'display notification "呼び出し番号が近づきました！" with title "注意"'])
        subprocess.run(["say", "呼び出し番号が近づきました！"])
    else:
        logger.info("通知機能はこのOSでサポートされていません")

def make_call_and_record():
    """通話を発信し、録音を行う"""
    try:
        call = twilio_client.calls.create(
            to=os.getenv("TARGET_PHONE_NUMBER"),
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            record=True,
            twiml='<Response><Pause length="20"/><Hangup/></Response>'  # 通話時間を少し延長
        )

        logger.info(f"通話を開始しました: {call.sid}")

        # 録音が完了するまで待機
        wait_count = 0
        while wait_count < 30:  # 最大60秒待機
            call = twilio_client.calls(call.sid).fetch()
            if call.status in ["completed", "failed", "canceled"]:
                break
            time.sleep(2)
            wait_count += 1

        # 通話状態を確認
        if call.status == "failed":
            logger.error(f"通話が失敗しました: {call.status}")
            return None

        # 録音が作成されるまで少し待機
        time.sleep(5)  # 待機時間を短縮

        # 録音URLの取得をリトライ
        max_retries = 3
        for attempt in range(max_retries):
            recordings = twilio_client.recordings.list(call_sid=call.sid)
            if recordings:
                recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{os.getenv('TWILIO_ACCOUNT_SID')}/Recordings/{recordings[0].sid}.mp3"
                logger.info(f"録音を取得しました: {recording_url}")
                return recording_url
            logger.warning(f"録音の取得に失敗しました。リトライ {attempt + 1}/{max_retries}")
            time.sleep(5)  # リトライ間隔

        logger.error("録音が見つかりませんでした")
        return None

    except Exception as e:
        logger.error(f"通話または録音中にエラーが発生: {e}")
        return None

def transcribe_audio(audio_url):
    """音声をテキストに変換"""
    try:
        logger.info(f"音声認識を開始します: {audio_url}")

        # 音声ファイルをダウンロード
        response = requests.get(
            audio_url,
            auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        )

        if response.status_code != 200:
            logger.error(f"音声ファイルのダウンロードに失敗: {response.status_code}")
            return None

        # 一時ファイルとして保存
        temp_file = "temp_recording.mp3"
        with open(temp_file, "wb") as f:
            f.write(response.content)

        # 音声認識を実行
        with open(temp_file, "rb") as f:
            response = openai.Audio.transcribe(
                "whisper-1",
                f,
                language="ja"
            )

        # 一時ファイルを削除
        os.remove(temp_file)

        logger.info(f"音声認識結果: {response['text']}")
        return response["text"]
    except Exception as e:
        logger.error(f"音声認識中にエラーが発生: {e}")
        return None

def extract_number(text):
    """テキストから番号を抽出"""
    if not text:
        return None

    # 数字を抽出（例：「現在の呼び出し番号は123番です」から「123」を抽出）
    match = re.search(r'(\d+)番', text)
    if match:
        return match.group(1)
    return None

def check_current_number():
    """現在の番号をチェック"""
    logger.info("番号チェックを開始します")

    # 通話と録音
    recording_url = make_call_and_record()
    if not recording_url:
        logger.error("録音の取得に失敗しました")
        return

    # 音声認識
    text = transcribe_audio(recording_url)
    if not text:
        logger.error("音声認識に失敗しました")
        return

    # 番号の抽出
    number = extract_number(text)
    if number:
        message = f"現在の呼び出し番号: {number}"
        logger.info(message)
        print(message)
        if int(number) > 44:
            notify_user()
            logger.info("通知を送信したため、スクリプトを終了します。")
            exit(0)  # スクリプトを終了
    else:
        logger.error("番号を抽出できませんでした")

    # 次回の呼び出し時刻をログに表示
    next_call_time = datetime.now() + timedelta(minutes=10)
    logger.info(f"次回の呼び出し時刻: {next_call_time.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """メイン実行関数"""
    logger.info("自動呼び出し確認システムを開始します")

    # 初回実行
    check_current_number()

    # スケジュール設定（10分ごと）
    schedule.every(10).minutes.do(check_current_number)

    # 定期実行
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

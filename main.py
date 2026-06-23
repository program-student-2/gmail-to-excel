# -*- coding: utf-8 -*-
"""
就活メール → Excel 自動転記システム（メイン）

流れ:
  1. Gmail から未処理メールを取得
  2. Claude で企業名・ID・PW・URL を抽出
  3. Excel（サマーインターン管理表）へ転記
  4. 処理したメールに「処理済み」ラベルを付与
"""

import json
import os
import sys

# Windows コンソールでも日本語/✓ を文字化けさせない
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

import excel_writer
import extractor
import gmail_client

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(_HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def main():
    load_dotenv(os.path.join(_HERE, ".env"))

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[エラー] ANTHROPIC_API_KEY が設定されていません。")
        print("        .env ファイルに ANTHROPIC_API_KEY=... を記入してください。")
        return 1

    config = load_config()

    if not os.path.exists(config["excel_path"]):
        print(f"[エラー] Excelが見つかりません: {config['excel_path']}")
        return 1

    print("=" * 60)
    print(" 就活メール → Excel 自動転記システム")
    print("=" * 60)

    # 1. Gmail
    print("\n[1/4] Gmail に接続中...")
    service = gmail_client.get_service()
    print(f"      検索: {config['gmail_query']}")
    emails = gmail_client.fetch_unprocessed(
        service, config["gmail_query"], config["max_emails"]
    )
    print(f"      未処理メール: {len(emails)} 件")
    if not emails:
        print("\n処理対象のメールはありませんでした。")
        return 0

    label_id = None
    if config.get("mark_processed", True):
        label_id = gmail_client.ensure_label(service, config["processed_label"])

    # 2 & 3. 抽出 → Excel
    client = extractor.make_client()
    table = excel_writer.ExcelTable(
        config["excel_path"],
        config["sheet_name"],
        config["columns"],
        mypage_mark=config.get("mypage_mark", "済"),
    )
    existing_companies = table.company_names()

    print("\n[2/4] メールを解析して Excel に転記中...")
    summary = []
    for i, email in enumerate(emails, 1):
        subject = email.get("subject", "")[:40]
        try:
            data = extractor.extract(
                client, config["model"], email, existing_companies
            )
        except Exception as e:
            print(f"  {i:2}. [抽出失敗] {subject} … {e}")
            continue

        if not data.get("is_relevant"):
            print(f"  {i:2}. [対象外] {subject}")
            if label_id:
                gmail_client.mark_processed(service, email["id"], label_id)
            continue

        status, row, changes = table.upsert(
            data, overwrite=config.get("overwrite_existing", False)
        )
        marks = {"new": "新規", "update": "更新", "skip": "スキップ"}
        company = data.get("company_name", "?")
        print(f"  {i:2}. [{marks.get(status, status)}] {company} … {', '.join(changes)}")

        summary.append((status, company, row))

        # 4. 処理済みラベル
        if label_id and status != "skip":
            gmail_client.mark_processed(service, email["id"], label_id)

    # 保存
    print("\n[3/4] Excel を保存中...")
    try:
        table.save()
        print(f"      保存しました: {config['excel_path']}")
    except PermissionError:
        print("[エラー] Excelファイルが開いたままです。閉じてから再実行してください。")
        return 1

    # 集計
    print("\n[4/4] 完了")
    new_n = sum(1 for s, *_ in summary if s == "new")
    upd_n = sum(1 for s, *_ in summary if s == "update")
    print(f"      新規追加: {new_n} 件 / 既存更新: {upd_n} 件")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

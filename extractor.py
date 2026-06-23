# -*- coding: utf-8 -*-
"""Claude APIでメール本文から企業名・ID・PW・ログインURLを抽出するモジュール。"""

import json

import anthropic

# 抽出結果の構造（Structured Outputs で形を保証する）
_SCHEMA = {
    "type": "object",
    "properties": {
        "is_relevant": {
            "type": "boolean",
            "description": "就活マイページ登録・ID発行に関するメールなら true。それ以外（広告・通知など）は false。",
        },
        "company_name": {
            "type": "string",
            "description": "企業名。例: 野村総合研究所、トヨタ自動車。不明なら空文字。",
        },
        "login_id": {
            "type": "string",
            "description": "ログインID・会員ID・マイページID。無ければ空文字。",
        },
        "password": {
            "type": "string",
            "description": "パスワード。本文に明記されていれば。『登録時のもの』等で不明なら空文字。",
        },
        "login_url": {
            "type": "string",
            "description": "マイページ／ログインページのURL。複数あれば最もログイン用らしいもの1つ。無ければ空文字。",
        },
        "existing_match": {
            "type": "string",
            "description": (
                "既存企業リストの中に同じ企業があれば、その表記を一字一句そのまま返す"
                "（表記ゆれ・略称・新旧字体も同一企業とみなす。例: 野村證券=野村証券、トヨタ自動車=トヨタ）。"
                "同じ企業が無ければ空文字。"
            ),
        },
        "notes": {
            "type": "string",
            "description": "補足（任意・空でも可）。",
        },
    },
    "required": [
        "is_relevant",
        "company_name",
        "login_id",
        "password",
        "login_url",
        "existing_match",
        "notes",
    ],
    "additionalProperties": False,
}

_SYSTEM = (
    "あなたは就職活動中の学生のメールを整理するアシスタントです。"
    "与えられたメール本文から、就活マイページの企業名・ログインID・パスワード・"
    "ログインURLを正確に抽出してください。"
    "メールごとに書式はバラバラです（『ID：』『会員番号』『ログインID』など）。"
    "推測で値を作らず、本文に書かれている情報だけを抜き出してください。"
    "該当情報が無い項目は空文字にします。"
    "登録完了・ID発行・マイページ案内のメールでなければ is_relevant を false にしてください。"
)


def extract(client, model, email, existing_companies=None):
    """1通のメールから情報を抽出して辞書を返す。

    existing_companies: 既存の企業名リスト（表記ゆれ照合のためモデルに提示する）。
    """
    company_list = "（なし）"
    if existing_companies:
        company_list = "\n".join(f"- {c}" for c in existing_companies)

    content = (
        "【Excelに既に登録済みの企業名リスト】\n"
        f"{company_list}\n\n"
        "上記に同じ企業があれば existing_match にその表記をそのまま入れてください。\n\n"
        f"件名: {email.get('subject', '')}\n"
        f"差出人: {email.get('from', '')}\n"
        f"--- 本文ここから ---\n{email.get('body', '')}\n--- 本文ここまで ---"
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )

    text = next((b.text for b in response.content if b.type == "text"), "{}")
    return json.loads(text)


def make_client():
    """ANTHROPIC_API_KEY（環境変数）からClaudeクライアントを作る。"""
    return anthropic.Anthropic()

# -*- coding: utf-8 -*-
"""Gmail APIでメールを取得し、処理済みラベルを付けるためのモジュール。"""

import base64
import os
import re
from html.parser import HTMLParser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# gmail.modify: メール読み取り + ラベル付け（処理済みにするため）
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

_HERE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(_HERE, "credentials.json")
TOKEN_PATH = os.path.join(_HERE, "token.json")


class _HTMLTextExtractor(HTMLParser):
    """HTMLメールからプレーンテキストをざっくり取り出す。"""

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        if tag in ("br", "p", "div", "tr", "li"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        text = "".join(self._parts)
        return re.sub(r"\n{3,}", "\n\n", text)


def _html_to_text(html):
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return html
    return parser.get_text()


def get_service():
    """OAuth認証を行い、Gmail APIサービスを返す。初回はブラウザで認証する。"""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "credentials.json が見つかりません。"
                    "Google Cloud から OAuth クライアントをダウンロードして、"
                    f"次の場所に置いてください:\n  {CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_body(payload):
    """メール本文（プレーンテキスト優先）を取り出す。"""
    plain_parts = []
    html_parts = []

    def walk(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode(
                "utf-8", errors="replace"
            )
            if mime == "text/plain":
                plain_parts.append(decoded)
            elif mime == "text/html":
                html_parts.append(decoded)
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)

    if plain_parts:
        return "\n".join(plain_parts)
    if html_parts:
        return _html_to_text("\n".join(html_parts))
    return ""


def _header(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_unprocessed(service, query, max_emails):
    """検索クエリにマッチする未処理メールを取得し、辞書のリストで返す。"""
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_emails)
        .execute()
    )
    messages = result.get("messages", [])

    emails = []
    for meta in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=meta["id"], format="full")
            .execute()
        )
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        emails.append(
            {
                "id": meta["id"],
                "subject": _header(headers, "Subject"),
                "from": _header(headers, "From"),
                "body": _extract_body(payload),
            }
        )
    return emails


def ensure_label(service, label_name):
    """ラベルが無ければ作成し、ラベルIDを返す。"""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]
    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def mark_processed(service, message_id, label_id):
    """メールに処理済みラベルを付ける。"""
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]}
    ).execute()

#!/usr/bin/env python3
"""Мини-сервис формирования справок осмотра веб-страниц.

Запуск:
    python3 web_inspection_service.py

По умолчанию сервис стартует на http://127.0.0.1:8080.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import socketserver
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

REPORTS_DIR = Path("reports")
USER_AGENT = (
    "SellerPravoWebInspectionBot/1.0 "
    "(+https://sellerpravo.ru; purpose=web-inspection-certificate)"
)


class TitleAndLinksParser(HTMLParser):
    """Парсер заголовка страницы и ссылок."""

    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: List[str] = []
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data.strip())

    @property
    def title(self) -> str:
        return " ".join(part for part in self.title_parts if part).strip()


@dataclass
class InspectionReport:
    report_id: str
    inspected_at_utc: str
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    content_length_bytes: int
    sha256: str
    page_title: str
    extracted_links: List[str]
    response_headers: Dict[str, str]


def validate_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL должен начинаться с http:// или https://")
    return parsed.geturl()


def inspect_url(url: str, timeout: int = 15) -> InspectionReport:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
        body: bytes = response.read()
        final_url = response.geturl()
        status_code = response.status
        headers = {k: v for k, v in response.headers.items()}

    decoded_body = body.decode("utf-8", errors="replace")
    parser = TitleAndLinksParser()
    parser.feed(decoded_body)

    report = InspectionReport(
        report_id=str(uuid4()),
        inspected_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        requested_url=url,
        final_url=final_url,
        status_code=status_code,
        content_type=headers.get("Content-Type", ""),
        content_length_bytes=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
        page_title=parser.title,
        extracted_links=parser.links[:25],
        response_headers=headers,
    )
    return report


def save_report(report: InspectionReport) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{report.report_id}.json"
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def report_as_text(report: InspectionReport) -> str:
    lines = [
        "СПРАВКА О РЕЗУЛЬТАТАХ ОСМОТРА ВЕБ-СТРАНИЦЫ",
        "=" * 55,
        f"Номер справки: {report.report_id}",
        f"Дата и время (UTC): {report.inspected_at_utc}",
        "",
        f"Заявленный URL: {report.requested_url}",
        f"Фактический URL: {report.final_url}",
        f"HTTP статус: {report.status_code}",
        f"Тип содержимого: {report.content_type}",
        f"Размер ответа: {report.content_length_bytes} байт",
        f"SHA-256 содержимого: {report.sha256}",
        f"Заголовок страницы: {report.page_title or 'не найден'}",
        "",
        "Извлеченные ссылки (до 25):",
    ]

    if report.extracted_links:
        lines.extend(f"  {idx + 1}. {link}" for idx, link in enumerate(report.extracted_links))
    else:
        lines.append("  — ссылки не обнаружены")

    lines.append("\nКлючевые HTTP-заголовки:")
    for key in ["Date", "Server", "ETag", "Last-Modified", "Cache-Control"]:
        value = report.response_headers.get(key)
        if value:
            lines.append(f"  {key}: {value}")

    lines.append(
        "\nПримечание: данная справка фиксирует технические параметры страницы на момент обращения "
        "к веб-сервису и не является нотариальным действием."
    )

    return "\n".join(lines)


class InspectionHandler(BaseHTTPRequestHandler):
    server_version = "SellerPravoInspection/1.0"

    def _send_html(self, html_body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html_body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/inspect"}:
            self._send_html(index_page())
            return

        report_match = re.fullmatch(r"/reports/([a-f0-9\-]{36})\.(json|txt)", self.path)
        if report_match:
            report_id, ext = report_match.groups()
            report_path = REPORTS_DIR / f"{report_id}.json"
            if not report_path.exists():
                self._send_json({"error": "Справка не найдена"}, HTTPStatus.NOT_FOUND)
                return

            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            report = InspectionReport(**report_data)
            if ext == "json":
                self._send_json(report_data)
            else:
                content = report_as_text(report).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            return

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/inspect":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8"))
            url = validate_url(payload.get("url", ""))
            report = inspect_url(url)
            save_report(report)
        except (json.JSONDecodeError, TypeError):
            self._send_json({"error": "Некорректный JSON"}, HTTPStatus.BAD_REQUEST)
            return
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        except urllib.error.URLError as error:
            self._send_json(
                {"error": f"Не удалось выполнить осмотр URL: {error.reason}"},
                HTTPStatus.BAD_GATEWAY,
            )
            return

        self._send_json(
            {
                "ok": True,
                "report": asdict(report),
                "links": {
                    "json": f"/reports/{report.report_id}.json",
                    "text_certificate": f"/reports/{report.report_id}.txt",
                },
            }
        )


def index_page() -> str:
    return """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Web Inspection Certificate</title>
  <style>
    body{font-family:Arial,sans-serif;max-width:920px;margin:30px auto;padding:0 16px;line-height:1.5}
    h1{margin-bottom:6px}
    .sub{color:#555;margin-top:0}
    .row{display:flex;gap:10px;margin:18px 0}
    input{flex:1;padding:10px;font-size:16px}
    button{padding:10px 16px;font-size:16px;cursor:pointer}
    pre{background:#111;color:#e8e8e8;padding:14px;border-radius:8px;overflow:auto;white-space:pre-wrap}
    .err{color:#b00020;font-weight:700}
    .links a{display:block}
  </style>
</head>
<body>
  <h1>Справка осмотра веб-страницы</h1>
  <p class="sub">Сервис фиксирует техническое состояние веб-страницы на момент обращения: URL, HTTP-статус, заголовки, SHA-256 контента и извлечённые ссылки.</p>

  <div class="row">
    <input id="url" placeholder="https://example.com" />
    <button onclick="runInspection()">Сформировать справку</button>
  </div>

  <p id="status"></p>
  <div class="links" id="links"></div>
  <pre id="result">Пока нет данных.</pre>

  <script>
    async function runInspection(){
      const status = document.getElementById('status');
      const links = document.getElementById('links');
      const result = document.getElementById('result');
      const url = document.getElementById('url').value.trim();

      status.textContent = 'Выполняем осмотр...';
      status.className = '';
      links.innerHTML = '';

      const res = await fetch('/api/inspect', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({url})
      });
      const data = await res.json();

      if(!res.ok){
        status.textContent = data.error || 'Ошибка';
        status.className = 'err';
        return;
      }

      status.textContent = 'Справка сформирована';
      result.textContent = JSON.stringify(data.report, null, 2);
      links.innerHTML = `
        <a href="${data.links.json}" target="_blank">Скачать JSON справки</a>
        <a href="${data.links.text_certificate}" target="_blank">Скачать текстовую справку</a>
      `;
    }
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Web inspection certificate service")
    parser.add_argument("--host", default="127.0.0.1", help="Host for bind")
    parser.add_argument("--port", type=int, default=8080, help="Port for bind")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with socketserver.ThreadingTCPServer((args.host, args.port), InspectionHandler) as httpd:
        print(f"Inspection service started at http://{args.host}:{args.port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()

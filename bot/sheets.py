"""
Слой доступа к Google-таблице (реестру).
Таблица — единый источник правды. Все операции бота читают/пишут сюда.
gspread синхронный, поэтому каждый вызов оборачивается в asyncio.to_thread,
чтобы не блокировать event loop телеграм-бота.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict

import gspread
from google.oauth2.service_account import Credentials

from bot import config as cfg

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_spreadsheet: Optional[gspread.Spreadsheet] = None


# ── Подключение ───────────────────────────────────────────────────────────────

def _connect_sync() -> gspread.Spreadsheet:
    global _spreadsheet
    if cfg.GOOGLE_CREDENTIALS_JSON:
        info = json.loads(cfg.GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            cfg.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
        )
    gc = gspread.authorize(creds)
    _spreadsheet = gc.open_by_key(cfg.SPREADSHEET_ID)
    _ensure_structure_sync()
    return _spreadsheet


def _ensure_structure_sync() -> None:
    """Создаёт недостающие листы с заголовками (без оформления).
    Делает бота устойчивым, даже если setup_sheet не запускали."""
    sh = _spreadsheet
    needed = {
        cfg.SHEET_REGISTRY: cfg.REGISTRY_HEADERS,
        cfg.SHEET_STAFF: cfg.STAFF_HEADERS,
        cfg.SHEET_AGENCIES: cfg.AGENCY_HEADERS,
        cfg.SHEET_CLIENTS: cfg.CLIENT_HEADERS,
        cfg.SHEET_LOG: cfg.LOG_HEADERS,
    }
    existing = {w.title for w in sh.worksheets()}
    for title, headers in needed.items():
        if title not in existing:
            ws = sh.add_worksheet(title=title, rows=1000, cols=max(12, len(headers)))
            ws.update("A1", [headers], value_input_option="USER_ENTERED")
            ws.freeze(rows=1)
        else:
            ws = sh.worksheet(title)
            if not ws.acell("A1").value:
                ws.update("A1", [headers], value_input_option="USER_ENTERED")
                ws.freeze(rows=1)


async def connect() -> gspread.Spreadsheet:
    return await asyncio.to_thread(_connect_sync)


def _sh() -> gspread.Spreadsheet:
    if _spreadsheet is None:
        raise RuntimeError("Таблица не подключена. Вызовите connect() при старте.")
    return _spreadsheet


def _ws(title: str) -> gspread.Worksheet:
    return _sh().worksheet(title)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ── Реестр поручений ──────────────────────────────────────────────────────────

def _next_id_sync(date_prefix: str) -> str:
    """ID вида 2026-06-23-001 — счётчик в рамках дня создания."""
    ws = _ws(cfg.SHEET_REGISTRY)
    ids = ws.col_values(1)[1:]  # без заголовка
    count = sum(1 for x in ids if str(x).startswith(date_prefix))
    return f"{date_prefix}-{count + 1:03d}"


def _create_task_sync(data: Dict) -> str:
    ws = _ws(cfg.SHEET_REGISTRY)
    today = datetime.now()
    task_id = _next_id_sync(today.strftime("%Y-%m-%d"))

    data = dict(data)
    data[cfg.H_ID] = task_id
    data[cfg.H_CREATED] = _now()
    data.setdefault(cfg.H_STATUS, cfg.ST_NEW)
    data[cfg.H_UPDATED] = _now()

    row = [str(data.get(h, "")) for h in cfg.REGISTRY_HEADERS]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return task_id


def _find_row_sync(task_id: str) -> Optional[int]:
    ws = _ws(cfg.SHEET_REGISTRY)
    ids = ws.col_values(1)
    for idx, val in enumerate(ids, start=1):
        if val == task_id:
            return idx
    return None


def _records_sync() -> List[Dict]:
    return _ws(cfg.SHEET_REGISTRY).get_all_records()


def _get_task_sync(task_id: str) -> Optional[Dict]:
    for rec in _records_sync():
        if str(rec.get(cfg.H_ID)) == task_id:
            return rec
    return None


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _update_task_sync(task_id: str, updates: Dict) -> bool:
    ws = _ws(cfg.SHEET_REGISTRY)
    row_idx = _find_row_sync(task_id)
    if not row_idx:
        return False
    updates = dict(updates)
    updates[cfg.H_UPDATED] = _now()
    cells = []
    for header, value in updates.items():
        if header not in cfg.REGISTRY_HEADERS:
            continue
        col = cfg.REGISTRY_HEADERS.index(header) + 1
        a1 = f"{_col_letter(col)}{row_idx}"
        cells.append({"range": a1, "values": [[str(value)]]})
    if cells:
        ws.batch_update(cells, value_input_option="USER_ENTERED")
    return True


def _append_comment_sync(task_id: str, author: str, text: str) -> bool:
    ws = _ws(cfg.SHEET_REGISTRY)
    row_idx = _find_row_sync(task_id)
    if not row_idx:
        return False
    col = cfg.REGISTRY_HEADERS.index(cfg.H_COMMENTS) + 1
    a1 = f"{_col_letter(col)}{row_idx}"
    current = ws.acell(a1).value or ""
    stamp = datetime.now().strftime("%d.%m %H:%M")
    entry = f"[{stamp} {author}] {text}"
    new_val = (current + "\n" + entry).strip()
    upd_col = cfg.REGISTRY_HEADERS.index(cfg.H_UPDATED) + 1
    ws.batch_update([
        {"range": a1, "values": [[new_val]]},
        {"range": f"{_col_letter(upd_col)}{row_idx}", "values": [[_now()]]},
    ], value_input_option="USER_ENTERED")
    return True


# Публичные асинхронные обёртки

async def next_id(date_prefix: str) -> str:
    return await asyncio.to_thread(_next_id_sync, date_prefix)


async def create_task(data: Dict) -> str:
    return await asyncio.to_thread(_create_task_sync, data)


async def get_task(task_id: str) -> Optional[Dict]:
    return await asyncio.to_thread(_get_task_sync, task_id)


async def update_task(task_id: str, updates: Dict) -> bool:
    return await asyncio.to_thread(_update_task_sync, task_id, updates)


async def append_comment(task_id: str, author: str, text: str) -> bool:
    return await asyncio.to_thread(_append_comment_sync, task_id, author, text)


async def all_tasks() -> List[Dict]:
    return await asyncio.to_thread(_records_sync)


async def filter_tasks(
    statuses: tuple = None,
    initiator_tg: str = None,
    executor_tg: str = None,
    plan_date: str = None,
) -> List[Dict]:
    records = await all_tasks()
    out = []
    for r in records:
        if statuses and r.get(cfg.H_STATUS) not in statuses:
            continue
        if initiator_tg and str(r.get(cfg.H_INITIATOR_TG)) != str(initiator_tg):
            continue
        if executor_tg and str(r.get(cfg.H_EXECUTOR_TG)) != str(executor_tg):
            continue
        if plan_date and str(r.get(cfg.H_PLAN_DATE)) != plan_date:
            continue
        out.append(r)
    return out


async def search_tasks(query: str, limit: int = 15) -> List[Dict]:
    q = query.lower().strip()
    records = await all_tasks()
    fields = [
        cfg.H_ID, cfg.H_CLIENT, cfg.H_CASE, cfg.H_ORGAN, cfg.H_ORGAN_TYPE,
        cfg.H_ACTION, cfg.H_FULL, cfg.H_INITIATOR, cfg.H_EXECUTOR, cfg.H_STATUS,
    ]
    out = []
    for r in records:
        haystack = " ".join(str(r.get(f, "")) for f in fields).lower()
        if q in haystack:
            out.append(r)
    return out[-limit:][::-1]  # последние совпадения сверху


# ── Справочник сотрудников ────────────────────────────────────────────────────

def _staff_records_sync() -> List[Dict]:
    return _ws(cfg.SHEET_STAFF).get_all_records()


def _get_user_sync(tg_id: int) -> Optional[Dict]:
    for r in _staff_records_sync():
        if str(r.get("Telegram ID")) == str(tg_id):
            return r
    return None


def _register_user_sync(tg_id: int, name: str, role: str, username: str = "") -> None:
    ws = _ws(cfg.SHEET_STAFF)
    ids = ws.col_values(1)
    for idx, val in enumerate(ids, start=1):
        if str(val) == str(tg_id):
            ws.update(
                f"B{idx}:D{idx}",
                [[name, role, username]],
                value_input_option="USER_ENTERED",
            )
            return
    ws.append_row(
        [str(tg_id), name, role, username, "", "", "", _now()],
        value_input_option="USER_ENTERED",
    )


def _users_by_role_sync(role: str) -> List[Dict]:
    return [r for r in _staff_records_sync() if r.get("Роль") == role]


async def get_user(tg_id: int) -> Optional[Dict]:
    return await asyncio.to_thread(_get_user_sync, tg_id)


async def register_user(tg_id: int, name: str, role: str, username: str = "") -> None:
    return await asyncio.to_thread(_register_user_sync, tg_id, name, role, username)


async def users_by_role(role: str) -> List[Dict]:
    return await asyncio.to_thread(_users_by_role_sync, role)


async def all_executors() -> List[Dict]:
    staff = await asyncio.to_thread(_staff_records_sync)
    return [r for r in staff if r.get("Роль") in cfg.EXECUTOR_ROLES]


async def secretary_tg_ids() -> List[int]:
    secs = await users_by_role(cfg.ROLE_SECRETARY)
    return [int(s["Telegram ID"]) for s in secs if str(s.get("Telegram ID")).isdigit()]


# ── Справочник органов ────────────────────────────────────────────────────────

async def agencies() -> List[Dict]:
    return await asyncio.to_thread(lambda: _ws(cfg.SHEET_AGENCIES).get_all_records())


async def agencies_by_type(organ_type: str) -> List[Dict]:
    items = await agencies()
    return [a for a in items if a.get("Тип органа") == organ_type]


# ── Журнал действий ───────────────────────────────────────────────────────────

def _log_sync(actor: str, action: str, task_id: str, details: str) -> None:
    _ws(cfg.SHEET_LOG).append_row(
        [_now(), actor, action, task_id, details],
        value_input_option="USER_ENTERED",
    )


async def log(actor: str, action: str, task_id: str = "", details: str = "") -> None:
    try:
        await asyncio.to_thread(_log_sync, actor, action, task_id, details)
    except Exception:
        pass  # журнал не критичен

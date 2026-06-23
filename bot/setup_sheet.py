"""
Одноразовый скрипт: создаёт и оформляет всю структуру Google-таблицы —
листы, заголовки, выпадающие списки, цветовую заливку статусов, панель контроля
и стартовое наполнение справочника органов.

Запуск:  python -m bot.setup_sheet
Таблица должна быть уже создана и расшарена на сервисный аккаунт (см. ВНЕДРЕНИЕ.md).
"""
import json

import gspread
from google.oauth2.service_account import Credentials

from bot import config as cfg

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _open():
    if cfg.GOOGLE_CREDENTIALS_JSON:
        creds = Credentials.from_service_account_info(
            json.loads(cfg.GOOGLE_CREDENTIALS_JSON), scopes=SCOPES
        )
    else:
        creds = Credentials.from_service_account_file(
            cfg.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
        )
    gc = gspread.authorize(creds)
    return gc.open_by_key(cfg.SPREADSHEET_ID)


def _ensure_ws(sh, title, rows, cols):
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
    return ws


def _set_headers(ws, headers):
    ws.update("A1", [headers], value_input_option="USER_ENTERED")
    ws.freeze(rows=1)
    ws.format("A1:1", {
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "backgroundColor": {"red": 0.15, "green": 0.20, "blue": 0.35},
        "horizontalAlignment": "CENTER",
        "wrapStrategy": "WRAP",
    })


def _dropdown(sh, ws, header_list, header_name, values):
    """Выпадающий список для всей колонки (со 2-й строки)."""
    if header_name not in header_list:
        return
    col = header_list.index(header_name)  # 0-based
    req = {
        "setDataValidation": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 1,
                "endRowIndex": 5000,
                "startColumnIndex": col,
                "endColumnIndex": col + 1,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in values],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    }
    sh.batch_update({"requests": [req]})


def _status_colors(sh, ws):
    """Условное форматирование колонки статуса."""
    col = cfg.REGISTRY_HEADERS.index(cfg.H_STATUS)
    palette = {
        cfg.ST_NEW: (0.85, 0.92, 1.0),
        cfg.ST_CLARIFY: (1.0, 0.95, 0.80),
        cfg.ST_READY: (0.90, 0.96, 0.86),
        cfg.ST_ASSIGNED: (0.80, 0.90, 0.98),
        cfg.ST_DONE_WAIT: (0.95, 0.90, 1.0),
        cfg.ST_REVISIT: (1.0, 0.90, 0.75),
        cfg.ST_FAILED: (1.0, 0.80, 0.80),
        cfg.ST_OVERDUE: (1.0, 0.70, 0.70),
        cfg.ST_CANCELLED: (0.90, 0.90, 0.90),
        cfg.ST_ACCEPTED: (0.80, 0.95, 0.80),
    }
    requests = []
    for status, (r, g, b) in palette.items():
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 5000,
                        "startColumnIndex": col, "endColumnIndex": col + 1,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": status}],
                        },
                        "format": {"backgroundColor": {"red": r, "green": g, "blue": b}},
                    },
                },
                "index": 0,
            }
        })
    sh.batch_update({"requests": requests})


def _build_dashboard(ws):
    """Панель контроля на формулах поверх 01_Реестр."""
    reg = f"'{cfg.SHEET_REGISTRY}'"
    status_col = chr(65 + cfg.REGISTRY_HEADERS.index(cfg.H_STATUS))
    plan_col = chr(65 + cfg.REGISTRY_HEADERS.index(cfg.H_PLAN_DATE))
    exec_col = chr(65 + cfg.REGISTRY_HEADERS.index(cfg.H_EXECUTOR))

    rows = [
        ["ПАНЕЛЬ КОНТРОЛЯ ПОРУЧЕНИЙ", ""],
        ["Показатель", "Значение"],
        ["Всего поручений", f"=COUNTA({reg}!A2:A)"],
        ["Новых заявок", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_NEW}")'],
        ["Требуют уточнения", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_CLARIFY}")'],
        ["Готовы к маршрутизации", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_READY}")'],
        ["Назначено", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_ASSIGNED}")'],
        ["Ждут приёмки", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_DONE_WAIT}")'],
        ["Повторный визит", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_REVISIT}")'],
        ["Просрочено", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_OVERDUE}")'],
        ["Не исполнено", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_FAILED}")'],
        ["Принято (закрыто)", f'=COUNTIF({reg}!{status_col}2:{status_col},"{cfg.ST_ACCEPTED}")'],
        ["", ""],
        ["На сегодня в плане",
         f'=COUNTIF({reg}!{plan_col}2:{plan_col},TEXT(TODAY(),"yyyy-mm-dd"))'],
        ["На завтра в плане",
         f'=COUNTIF({reg}!{plan_col}2:{plan_col},TEXT(TODAY()+1,"yyyy-mm-dd"))'],
        ["", ""],
        ["⚠️ Без исполнителя (в работе)",
         f'=COUNTIFS({reg}!{exec_col}2:{exec_col},"",{reg}!{status_col}2:{status_col},"<>"&"{cfg.ST_CANCELLED}",{reg}!{status_col}2:{status_col},"<>"&"{cfg.ST_ACCEPTED}")'],
    ]
    ws.update("A1", rows, value_input_option="USER_ENTERED")
    ws.format("A1:B1", {
        "textFormat": {"bold": True, "fontSize": 14},
        "backgroundColor": {"red": 0.15, "green": 0.20, "blue": 0.35},
    })
    ws.format("A1:B1", {"textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
    ws.format("A2:B2", {"textFormat": {"bold": True}})


# Стартовое наполнение справочника органов (на основе старой таблицы)
SEED_AGENCIES = [
    ["Суд общей юрисдикции", "Суды Москвы (общий приём)", "", "",
     "ПН с 14:00, ЧТ с 09:00", "Нет", "Приёмные дни помощников — ПН и ЧТ", ""],
    ["ОСП (приставы)", "ОСП (общий режим)", "", "",
     "ВТ 09:00-13:00, ЧТ 14:00-18:00", "Иногда", "Крутицкий Вал и др.", ""],
    ["ГИБДД/ГАИ", "ГИБДД (Перерва, 21)", "ул. Перерва, 21", "",
     "Приёма нет", "Нет", "Только ящик для документов, приёма нет", ""],
    ["ГИБДД/ГАИ", "ГИБДД (Садовая-Самотечная)", "ул. Садовая-Самотечная", "",
     "Запросы только ЧТ", "Нет", "Запросы принимают только по четвергам", ""],
    ["Военкомат", "Военкоматы (общий режим)", "", "",
     "По графику учреждения", "Да", "График приёма граждан зависит от района", ""],
]


def main():
    print("Подключаюсь к таблице…")
    sh = _open()
    print(f"Открыта таблица: {sh.title}")

    # 01_Реестр
    print("→ 01_Реестр")
    reg = _ensure_ws(sh, cfg.SHEET_REGISTRY, 1000, len(cfg.REGISTRY_HEADERS))
    _set_headers(reg, cfg.REGISTRY_HEADERS)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_STATUS, cfg.STATUSES)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_ORGAN_TYPE, cfg.ORGAN_TYPES)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_TASK_TYPE, cfg.TASK_TYPES)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_PRIORITY, cfg.PRIORITIES)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_EXECUTOR_TYPE, cfg.EXECUTOR_TYPES)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_POA, cfg.YES_NO)
    _dropdown(sh, reg, cfg.REGISTRY_HEADERS, cfg.H_MOVABLE, cfg.YES_NO)
    _status_colors(sh, reg)

    # Справочники
    print("→ Справочник_Сотрудники")
    staff = _ensure_ws(sh, cfg.SHEET_STAFF, 200, len(cfg.STAFF_HEADERS))
    _set_headers(staff, cfg.STAFF_HEADERS)
    _dropdown(sh, staff, cfg.STAFF_HEADERS, "Роль", cfg.ROLES)

    print("→ Справочник_Органы")
    ag = _ensure_ws(sh, cfg.SHEET_AGENCIES, 500, len(cfg.AGENCY_HEADERS))
    _set_headers(ag, cfg.AGENCY_HEADERS)
    _dropdown(sh, ag, cfg.AGENCY_HEADERS, "Тип органа", cfg.ORGAN_TYPES)
    if len(ag.col_values(1)) <= 1:  # пусто — наполняем
        ag.append_rows(SEED_AGENCIES, value_input_option="USER_ENTERED")

    print("→ Справочник_Клиенты")
    cl = _ensure_ws(sh, cfg.SHEET_CLIENTS, 1000, len(cfg.CLIENT_HEADERS))
    _set_headers(cl, cfg.CLIENT_HEADERS)

    print("→ Журнал")
    lg = _ensure_ws(sh, cfg.SHEET_LOG, 5000, len(cfg.LOG_HEADERS))
    _set_headers(lg, cfg.LOG_HEADERS)

    # 00_Панель
    print("→ 00_Панель")
    dash = _ensure_ws(sh, cfg.SHEET_DASHBOARD, 40, 4)
    _build_dashboard(dash)

    # Переставим панель первой
    try:
        sh.reorder_worksheets([
            dash, reg, ag, staff, cl, lg,
        ] + [w for w in sh.worksheets()
             if w.title not in (cfg.SHEET_DASHBOARD, cfg.SHEET_REGISTRY,
                                cfg.SHEET_AGENCIES, cfg.SHEET_STAFF,
                                cfg.SHEET_CLIENTS, cfg.SHEET_LOG)])
    except Exception:
        pass

    print("\n✅ Структура таблицы готова.")
    print("Откройте таблицу — там появились листы 00_Панель, 01_Реестр и справочники.")


if __name__ == "__main__":
    main()

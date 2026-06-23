import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict

_db_path: Optional[Path] = None


def _get_path() -> Path:
    global _db_path
    if _db_path is None:
        from bot.config import DATABASE_PATH
        _db_path = Path(DATABASE_PATH)
        _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


async def init_db() -> None:
    async with aiosqlite.connect(_get_path()) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                username TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                court TEXT NOT NULL,
                case_name TEXT NOT NULL,
                case_number TEXT,
                client TEXT NOT NULL,
                description TEXT NOT NULL,
                notes TEXT,
                has_poa INTEGER DEFAULT 0,
                representative_id INTEGER NOT NULL,
                executor_id INTEGER,
                scheduled_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                completed_at TEXT,
                FOREIGN KEY (representative_id) REFERENCES users(id),
                FOREIGN KEY (executor_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS assistant_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assistant_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                court TEXT NOT NULL,
                UNIQUE(assistant_id, date),
                FOREIGN KEY (assistant_id) REFERENCES users(id)
            );
        """)
        await db.commit()


async def get_user(telegram_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(telegram_id: int, name: str, role: str, username: str = None) -> None:
    async with aiosqlite.connect(_get_path()) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (telegram_id, name, role, username) VALUES (?, ?, ?, ?)",
            (telegram_id, name, role, username),
        )
        await db.commit()


async def update_user_role(telegram_id: int, role: str) -> None:
    async with aiosqlite.connect(_get_path()) as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (role, telegram_id)
        )
        await db.commit()


async def get_users_by_role(role: str) -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role = ? ORDER BY name", (role,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_executors() -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role IN ('courier', 'assistant') ORDER BY role, name"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_users() -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY role, name") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def create_task(data: Dict) -> int:
    async with aiosqlite.connect(_get_path()) as db:
        cur = await db.execute(
            """INSERT INTO tasks
               (court, case_name, case_number, client, description, notes,
                has_poa, representative_id, scheduled_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["court"], data["case_name"], data.get("case_number"),
                data["client"], data["description"], data.get("notes"),
                1 if data.get("has_poa") else 0,
                data["representative_id"], data["scheduled_date"],
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_task(task_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT t.*,
                      u1.name as representative_name, u1.telegram_id as representative_tg,
                      u2.name as executor_name, u2.telegram_id as executor_tg
               FROM tasks t
               LEFT JOIN users u1 ON t.representative_id = u1.id
               LEFT JOIN users u2 ON t.executor_id = u2.id
               WHERE t.id = ?""",
            (task_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_tasks_for_date(scheduled_date: str) -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT t.*,
                      u1.name as representative_name,
                      u2.name as executor_name, u2.telegram_id as executor_tg
               FROM tasks t
               LEFT JOIN users u1 ON t.representative_id = u1.id
               LEFT JOIN users u2 ON t.executor_id = u2.id
               WHERE t.scheduled_date = ?
               ORDER BY t.status, t.court, t.id""",
            (scheduled_date,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_tasks_for_executor(executor_id: int, scheduled_date: str) -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT t.*, u1.name as representative_name, u1.telegram_id as representative_tg
               FROM tasks t
               LEFT JOIN users u1 ON t.representative_id = u1.id
               WHERE t.executor_id = ? AND t.scheduled_date = ?
                 AND t.status IN ('assigned', 'in_progress')
               ORDER BY t.court, t.id""",
            (executor_id, scheduled_date),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_tasks_by_representative(rep_id: int, limit: int = 20) -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT t.*, u2.name as executor_name
               FROM tasks t
               LEFT JOIN users u2 ON t.executor_id = u2.id
               WHERE t.representative_id = ?
               ORDER BY t.scheduled_date DESC, t.id DESC
               LIMIT ?""",
            (rep_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def assign_task(task_id: int, executor_id: int) -> None:
    async with aiosqlite.connect(_get_path()) as db:
        await db.execute(
            "UPDATE tasks SET executor_id = ?, status = 'assigned' WHERE id = ?",
            (executor_id, task_id),
        )
        await db.commit()


async def complete_task(task_id: int, result: str, success: bool = True) -> None:
    status = "done" if success else "failed"
    async with aiosqlite.connect(_get_path()) as db:
        await db.execute(
            """UPDATE tasks SET result = ?, status = ?,
               completed_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (result, status, task_id),
        )
        await db.commit()


async def get_archived_tasks(limit: int = 30, offset: int = 0) -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT t.*, u1.name as representative_name, u2.name as executor_name
               FROM tasks t
               LEFT JOIN users u1 ON t.representative_id = u1.id
               LEFT JOIN users u2 ON t.executor_id = u2.id
               WHERE t.status IN ('done', 'failed')
               ORDER BY t.completed_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def set_assistant_schedule(assistant_id: int, date_str: str, court: str) -> None:
    async with aiosqlite.connect(_get_path()) as db:
        await db.execute(
            "INSERT OR REPLACE INTO assistant_schedule (assistant_id, date, court) VALUES (?, ?, ?)",
            (assistant_id, date_str, court),
        )
        await db.commit()


async def get_assistant_schedule(date_str: str, court: str = None) -> List[Dict]:
    async with aiosqlite.connect(_get_path()) as db:
        db.row_factory = aiosqlite.Row
        if court:
            async with db.execute(
                """SELECT s.*, u.name, u.telegram_id, u.id as user_id
                   FROM assistant_schedule s
                   JOIN users u ON s.assistant_id = u.id
                   WHERE s.date = ? AND s.court = ?""",
                (date_str, court),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]
        else:
            async with db.execute(
                """SELECT s.*, u.name, u.telegram_id, u.id as user_id
                   FROM assistant_schedule s
                   JOIN users u ON s.assistant_id = u.id
                   WHERE s.date = ?""",
                (date_str,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

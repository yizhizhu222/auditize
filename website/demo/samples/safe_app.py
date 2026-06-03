"""
安全代码示例 — 使用良好实践
"""
import os
import sqlite3
from typing import Optional


# API Key 从环境变量读取，不硬编码
API_KEY = os.environ.get("API_KEY", "")


def safe_login(username: str, password: str) -> Optional[tuple]:
    """安全的登录函数 — 使用参数化查询"""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # 参数化查询，防止 SQL 注入
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    return cursor.fetchone()


def safe_execute_command(cmd: list[str]) -> str:
    """安全的命令执行 — 使用白名单"""
    allowed_commands = {
        "ping": ["ping", "-c", "4", "8.8.8.8"],
        "date": ["date"],
        "uptime": ["uptime"],
    }

    if cmd[0] not in allowed_commands:
        raise ValueError(f"Command not allowed: {cmd[0]}")

    import subprocess
    result = subprocess.run(
        allowed_commands[cmd[0]],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout


def save_report(data: dict, filepath: str) -> None:
    """安全地保存数据到 JSON 文件"""
    import json
    # 使用 JSON 替代 pickle，避免反序列化风险
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_db_path() -> str:
    """安全地获取数据库路径"""
    db_dir = "/var/lib/app/data"
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "app.db")


if __name__ == "__main__":
    user = safe_login("admin", "password123")
    print(f"User: {user}")
    uptime = safe_execute_command(["uptime"])
    print(f"Uptime: {uptime}")

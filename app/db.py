import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor


def _config() -> dict:
    return dict(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "app"),
        password=os.getenv("DB_PASSWORD", "app_password"),
        database=os.getenv("DB_NAME", "book_lending"),
        cursorclass=DictCursor,
        charset="utf8mb4",
        # Store all NOW() values in UTC so due dates are unambiguous.
        init_command="SET time_zone = '+00:00'",
    )


@contextmanager
def transaction():
    """One request = one transaction. Commit on success, roll back on any exception.

    A business-rule HTTPException also triggers rollback, so a rejected
    request leaves the database exactly as it was.
    """
    conn = pymysql.connect(**_config())
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
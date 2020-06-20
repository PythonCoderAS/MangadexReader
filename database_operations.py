import os
import sys
from typing import List, Optional, Tuple, Union

import psycopg2

from mangadex_operations import fetch_data

DATABASE_URL = os.environ['DATABASE_URL']

if "darwin" in sys.implementation._multiarch:
    conn = psycopg2.connect(DATABASE_URL, host="localhost")
else:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')

autocommit = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
conn.set_isolation_level(autocommit)


def setup_db():
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS MANGADEX
(
    MANGA_ID       INTEGER PRIMARY KEY CHECK (MANGA_ID > 0),
    TITLE          TEXT    NOT NULL CHECK ( length(TITLE) > 0 ),
    COVER_URL      TEXT    NOT NULL CHECK ( length(COVER_URL) > 0 AND
                                            left(COVER_URL, 38) = 'https://www.mangadex.org/images/manga/' ),
    READ           INTEGER NOT NULL DEFAULT 0 CHECK (READ >= 0),
    TOTAL          INTEGER NOT NULL CHECK ( TOTAL > 0 ),
    COMPLETED      BOOLEAN NOT NULL DEFAULT FALSE,
    UPDATED        BOOLEAN NOT NULL DEFAULT TRUE,
    USER_COMPLETED BOOLEAN NOT NULL DEFAULT FALSE
);""")


def get_data(manga_id: int,
             parameters: Optional[List[str]] = None) -> Union[Tuple[str, str, int, int, bool, bool],
                                                              Tuple[Union[int, bool, str]]]:
    cursor = conn.cursor()
    if parameters is None:
        parameters = ["title", "cover_url", "read", "total", "completed", "user_completed"]
    cursor.execute("""SELECT {} FROM mangadex WHERE manga_id = %s""".format(", ".join(parameters), ), [manga_id])
    values = cursor.fetchall()
    if len(values) != 1:
        data = fetch_data(manga_id)
        add_data(*data)
        return get_data(manga_id)
    else:
        data = tuple(values[0])
        return data


def add_data(manga_id: int, title: str, cover_url: str, total: int, completed: bool):
    query = (
        """INSERT INTO mangadex(MANGA_ID, TITLE, COVER_URL, TOTAL, COMPLETED) VALUES (%s, %s, %s, %s, %s)""",
        (manga_id, title, cover_url, total, completed))
    cursor = conn.cursor()
    cursor.execute(*query)


def update_data(manga_id: int,
                title: Optional[str] = None,
                cover_url: Optional[str] = None,
                read: Optional[int] = None,
                total: Optional[int] = None,
                completed: Optional[bool] = None,
                user_completed: Optional[bool] = None):
    if None in (title, cover_url, read, total, completed, user_completed):
        _title, _cover_url, _read, _total, _completed, _user_completed = get_data(manga_id)
    if title is None:
        title = _title
    if cover_url is None:
        cover_url = _cover_url
    if read is None:
        read = _read
    if total is None:
        total = _total
    if completed is None:
        completed = _completed
    if user_completed is None:
        user_completed = _user_completed
    cursor = conn.cursor()
    cursor.execute("""UPDATE mangadex
SET title = %s,
    cover_url = %s,
    read = %s,
    total = %s,
    completed = %s,
    updated = True,
    user_completed = %s
WHERE manga_id = {}""".format(manga_id), [title, cover_url, read, total, completed, user_completed])
    return title, cover_url, read, total, completed, user_completed


def delete_data(manga_id: int):
    cursor = conn.cursor()
    cursor.execute("""DELETE FROM mangadex WHERE manga_id = %s""", (manga_id,))


def get_all(parameters: Optional[Union[List[str], str]] = None, order: str = "manga_id", direction: str = "desc",
            where: Optional[str] = None):
    if parameters == "*" or parameters is None:
        parameters = ["manga_id", "title", "cover_url", "read", "total", "completed", "user_completed"]
    if isinstance(parameters, list):
        parameters = ",".join(parameters)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {parameters} FROM MANGADEX {'WHERE ' + where if where is not None else ''} ORDER BY {order}"
                   f" {direction}, TOTAL ASC, TITLE ASC")
    return cursor.fetchall()


def refresh_manga_data(manga_id: int):
    manga_id, title, cover_url, total, completed = fetch_data(manga_id)
    update_data(manga_id, title=title, cover_url=cover_url, total=total, completed=completed)


def refresh_all():
    cursor = conn.cursor()
    cursor.execute("""UPDATE mangadex SET updated = FALSE""")
    cursor.execute("""SELECT MANGA_ID FROM mangadex""")
    for manga_id, in cursor.fetchall():
        refresh_manga_data(manga_id)


def updated_count() -> Tuple[int, int]:
    cursor = conn.cursor()
    cursor.execute("""SELECT COUNT(*) FROM mangadex""")
    total, = cursor.fetchone()
    cursor.execute("""SELECT COUNT(*) FROM mangadex WHERE updated = TRUE""")
    updated, = cursor.fetchone()
    return updated, total


def auto_complete():
    for manga_id, read, total, completed, user_completed in get_all(["manga_id", "read", "total", "completed",
                                                                     "user_completed"]):
        if read == total and completed:
            update_data(manga_id, user_completed=True)
        if read != total and user_completed:
            update_data(manga_id, user_completed=False)


setup_db()
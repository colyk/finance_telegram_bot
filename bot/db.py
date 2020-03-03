import sqlite3


def get_connection(func):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (username text, api_key text)')
        result = func(conn, *args, **kwargs)
        conn.commit()
        conn.close()
        return result
    return wrapper


@get_connection
def get_user(conn, username: str):
    c = conn.cursor()
    rows = c.execute(
        'SELECT * FROM users WHERE username==? LIMIT 1', (username,)).fetchone()
    if not rows:
        return None
    return rows


@get_connection
def save_user(conn, username: str, api_key: str):
    c = conn.cursor()
    if get_user(username):
        c.execute('UPDATE users SET api_key=? WHERE username=?',
                  (api_key, username))
    else:
        c.execute('INSERT INTO users (username, api_key) VALUES(?, ?)',
                  (username, api_key))

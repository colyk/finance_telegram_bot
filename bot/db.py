import sqlite3


def get_user(username: str):
    c = get_cursor()
    rows = c.execute(
        'SELECT api_key FROM users WHERE username==?', (username,))
    if rows.rowcount != 1:
        return None
    return rows.fetchall()


def save_user(username: str, api_key):
    c = get_cursor()
    c.execute('INSERT INTO users (username, api_key) VALUES(?, ?)',
              (username, api_key))


def get_cursor():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username text, api_key text)')
    return c

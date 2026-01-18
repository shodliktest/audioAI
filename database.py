import sqlite3
from datetime import datetime, date
from config import DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, fullname TEXT, join_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (date TEXT, usage_count INTEGER)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, fullname):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if c.fetchone() is None:
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, username, fullname, join_date))
        conn.commit()
        conn.close()
        return True, join_date
    conn.close()
    return False, None

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users
def update_stats():
    today = str(date.today())
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 1. Bugungi sanaga tegishli qator borligini tekshirish
    c.execute("SELECT usage_count FROM stats WHERE date = ?", (today,))
    result = c.fetchone()
    
    if result:
        # 2. Agar bo'lsa, sonini 1 taga oshirish (so'rov oxirida (today,) bo'lishi shart)
        c.execute("UPDATE stats SET usage_count = usage_count + 1 WHERE date = ?", (today,))
    else:
        # 3. Agar bo'lmasa, yangi qator qo'shish (bu yerda ham (today,) bo'lishi shart)
        c.execute("INSERT INTO stats VALUES (?, 1)", (today,))
        
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = str(date.today())
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT usage_count FROM stats WHERE date = ?", (today,))
    res = c.fetchone()
    today_usage = res[0] if res else 0
    c.execute("SELECT SUM(usage_count) FROM stats")
    total_usage = c.fetchone()[0]
    conn.close()
    return total_users, today_usage, (total_usage if total_usage else 0)


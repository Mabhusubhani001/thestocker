import sqlite3
conn = sqlite3.connect('storage/audit.db')
conn.execute("UPDATE structures SET status = 'closed'")
conn.commit()
print("Stale structures closed!")

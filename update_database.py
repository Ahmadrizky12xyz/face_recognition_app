import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Tambahkan kolom entry_time dan exit_time jika belum ada
c.execute("PRAGMA table_info(employees)")
columns = [col[1] for col in c.fetchall()]
if 'entry_time' not in columns:
    c.execute("ALTER TABLE employees ADD COLUMN entry_time TEXT")
if 'exit_time' not in columns:
    c.execute("ALTER TABLE employees ADD COLUMN exit_time TEXT")

conn.commit()
conn.close()
print("Database diperbarui: kolom entry_time dan exit_time ditambahkan.")
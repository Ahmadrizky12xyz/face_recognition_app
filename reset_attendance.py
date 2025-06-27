import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute("DELETE FROM attendance")
conn.commit()
conn.close()
print("Semua data kehadiran telah direset.")
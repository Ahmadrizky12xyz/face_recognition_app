import sqlite3
import bcrypt

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Hash password
admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
guru_password = bcrypt.hashpw('guru123'.encode('utf-8'), bcrypt.gensalt())

# Insert pengguna
c.execute("INSERT OR REPLACE INTO users (id, username, password, role) VALUES (?, ?, ?, ?)",
          (1, 'admin', admin_password.decode('utf-8'), 'admin'))
c.execute("INSERT OR REPLACE INTO users (id, username, password, role) VALUES (?, ?, ?, ?)",
          (2, 'guru1', guru_password.decode('utf-8'), 'guru'))

conn.commit()
conn.close()
print("Pengguna admin dan guru telah diinisialisasi.")
import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Periksa struktur tabel
print("Struktur Tabel Employees:")
c.execute("PRAGMA table_info(employees)")
print(c.fetchall())

# Periksa data untuk ID 12
print("\nData Tabel Employees (ID 12):")
c.execute("SELECT id, name, photo_path, entry_time, exit_time FROM employees WHERE id = ?", (12,))
data = c.fetchall()
print(data)

# Jika exit_time kosong, perbarui
if data and data[0][3] and not data[0][4]:  # entry_time ada (indeks 3), exit_time None (indeks 4)
    c.execute("UPDATE employees SET exit_time = ? WHERE id = ?", ('16:00', 12))
    conn.commit()
    print("exit_time untuk ID 12 diperbarui ke '16:00'.")

# Periksa ulang data
print("\nData Tabel Employees (ID 12 setelah pembaruan):")
c.execute("SELECT id, name, photo_path, entry_time, exit_time FROM employees WHERE id = ?", (12,))
print(c.fetchall())

conn.close()
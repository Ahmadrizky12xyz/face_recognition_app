import sqlite3
from datetime import datetime

def create_database():
    try:
        # Buat koneksi ke database (ini akan membuat file database.db jika belum ada)
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Buat tabel employees
        c.execute('''CREATE TABLE IF NOT EXISTS employees
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      face_encoding TEXT,
                      photo_path TEXT)''')

        # Buat tabel attendance
        c.execute('''CREATE TABLE IF NOT EXISTS attendance
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      employee_id INTEGER,
                      timestamp TEXT,
                      status TEXT,
                      FOREIGN KEY (employee_id) REFERENCES employees(id))''')

        # Kosongkan tabel untuk memastikan data contoh baru
        c.execute("DELETE FROM employees")
        c.execute("DELETE FROM attendance")

        # Masukkan data contoh ke tabel employees
        example_employees = [
            ('Budi Santoso', str([0.123, -0.456, 0.789] * 43), 'static/uploads/budi.jpg'),  # Simulasi encoding 128 elemen
            ('Ani Wijaya', str([-0.234, 0.567, -0.123] * 43), 'static/uploads/ani.jpg'),
            ('Siti Aminah', str([0.345, -0.678, 0.234] * 43), 'static/uploads/siti.jpg')
        ]
        c.executemany("INSERT INTO employees (name, face_encoding, photo_path) VALUES (?, ?, ?)", example_employees)

        # Masukkan data contoh ke tabel attendance
        example_attendance = [
            (1, '2025-05-20 08:00:00', 'Hadir'),
            (1, '2025-05-20 08:05:00', 'Hadir'),
            (2, '2025-05-20 08:10:00', 'Hadir'),
            (3, '2025-05-20 08:15:00', 'Hadir')
        ]
        c.executemany("INSERT INTO attendance (employee_id, timestamp, status) VALUES (?, ?, ?)", example_attendance)

        # Komit perubahan
        conn.commit()
        print("Database database.db berhasil dibuat dan diisi dengan data contoh!")

        # Tampilkan isi tabel untuk verifikasi
        print("\nIsi Tabel Employees:")
        c.execute("SELECT * FROM employees")
        for row in c.fetchall():
            print(row)

        print("\nIsi Tabel Attendance:")
        c.execute("SELECT * FROM attendance")
        for row in c.fetchall():
            print(row)

    except sqlite3.Error as e:
        print(f"Terjadi kesalahan saat membuat database: {e}")
    
    finally:
        # Tutup koneksi
        conn.close()
        print("\nKoneksi database ditutup.")

if __name__ == "__main__":
    create_database()
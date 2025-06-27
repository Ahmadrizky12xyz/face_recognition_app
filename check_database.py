import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

print("Tabel Employees:")
c.execute("SELECT * FROM employees")
employees = c.fetchall()
for emp in employees:
    print(emp)

print("\nTabel Attendance:")
c.execute("SELECT * FROM attendance")
attendance = c.fetchall()
for att in attendance:
    print(att)

conn.close()
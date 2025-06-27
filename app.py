from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import cv2
import face_recognition
import numpy as np
import psycopg2
from psycopg2 import pool
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
import bcrypt
from functools import wraps
import cloudinary
import cloudinary.uploader
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inisialisasi Flask
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')  # Ambil dari env

# Konfigurasi Cloudinary untuk penyimpanan foto
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Konfigurasi PostgreSQL
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    user=os.getenv('PG_USER'),
    password=os.getenv('PG_PASSWORD'),
    host=os.getenv('PG_HOST'),
    port=os.getenv('PG_PORT', '5432'),
    database=os.getenv('PG_DATABASE')
)

# Inisialisasi database
def init_db():
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            name TEXT,
            face_encoding TEXT,
            photo_url TEXT,
            entry_time TEXT,
            exit_time TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER,
            timestamp TEXT,
            status TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    conn.commit()
    db_pool.putconn(conn)
    logger.info("Database initialized successfully")

init_db()

# Dekorator login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Dekorator admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Akses ditolak. Hanya admin yang dapat mengakses halaman ini.', 'error')
            return redirect(url_for('attendance'))
        return f(*args, **kwargs)
    return decorated_function

# Fungsi untuk kompresi gambar
def compress_image(image_data):
    try:
        img = Image.open(BytesIO(image_data))
        img = img.convert('RGB')
        output = BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return None

# Fungsi mendapatkan face encoding
def get_face_encoding(image_data=None):
    try:
        image = np.array(Image.open(BytesIO(image_data)))
        encodings = face_recognition.face_encodings(image)
        return encodings[0] if encodings else None
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None

# Validasi waktu
def validate_times(entry_time, exit_time):
    try:
        if not entry_time or not exit_time:
            return False, "Jam Masuk dan Jam Pulang harus diisi."
        entry = datetime.strptime(entry_time, '%H:%M')
        exit = datetime.strptime(exit_time, '%H:%M')
        if exit <= entry:
            return False, "Jam Pulang harus lebih besar dari Jam Masuk."
        return True, ""
    except ValueError:
        return False, "Format waktu tidak valid."

# Tentukan status absensi
def determine_attendance_status(current_time, entry_time, exit_time, attendance_type):
    try:
        if not entry_time or not exit_time:
            return "Hadir"
        current = datetime.strptime(current_time, '%H:%M')
        entry = datetime.strptime(entry_time, '%H:%M')
        exit = datetime.strptime(exit_time, '%H:%M')
        if attendance_type == 'entry':
            late_threshold = entry.replace(minute=entry.minute + 30)
            if current <= late_threshold:
                return "Hadir" if current <= entry else "Terlambat"
            else:
                return "Terlambat"
        elif attendance_type == 'exit':
            if current >= exit:
                return "Pulang"
            else:
                return "Pulang Dini"
        else:
            return "Hadir"
    except Exception as e:
        logger.error(f"Error determining status: {e}")
        return "Hadir"

# Route API Riwayat Kehadiran
@app.route('/api/riwayat_kehadiran')
def api_riwayat():
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute('''
        SELECT e.name, a.timestamp, a.status 
        FROM attendance a 
        JOIN employees e ON a.employee_id = e.id
        ORDER BY a.timestamp DESC
    ''')
    data = c.fetchall()
    db_pool.putconn(conn)
    result = [{'nama': row[0], 'waktu': row[1], 'status': row[2]} for row in data]
    return jsonify(result)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username dan password harus diisi.', 'error')
            return redirect(url_for('login'))
        conn = db_pool.getconn()
        c = conn.cursor()
        c.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
        user = c.fetchone()
        db_pool.putconn(conn)
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            flash(f'Selamat datang, {username}!', 'success')
            if user[3] == 'admin':
                return redirect(url_for('index'))
            else:
                return redirect(url_for('attendance'))
        else:
            flash('Username atau password salah.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

# Halaman utama (admin)
@app.route('/')
@login_required
@admin_required
def index():
    return render_template('index.html')

# Pendaftaran karyawan
@app.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        entry_time = request.form.get('entry_time')
        exit_time = request.form.get('exit_time')
        photo = request.files.get('photo')
        if not all([name, entry_time, exit_time, photo]):
            flash('Semua kolom harus diisi!', 'error')
            return redirect(url_for('register'))
        is_valid, error_message = validate_times(entry_time, exit_time)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('register'))
        compressed_photo = compress_image(photo.read())
        if not compressed_photo:
            flash('Gagal memproses foto.', 'error')
            return redirect(url_for('register'))
        upload_result = cloudinary.uploader.upload(
            BytesIO(compressed_photo),
            folder="face_recognition_uploads",
            resource_type="image"
        )
        photo_url = upload_result['secure_url']
        encoding = get_face_encoding(image_data=compressed_photo)
        if encoding is not None:
            conn = db_pool.getconn()
            c = conn.cursor()
            c.execute(
                "INSERT INTO employees (name, face_encoding, photo_url, entry_time, exit_time) VALUES (%s, %s, %s, %s, %s)",
                (name, str(encoding.tolist()), photo_url, entry_time, exit_time)
            )
            conn.commit()
            db_pool.putconn(conn)
            flash('Karyawan berhasil didaftarkan!', 'success')
        else:
            flash('Gagal mendeteksi wajah pada foto.', 'error')
        return redirect(url_for('register'))
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute("SELECT id, name, photo_url, entry_time, exit_time FROM employees")
    employees = c.fetchall()
    db_pool.putconn(conn)
    return render_template('register.html', employees=employees)

# Edit karyawan
@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(id):
    conn = db_pool.getconn()
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        entry_time = request.form.get('entry_time')
        exit_time = request.form.get('exit_time')
        photo = request.files.get('photo')
        c.execute("SELECT name, photo_url, entry_time, exit_time FROM employees WHERE id = %s", (id,))
        old_data = c.fetchone()
        if not all([name, entry_time, exit_time]):
            flash('Semua kolom wajib diisi (kecuali foto).', 'error')
            db_pool.putconn(conn)
            return redirect(url_for('edit_employee', id=id))
        is_valid, error_message = validate_times(entry_time, exit_time)
        if not is_valid:
            flash(error_message, 'error')
            db_pool.putconn(conn)
            return redirect(url_for('edit_employee', id=id))
        if photo and photo.filename:
            compressed_photo = compress_image(photo.read())
            if not compressed_photo:
                flash('Gagal memproses foto baru.', 'error')
                db_pool.putconn(conn)
                return redirect(url_for('edit_employee', id=id))
            upload_result = cloudinary.uploader.upload(
                BytesIO(compressed_photo),
                folder="face_recognition_uploads",
                resource_type="image"
            )
            photo_url = upload_result['secure_url']
            encoding = get_face_encoding(image_data=compressed_photo)
            if encoding is not None:
                c.execute(
                    "UPDATE employees SET name=%s, face_encoding=%s, photo_url=%s, entry_time=%s, exit_time=%s WHERE id=%s",
                    (name, str(encoding.tolist()), photo_url, entry_time, exit_time, id)
                )
            else:
                flash('Gagal 벌
                db_pool.putconn(conn)
                return redirect(url_for('edit_employee', id=id))
        else:
            c.execute(
                "UPDATE employees SET name=%s, entry_time=%s, exit_time=%s WHERE id=%s",
                (name, entry_time, exit_time, id)
            )
        conn.commit()
        db_pool.putconn(conn)
        flash('Data karyawan berhasil diperbarui!', 'success')
        return redirect(url_for('register'))
    c.execute("SELECT id, name, photo_url, entry_time, exit_time FROM employees WHERE id = %s", (id,))
    employee = c.fetchone()
    db_pool.putconn(conn)
    if employee:
        return render_template('edit_employee.html', employee=employee)
    flash('Karyawan tidak ditemukan.', 'error')
    return redirect(url_for('register'))

# Hapus karyawan
@app.route('/delete_employee/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_employee(id):
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute("SELECT photo_url FROM employees WHERE id = %s", (id,))
    photo_url = c.fetchone()
    if photo_url and photo_url[0]:
        public_id = photo_url[0].split('/')[-1].split('.')[0]
        cloudinary.uploader.destroy(f"face_recognition_uploads/{public_id}")
    c.execute("DELETE FROM employees WHERE id = %s", (id,))
    c.execute("DELETE FROM attendance WHERE employee_id = %s", (id,))
    conn.commit()
    db_pool.putconn(conn)
    flash('Karyawan berhasil dihapus!', 'success')
    return redirect(url_for('register'))

# Halaman absensi
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if request.method == 'POST':
        photo = request.files.get('photo')
        attendance_type = request.form.get('attendance_type')
        if not photo:
            flash('Foto diperlukan untuk absensi.', 'error')
            return redirect(url_for('attendance'))
        if attendance_type not in ['entry', 'exit']:
            flash('Jenis absensi tidak valid.', 'error')
            return redirect(url_for('attendance'))
        compressed_photo = compress_image(photo.read())
        if not compressed_photo:
            flash('Gagal memproses foto.', 'error')
            return redirect(url_for('attendance'))
        unknown_encoding = get_face_encoding(image_data=compressed_photo)
        if unknown_encoding is not None:
            unknown_encoding = np.array(unknown_encoding)
            conn = db_pool.getconn()
            c = conn.cursor()
            c.execute("SELECT id, name, face_encoding, entry_time, exit_time FROM employees")
            employees = c.fetchall()
            matched = False
            for emp in employees:
                emp_id, emp_name, emp_encoding_str, entry_time, exit_time = emp
                emp_encoding = np.array(eval(emp_encoding_str))
                results = face_recognition.compare_faces([emp_encoding], unknown_encoding)
                if results[0]:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    current_time = datetime.now().strftime('%H:%M')
                    status = determine_attendance_status(current_time, entry_time, exit_time, attendance_type)
                    c.execute(
                        "INSERT INTO attendance (employee_id, timestamp, status) VALUES (%s, %s, %s)",
                        (emp_id, timestamp, status)
                    )
                    conn.commit()
                    flash(f'Absensi {attendance_type.capitalize()} berhasil untuk {emp_name} ({status})!', 'success')
                    matched = True
                    break
            db_pool.putconn(conn)
            if not matched:
                flash('Wajah tidak dikenali.', 'error')
        else:
            flash('Gagal mendeteksi wajah.', 'error')
        return redirect(url_for('attendance'))
    conn = db_pool.getconn()
    c = conn.cursor()
    if session.get('role') == 'guru' and session.get('employee_id'):
        c.execute(
            "SELECT a.id, e.name, a.timestamp, a.status FROM attendance a JOIN employees e ON a.employee_id = e.id WHERE a.employee_id = %s ORDER BY a.timestamp DESC",
            (session.get('employee_id'),)
        )
    else:
        c.execute("SELECT a.id, e.name, a.timestamp, a.status FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.timestamp DESC")
    records = c.fetchall()
    db_pool.putconn(conn)
    formatted_records = [{'id': r[0], 'name': r[1], 'timestamp': r[2], 'status': r[3]} for r in records]
    return render_template('attendance.html', records=formatted_records)

# Halaman absensi dengan kamera
@app.route('/attendance_with_camera')
@login_required
def attendance_with_camera():
    return render_template('attendance_with_camera.html')

# Laporan kehadiran
@app.route('/report')
@login_required
def report():
    conn = db_pool.getconn()
    c = conn.cursor()
    if session.get('role') == 'guru' and session.get('employee_id'):
        c.execute(
            "SELECT a.id, e.name, a.timestamp, a.status FROM attendance a JOIN employees e ON a.employee_id = e.id WHERE a.employee_id = %s ORDER BY a.timestamp DESC",
            (session.get('employee_id'),)
        )
    else:
        c.execute("SELECT a.id, e.name, a.timestamp, a.status FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.timestamp DESC")
    records = c.fetchall()
    db_pool.putconn(conn)
    formatted_records = [{'id': r[0], 'name': r[1], 'timestamp': r[2], 'status': r[3]} for r in records]
    return render_template('report.html', records=formatted_records)

# Hapus kehadiran individu
@app.route('/delete_attendance/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_attendance(id):
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE id = %s", (id,))
    conn.commit()
    db_pool.putconn(conn)
    flash('Data kehadiran berhasil dihapus!', 'success')
    return redirect(url_for('report'))

# Reset semua kehadiran
@app.route('/reset_attendance', methods=['POST'])
@login_required
@admin_required
def reset_attendance():
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute("DELETE FROM attendance")
    conn.commit()
    db_pool.putconn(conn)
    flash('Semua data kehadiran telah direset!', 'success')
    return redirect(url_for('report'))

# Dapatkan data karyawan untuk pemindaian wajah
@app.route('/get_employees')
@login_required
def get_employees():
    conn = db_pool.getconn()
    c = conn.cursor()
    c.execute("SELECT id, name, face_encoding FROM employees")
    employees = c.fetchall()
    db_pool.putconn(conn)
    employees_data = [
        {'id': emp[0], 'name': emp[1], 'face_encoding': eval(emp[2])}
        for emp in employees
    ]
    return jsonify(employees_data)

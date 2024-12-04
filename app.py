from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuración de MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flaskdb'

mysql = MySQL(app)

@app.route('/')
def home():
    # Verificar si el usuario está en sesión
    if 'user' not in session:
        flash('Por favor, inicia sesión para acceder a esta página.', 'danger')
        return redirect(url_for('login'))  # Redirige al login si no hay sesión
    return render_template('index.html', user=session['user'])  # Pasa el nombre del usuario a la plantilla

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cur.fetchone()
        cur.close()
        

        if user:
            session['user_id'] = user[0]  # Suponiendo que el ID del usuario está en user[0]
            session['user'] = user[1]  # Guardar el nombre del usuario en la sesión
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))  # Redirige a la página principal
        else:
            flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        mysql.connection.commit()
        cur.close()
        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user', None)  # Elimina al usuario de la sesión
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('login'))  # Redirige al login

@app.route('/doctors')
def doctors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()  # Obtén todos los doctores de la base de datos
    cur.close()
    return render_template('doctors.html', doctors=doctors)

@app.route('/reserve/<int:doctor_id>', methods=['GET', 'POST'])
def reserve(doctor_id):
    if 'user' not in session:
        flash('Debes iniciar sesión para reservar una cita.', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()

    # Obtener detalles del doctor
    cur.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
    doctor = cur.fetchone()

    if request.method == 'POST':
        user_id = session['user_id']
        appointment_date = request.form['date']
        appointment_time = request.form['time']

        # Verificar disponibilidad
        cur.execute("""
            SELECT * FROM appointments 
            WHERE doctor_id = %s AND appointment_date = %s AND appointment_time = %s
        """, (doctor_id, appointment_date, appointment_time))
        existing_appointment = cur.fetchone()

        if existing_appointment:
            flash('El doctor no está disponible en esta fecha y hora.', 'danger')
        else:
            # Crear la cita
            cur.execute("""
                INSERT INTO appointments (doctor_id, user_id, appointment_date, appointment_time) 
                VALUES (%s, %s, %s, %s)
            """, (doctor_id, user_id, appointment_date, appointment_time))
            mysql.connection.commit()
            flash('Cita reservada exitosamente.', 'success')
            return redirect(url_for('doctors'))

    cur.close()
    return render_template('reserve.html', doctor=doctor)

@app.route('/my_appointments')
def my_appointments():
    if 'user' not in session:
        flash('Debes iniciar sesión para ver tus citas.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.id, d.name, a.appointment_date, a.appointment_time, a.status 
        FROM appointments a 
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id = %s
    """, (user_id,))
    appointments = cur.fetchall()
    cur.close()

    return render_template('my_appointments.html', appointments=appointments)

@app.route('/appointments')
def appointments():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para ver tu historial de citas.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']  # Obtén el ID del usuario desde la sesión
    cur = mysql.connection.cursor()
    
    # Consulta para obtener citas del usuario con el ID de la cita
    cur.execute("""
        SELECT a.appointment_date, a.appointment_time, a.status, d.name, d.specialty, a.id
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """, (user_id,))
    appointments = cur.fetchall()
    cur.close()

    return render_template('appointments.html', appointments=appointments)

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para realizar esta acción.', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
    mysql.connection.commit()
    cur.close()
    
    flash('La cita ha sido eliminada con éxito.', 'success')
    return redirect(url_for('appointments'))

@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para realizar esta acción.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        # Actualizar la cita
        new_date = request.form['date']
        new_time = request.form['time']
        cur.execute("""
            UPDATE appointments 
            SET appointment_date = %s, appointment_time = %s 
            WHERE id = %s
        """, (new_date, new_time, appointment_id))
        mysql.connection.commit()
        cur.close()
        flash('La cita ha sido modificada con éxito.', 'success')
        return redirect(url_for('appointments'))
    else:
        # Mostrar el formulario de edición con los datos actuales
        cur.execute("SELECT appointment_date, appointment_time FROM appointments WHERE id = %s", (appointment_id,))
        appointment = cur.fetchone()
        cur.close()
        return render_template('edit_appointment.html', appointment=appointment, appointment_id=appointment_id)


if __name__ == '__main__':
    app.run(debug=True)

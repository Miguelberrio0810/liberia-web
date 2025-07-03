import os
from flask import Flask, abort, config, make_response
from flask import render_template, request, redirect, session
from flaskext.mysql import MySQL
from datetime import datetime
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash
from flask import session
from datetime import timedelta
from flask.sessions import SecureCookieSessionInterface




app = Flask(__name__)
app.secret_key="mi_clave_secreta" # Clave para sesiones
mysql = MySQL()
app.permanent_session_lifetime = timedelta(days=1)  # La sesión dura 1 día
app.config.from_object(config)
app.session_interface = SecureCookieSessionInterface()



app.config['MYSQL_DATABASE_HOST']='localhost'
app.config['MYSQL_DATABASE_USER']='root'
app.config['MYSQL_DATABASE_PASSWORD']=''
app.config['MYSQL_DATABASE_DB']='sitio'
mysql.init_app(app)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tu_clave_segura'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 horas


@app.route('/')
def inicio():
    return render_template('sitio/index.html')

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/img/<imagen>')
def imagenes(imagen):
    print(imagen)
    return send_from_directory(os.path.join('templates/sitio/img'),imagen)


@app.route('/css/<archivocss>')
def css_link(archivocss):
    return send_from_directory(os.path.join('templates/sitio/css'),archivocss)

@app.route('/libros')
def libros():


    conexion = mysql.connect()
    cursor= conexion.cursor()
    cursor.execute("SELECT * FROM `libros`")
    libros=cursor.fetchall()
    conexion.commit()
    
    return render_template('sitio/libros.html', libros=libros)

@app.route('/nosotros')
def nosotros():
    return render_template('sitio/nosotros.html')

# Ver detalle del libro
@app.route('/detalle/<int:id>')
def detalle_libro(id):
    conexion = mysql.connect()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM libros WHERE id = %s", (id,))
    libro = cursor.fetchone()
    conexion.commit()

    # Convertir a lista para poder modificar el campo precio
    if libro:
        libro = list(libro)
        try:
            libro[6] = float(libro[6])  # Asumiendo que libro[5] es el campo precio
        except (ValueError, TypeError):
            libro[6] = 0.00

    return render_template('sitio/detalle.html', libro=libro) if libro else redirect('/libros')

# Leer dentro de la página
@app.route('/leer/<int:id_libro>')
def leer_libro(id_libro):
    if 'usuario' not in session:
        flash("Debes iniciar sesión para leer este libro.", "warning")
        return redirect('/loginuser')

    conexion = mysql.connect()
    cursor = conexion.cursor()

    sql = "SELECT id, nombre, imagen, url FROM libros WHERE id = %s"
    cursor.execute(sql, (id_libro,))
    libro = cursor.fetchone()

    return render_template('sitio/leer.html', libro=libro) if libro else redirect('/libros')

# Precio del libro

@app.route('/comprar/<int:id_libro>')
def comprar_libro(id_libro):
    conexion = mysql.connect()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, precio, imagen FROM libros WHERE id = %s", (id_libro,))
    libro = cursor.fetchone()
    
    
    return render_template('sitio/comprar.html', libro=libro)



@app.route('/formulariopago/<int:libro_id>')
def formulariopago(libro_id):
    conexion = mysql.connect()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM libros WHERE id = %s", (libro_id,))
    libro = cursor.fetchone()
    if not libro:
        abort(404)
    return render_template('sitio/formulariopago.html', libro=libro)



# simulacion pago

@app.route('/simular_pago', methods=['POST'])
def simular_pago():
    libro_id = request.form['libro_id']
    valor = request.form['valor']
    nombre = request.form['nombre']
    email = request.form['email']
    estado = "aprobado"  # Puedes alternar entre "aprobado", "rechazado", etc.

    conexion = mysql.connect()
    cursor = conexion.cursor()
    sql = "INSERT INTO pagos (libro_id, nombre, email, valor, estado) VALUES (%s, %s, %s, %s, %s)"
    datos = (libro_id, nombre, email, valor, estado)
    cursor.execute(sql, datos)
    conexion.commit()

    flash("Pago simulado exitosamente. ¡Gracias por tu compra!", "success")
    return redirect('/confirmacionpago')

@app.route('/confirmacionpago')
def confirmacion_pago():
    return render_template('sitio/confirmacionpago.html')


# Descargar libro
@app.route('/descargar/<int:id_libro>')
def descargar_libro(id_libro):
    if 'usuario' not in session:
        flash("Debes iniciar sesión para descargar este libro.", "warning")
        return redirect('/loginuser')

    conexion = mysql.connect()
    cursor = conexion.cursor()

    sql = "SELECT url FROM libros WHERE id = %s"
    cursor.execute(sql, (id_libro,))
    libro = cursor.fetchone()

    return redirect(libro[0]) if libro else redirect('/libros')

# Registro de usuario
@app.route('/registrouser', methods=['GET', 'POST'])
def registrouser():
    if request.method == 'POST':
        _idusuario = request.form.get('txtIdUsuario')
        _nombre = request.form.get('txtNombre')
        _fecha_nacimiento = request.form.get('txtFechaNacimiento')
        _email = request.form.get('txtEmail')
        _contraseña = request.form.get('txtContraseña')
        
        # Encriptar contraseña para mayor seguridad
        _contraseña_hash = generate_password_hash(_contraseña)
        
        # Validar que los datos no estén vacíos
        if not _idusuario or not _nombre or not _fecha_nacimiento or not _email or not _contraseña:
            flash("Todos los campos son obligatorios", "danger")
            return redirect('/registrouser')
        
        # Guardar datos en la base de datos
        sql = "INSERT INTO cliente (idusuario, nombre, fecha_nacimiento, email, contraseña) VALUES (%s, %s, %s, %s, %s)"
        datos = (_idusuario, _nombre, _fecha_nacimiento, _email, _contraseña_hash)

        conexion = mysql.connect()
        cursor = conexion.cursor()
        cursor.execute(sql, datos)
        conexion.commit()
        
        flash("Registro exitoso. ¡Ahora inicia sesión!", "success")
        return redirect('/loginuser')

    # Si es GET, solo renderiza el formulario
    return render_template('sitio/registrouser.html')



# inicio de sesion de usuario

@app.route('/loginuser', methods=['GET', 'POST'])
def loginuser():
    if request.method == 'POST':
        _usuario = request.form.get('txtIdUsuario')
        _contraseña = request.form.get('txtContraseña').strip()

        conexion = mysql.connect()
        cursor = conexion.cursor()
        sql = "SELECT idusuario, nombre, contraseña FROM cliente WHERE idusuario = %s"
        cursor.execute(sql, (_usuario,))
        usuario = cursor.fetchone()

        if usuario:
            print("Usuario encontrado:", usuario)
            print("Cantidad de elementos en la tupla:", len(usuario))
            print("Contraseña ingresada:", _contraseña)
            print("Hash guardado:", usuario[2])
            print("Comparación:", check_password_hash(usuario[2], _contraseña.strip()))
        
        if len(usuario) >= 3:  # Asegurar que existen al menos 3 elementos
            if check_password_hash(usuario[2], _contraseña.strip()):
                session['usuario'] = usuario[1]
                flash("¡Bienvenido, " + usuario[1] + "!", "success")
                return redirect('/libros')
            else:
                flash("Contraseña incorrecta. Intenta de nuevo.", "danger")
        else:
            flash("Usuario no registrado. Regístrate aquí abajo.","warning")
            

        return redirect('/loginuser')

    # Si el método es GET, simplemente renderiza el formulario
    return render_template('sitio/loginuser.html')

@app.route('/verificar_sesion')
def verificar_sesion():
    return f"Usuario en sesión: {session.get('usuario')}"

@app.before_request
def hacer_sesion_permanente():
    session.permanent = True


# inicio de sesion de admin
@app.route('/admin/')
def admin_index():
    if not 'login' in session:
        return redirect("/admin/login")
    return render_template('admin/index.html')

@app.route('/admin/login')
def admin_login():
    return render_template('admin/login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    _usuario=request.form['txtUsuario']
    _password=request.form['txtPassword']
    print(_usuario)
    print(_password)

    if _usuario=="admin" and _password=="admin123.":
        session["login"]=True
        session["usuario"]="Administrador"
        return redirect("/admin")

    return render_template("admin/login.html", mensaje="Acceso Denegado")

@app.route('/admin/cerrar')
def admin_login_cerrar():
    session.clear()
    return render_template('/admin/cerrar.html')

@app.route('/admin/libros')
def admin_libros():
    if not 'login' in session:
        return redirect("/admin/login")
    
    conexion = mysql.connect()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM `libros`")
    libros = cursor.fetchall()
    conexion.commit()

    # Convertir a lista y asegurarse que el precio sea float
    libros = [list(libro) for libro in libros]
    for libro in libros:
        try:
            libro[6] = float(libro[6])
        except (ValueError, TypeError):
            libro[6] = 0.00

    return render_template('admin/libros.html', libros=libros)

# Guardar libro

@app.route('/admin/libros/guardar', methods=['POST'])
def admin_libros_guardar():
    if 'login' not in session:
        return redirect("/admin/login")

    _nombre = request.form['txtNombre']
    _url = request.form['txtURL']
    _archivo = request.files['txtImagen']
    _genero = request.form['txtGenero']
    _descripcion = request.form['txtDescripcion']
    _precio = request.form['txtPrecio']

    try:
        _precio = float(request.form['txtPrecio'].replace(',', '.').strip())
        # _precio = float(_precio_str)
    except (ValueError, TypeError):
        flash("El precio ingresado no es válido.", "danger")
        return redirect("/admin/libros")

    tiempo = datetime.now()
    horaActual = tiempo.strftime('%Y%H%M%S')

    nuevoNombre = ""
    if _archivo.filename != "":
        nuevoNombre = horaActual + "_" + _archivo.filename
        _archivo.save("templates/sitio/img/" + nuevoNombre)
        
        
        print("Precio recibido desde el formulario:", _precio)


    
    sql = "INSERT INTO `libros` (`id`, `nombre`, `imagen`, `url`, `genero`, `descripcion`, `precio`) VALUES (NULL, %s, %s, %s, %s, %s, %s)"
    datos = (_nombre, nuevoNombre, _url, _genero, _descripcion, _precio)

    conexion = mysql.connect()
    cursor = conexion.cursor()
    cursor.execute(sql, datos)
    conexion.commit()

    return redirect('/admin/libros')


@app.route("/admin/libros/borrar", methods=['POST'])
def admin_libros_borrar():
    
    if not 'login' in session:
        return redirect("/admin/login")

    _id=request.form['txtID']
    print(_id)

    conexion = mysql.connect()
    cursor= conexion.cursor()
    cursor.execute("SELECT imagen FROM `libros` WHERE id=%s",(_id))
    libro=cursor.fetchall()
    conexion.commit()
    print(libro)

    if os.path.exists("templates/sitio/img/"+str(libro[0][0])):
        os.unlink("templates/sitio/img/"+str(libro[0][0]))



    conexion=mysql.connect()
    cursor= conexion.cursor()
    cursor.execute("DELETE FROM libros WHERE id=%s",(_id))
    conexion.commit()



    return redirect('/admin/libros')

if __name__ == '__main__':
    app.run(debug=True)
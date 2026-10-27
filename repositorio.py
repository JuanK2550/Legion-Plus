"""Todas las consultas SQL del proyecto, una función por consulta."""

import hashlib
import hmac
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from config import SAL_LEGADA
from database import get_db


def cifrar_clave(clave):
    """La clave del perfil nunca se guarda tal cual (hash con sal, scrypt)."""
    if not clave:
        return None
    return generate_password_hash(clave)


def _verificar(guardada, clave):
    """Devuelve (es_correcta, hay_que_migrar_al_hash_nuevo)."""
    if not isinstance(clave, str):
        return False, False
    if len(guardada) == 64 and ':' not in guardada:  # SHA-256 antiguo
        if not SAL_LEGADA:  # sin la sal vieja en el .env no se puede comprobar
            return False, False
        viejo = hashlib.sha256((SAL_LEGADA + clave).encode('utf-8')).hexdigest()
        correcta = hmac.compare_digest(guardada, viejo)
        return correcta, correcta
    return check_password_hash(guardada, clave), False


def _sin_clave(fila):
    """Fuera la clave: a la página solo le interesa si el perfil tiene una."""
    perfil = dict(fila)
    perfil['tiene_clave'] = bool(perfil.pop('clave', None))
    return perfil


# El orden de estos valores debe coincidir con el de los ? del INSERT.
def _valores(datos):
    return (datos.get('titulo'), datos.get('director'), datos.get('genero'),
            datos.get('anio'), datos.get('calificacion') or 0, datos.get('sinopsis'),
            datos.get('poster_url'), datos.get('estado') or 'disponible',
            datos.get('fecha_estreno'), datos.get('plataformas'),
            datos.get('trailer_url'), datos.get('fondo_url'))


def listar_peliculas():
    conn = get_db()
    try:
        filas = conn.execute('SELECT * FROM peliculas ORDER BY id').fetchall()
        return [dict(fila) for fila in filas]
    finally:
        conn.close()


def obtener_pelicula(pelicula_id):
    conn = get_db()
    try:
        fila = conn.execute('SELECT * FROM peliculas WHERE id = ?',
                            (pelicula_id,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def crear_pelicula(datos):
    conn = get_db()
    try:
        cur = conn.execute(
            '''INSERT INTO peliculas (titulo, director, genero, anio, calificacion,
               sinopsis, poster_url, estado, fecha_estreno, plataformas, trailer_url, fondo_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            _valores(datos))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def actualizar_pelicula(pelicula_id, datos):
    conn = get_db()
    try:
        conn.execute(
            '''UPDATE peliculas SET titulo = ?, director = ?, genero = ?,
               anio = ?, calificacion = ?, sinopsis = ?, poster_url = ?,
               estado = ?, fecha_estreno = ?, plataformas = ?, trailer_url = ?, fondo_url = ?
               WHERE id = ?''',
            _valores(datos) + (pelicula_id,))
        conn.commit()
    finally:
        conn.close()


def eliminar_pelicula(pelicula_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM vistas WHERE pelicula_id = ?', (pelicula_id,))
        conn.execute('DELETE FROM peliculas WHERE id = ?', (pelicula_id,))
        conn.commit()
    finally:
        conn.close()


def listar_perfiles(usuario_id):
    """Solo los perfiles de esa cuenta."""
    conn = get_db()
    try:
        filas = conn.execute('SELECT * FROM perfiles WHERE usuario_id = ? ORDER BY id',
                             (usuario_id,)).fetchall()
        return [_sin_clave(fila) for fila in filas]
    finally:
        conn.close()


def obtener_perfil(perfil_id):
    conn = get_db()
    try:
        fila = conn.execute('SELECT * FROM perfiles WHERE id = ?',
                            (perfil_id,)).fetchone()
        return _sin_clave(fila) if fila else None
    finally:
        conn.close()


def crear_perfil(datos):
    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO perfiles (usuario_id, nombre, avatar, clave) VALUES (?, ?, ?, ?)',
            (datos.get('usuario_id'), datos.get('nombre', '').strip(),
             datos.get('avatar'), cifrar_clave(datos.get('clave'))))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def eliminar_perfil(perfil_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM vistas WHERE perfil_id = ?', (perfil_id,))
        conn.execute('DELETE FROM perfiles WHERE id = ?', (perfil_id,))
        conn.commit()
    finally:
        conn.close()


def listar_vistas(perfil_id):
    """Devuelve {pelicula_id: estado} con todo lo que marcó un perfil."""
    conn = get_db()
    try:
        filas = conn.execute(
            'SELECT pelicula_id, estado FROM vistas WHERE perfil_id = ?',
            (perfil_id,)).fetchall()
        return {str(f['pelicula_id']): f['estado'] for f in filas}
    finally:
        conn.close()


def marcar_vista(perfil_id, pelicula_id, estado):
    conn = get_db()
    try:
        conn.execute(
            '''INSERT INTO vistas (perfil_id, pelicula_id, estado) VALUES (?, ?, ?)
               ON CONFLICT (perfil_id, pelicula_id) DO UPDATE SET estado = ?''',
            (perfil_id, pelicula_id, estado, estado))
        conn.commit()
    finally:
        conn.close()


def borrar_vista(perfil_id, pelicula_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM vistas WHERE perfil_id = ? AND pelicula_id = ?',
                     (perfil_id, pelicula_id))
        conn.commit()
    finally:
        conn.close()


def actualizar_perfil(perfil_id, datos):
    conn = get_db()
    try:
        conn.execute(
            'UPDATE perfiles SET nombre = ?, avatar = ?, clave = ? WHERE id = ?',
            (datos.get('nombre', '').strip(), datos.get('avatar'),
             cifrar_clave(datos.get('clave')), perfil_id))
        conn.commit()
    finally:
        conn.close()


def clave_correcta(perfil_id, clave):
    conn = get_db()
    try:
        fila = conn.execute('SELECT clave FROM perfiles WHERE id = ?',
                            (perfil_id,)).fetchone()
        if fila is None or not fila['clave']:
            return True
        correcta, migrar = _verificar(fila['clave'], clave)
        if correcta and migrar:
            conn.execute('UPDATE perfiles SET clave = ? WHERE id = ?',
                         (cifrar_clave(clave), perfil_id))
            conn.commit()
        return correcta
    finally:
        conn.close()


def pelicula_por_titulo(titulo):
    conn = get_db()
    try:
        fila = conn.execute('SELECT * FROM peliculas WHERE titulo = ?',
                            (titulo,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def usuario_por_nombre(username):
    """Devuelve la cuenta con su hash, para comprobar la contraseña."""
    conn = get_db()
    try:
        fila = conn.execute('SELECT * FROM usuarios WHERE username = ?',
                            (username,)).fetchone()
        return dict(fila) if fila else None
    finally:
        conn.close()


def crear_usuario(username, clave, rol='usuario'):
    """Crea una cuenta. Devuelve su id, o None si el nombre ya existe."""
    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO usuarios (username, clave, rol) VALUES (?, ?, ?)',
            (username, generate_password_hash(clave), rol))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def clave_de_usuario_correcta(usuario, clave):
    """Compara la contraseña contra el hash guardado."""
    if not isinstance(clave, str) or not usuario:
        return False
    return check_password_hash(usuario['clave'], clave)


def asegurar_admin(username, hash_clave):
    """Deja la cuenta de administrador del .env lista en la base."""
    if not username or not hash_clave:
        return
    conn = get_db()
    try:
        fila = conn.execute('SELECT id FROM usuarios WHERE username = ?',
                            (username,)).fetchone()
        if fila:
            conn.execute("UPDATE usuarios SET clave = ?, rol = 'admin' WHERE id = ?",
                         (hash_clave, fila['id']))
        else:
            conn.execute(
                "INSERT INTO usuarios (username, clave, rol) VALUES (?, ?, 'admin')",
                (username, hash_clave))
        # Los perfiles creados antes de que existieran las cuentas pasan al admin.
        admin = conn.execute('SELECT id FROM usuarios WHERE username = ?',
                             (username,)).fetchone()
        conn.execute('UPDATE perfiles SET usuario_id = ? WHERE usuario_id IS NULL',
                     (admin['id'],))
        conn.commit()
    finally:
        conn.close()

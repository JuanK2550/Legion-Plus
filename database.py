"""Conexión a SQLite y creación de las cuatro tablas."""

import re
import sqlite3

from config import DB_NAME

COLUMNAS_NUEVAS = {
    'estado': "TEXT NOT NULL DEFAULT 'disponible'",
    'fecha_estreno': 'TEXT',
    'plataformas': 'TEXT',
    'trailer_url': 'TEXT',
    'fondo_url': 'TEXT',
}


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def _nombre_seguro(texto):
    """SQLite no admite parámetros para nombres de tabla o columna.

    Estos nombres salen siempre de constantes de este archivo, nunca del
    usuario, pero se comprueban igual antes de meterlos en la consulta.
    """
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', texto):
        raise ValueError('Nombre no válido para la base de datos: %r' % texto)
    return texto


def _agregar_columna(conn, tabla, nombre, tipo):
    tabla, nombre = _nombre_seguro(tabla), _nombre_seguro(nombre)
    actuales = {fila['name'] for fila in conn.execute('PRAGMA table_info(%s)' % tabla)}
    if nombre not in actuales:
        conn.execute('ALTER TABLE %s ADD COLUMN %s %s' % (tabla, nombre, tipo))


def _agregar_columnas_faltantes(conn):
    """Actualiza tablas creadas antes de que existieran estas columnas."""
    for nombre, tipo in COLUMNAS_NUEVAS.items():
        _agregar_columna(conn, 'peliculas', nombre, tipo)


def _tabla_peliculas(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS peliculas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        director TEXT NOT NULL,
        genero TEXT NOT NULL,
        anio INTEGER NOT NULL,
        calificacion REAL NOT NULL,
        sinopsis TEXT,
        poster_url TEXT,
        estado TEXT NOT NULL DEFAULT 'disponible',
        fecha_estreno TEXT,
        plataformas TEXT,
        trailer_url TEXT,
        fondo_url TEXT
    )''')
    _agregar_columnas_faltantes(conn)


def _tabla_usuarios(conn):
    """Las cuentas. El rol decide quién puede administrar la cartelera."""
    conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        clave TEXT NOT NULL,
        rol TEXT NOT NULL DEFAULT 'usuario'
    )''')


def _tabla_perfiles(conn):
    """Cada cuenta tiene sus propios perfiles, como en una plataforma real."""
    conn.execute('''CREATE TABLE IF NOT EXISTS perfiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        nombre TEXT NOT NULL,
        avatar TEXT NOT NULL,
        clave TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )''')
    _agregar_columna(conn, 'perfiles', 'clave', 'TEXT')
    _agregar_columna(conn, 'perfiles', 'usuario_id', 'INTEGER')


def _tabla_vistas(conn):
    """Lo que cada perfil marcó sobre una película: vista, viendo o no_interesa."""
    conn.execute('''CREATE TABLE IF NOT EXISTS vistas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        perfil_id INTEGER NOT NULL,
        pelicula_id INTEGER NOT NULL,
        estado TEXT NOT NULL,
        UNIQUE (perfil_id, pelicula_id),
        FOREIGN KEY (perfil_id) REFERENCES perfiles (id),
        FOREIGN KEY (pelicula_id) REFERENCES peliculas (id)
    )''')


def init_db():
    conn = get_db()
    try:
        _tabla_peliculas(conn)
        _tabla_usuarios(conn)
        _tabla_perfiles(conn)
        _tabla_vistas(conn)
        conn.commit()
    finally:
        conn.close()

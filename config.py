"""Ajustes del proyecto.

Los secretos ya NO viven en el código: se leen de variables de entorno o de un
archivo `.env` (que está en .gitignore y nunca se sube a GitHub).
Copia `.env.example` a `.env` y rellénalo.
"""

import os
import secrets
import sys

from werkzeug.security import generate_password_hash


def _cargar_env(ruta='.env'):
    """Lector mínimo de .env (CLAVE=valor). No pisa variables ya definidas."""
    if not os.path.isfile(ruta):
        return
    with open(ruta, encoding='utf-8') as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            nombre, valor = linea.split('=', 1)
            os.environ.setdefault(nombre.strip(), valor.strip().strip('"\''))


_cargar_env()

# Firma los tokens JWT. Si no se define, se genera una al azar (los tokens
# dejan de valer cada vez que se reinicia el servidor).
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print('AVISO: SECRET_KEY no está definida; se usa una temporal.', file=sys.stderr)

DB_NAME = os.environ.get('DB_NAME', 'peliculas.db')

# Sal del esquema anterior (SHA-256), solo para reconocer claves ya guardadas
# y migrarlas al entrar. Si se deja vacía, esas claves dejan de aceptarse.
SAL_LEGADA = os.environ.get('SAL_LEGADA', '')
MINUTOS_EXPIRACION_TOKEN = int(os.environ.get('MINUTOS_EXPIRACION_TOKEN', '60'))
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')

# Administrador: usuario + contraseña (o directamente su hash).
ADMIN_USER = os.environ.get('ADMIN_USER', '')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')  # solo para verificar.py
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH') or (
    generate_password_hash(ADMIN_PASSWORD) if ADMIN_PASSWORD else '')

if not ADMIN_USER or not ADMIN_PASSWORD_HASH:
    sys.exit('Falta ADMIN_USER y ADMIN_PASSWORD en el entorno o en .env '
             '(mira .env.example).')

# Límite de intentos fallidos (login y claves de perfil).
MAX_INTENTOS = int(os.environ.get('MAX_INTENTOS', '5'))
SEGUNDOS_BLOQUEO = int(os.environ.get('SEGUNDOS_BLOQUEO', '300'))

DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

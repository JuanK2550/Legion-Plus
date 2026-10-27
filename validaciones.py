"""Reglas que deben cumplir los datos antes de guardarse."""

import re
from datetime import datetime
from urllib.parse import urlparse

import avatares

GENEROS = ['Acción', 'Animación', 'Ciencia ficción', 'Comedia', 'Drama',
           'Romance', 'Terror']
ESTADOS = ['disponible', 'proximamente']
DOMINIOS_TRAILER = ('youtube.com', 'youtu.be')
ANIO_MINIMO = 1888
ANIOS_DE_ADELANTO = 10
ESTADOS_VISTA = ['vista', 'viendo', 'no_interesa']
LARGO_CLAVE = 4
LARGO_MINIMO_PASSWORD = 8
LARGO_MAXIMO_USERNAME = 30


def es_proximamente(datos):
    return datos.get('estado') == 'proximamente'


def _anio_maximo(datos):
    """Un estreno futuro puede tener un año que todavía no llega."""
    actual = datetime.now().year
    return actual + ANIOS_DE_ADELANTO if es_proximamente(datos) else actual




def validar_usuario(datos):
    """Reglas para registrar una cuenta nueva."""
    if not isinstance(datos, dict):
        return 'Se esperaba un objeto JSON con username y password'
    error = _validar_texto(datos, 'username')
    if error:
        return error
    username = datos['username'].strip()
    if len(username) > LARGO_MAXIMO_USERNAME:
        return f'El campo "username" no puede pasar de {LARGO_MAXIMO_USERNAME} caracteres'
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', username):
        return 'El campo "username" solo admite letras, números, punto, guion y guion bajo'
    password = datos.get('password')
    if not isinstance(password, str) or len(password) < LARGO_MINIMO_PASSWORD:
        return f'El campo "password" debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres'
    if len(password) > 200:
        return 'El campo "password" no puede pasar de 200 caracteres'
    return None


def validar_perfil(datos):
    """Devuelve un mensaje de error o None si el perfil es válido."""
    if not isinstance(datos, dict):
        return 'Se esperaba un objeto JSON con los datos del perfil'
    error = _validar_texto(datos, 'nombre')
    if error:
        return error
    if len(datos['nombre'].strip()) > 20:
        return 'El campo "nombre" no puede pasar de 20 caracteres'
    if not avatares.existe(datos.get('avatar')):
        return 'El campo "avatar" no está en la galería'
    return _validar_clave(datos.get('clave'))


def _validar_clave(clave):
    """La clave es opcional, pero si viene son 4 dígitos."""
    if clave in (None, ''):
        return None
    if not isinstance(clave, str) or not clave.isdigit() or len(clave) != LARGO_CLAVE:
        return f'El campo "clave" debe tener {LARGO_CLAVE} dígitos'
    return None


def validar_estado_vista(datos):
    """Comprueba la marca que un perfil le pone a una película."""
    if not isinstance(datos, dict):
        return 'Se esperaba un objeto JSON con el campo "estado"'
    if datos.get('estado') not in ESTADOS_VISTA:
        return 'El campo "estado" debe ser uno de: ' + ', '.join(ESTADOS_VISTA)
    return None


def _validar_texto(datos, campo):
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        return f'El campo "{campo}" debe ser un texto no vacío'
    return None


def _validar_anio(datos):
    anio = datos.get('anio')
    if isinstance(anio, bool) or not isinstance(anio, int):
        return 'El campo "anio" debe ser un número entero'
    maximo = _anio_maximo(datos)
    if not ANIO_MINIMO <= anio <= maximo:
        return f'El campo "anio" debe estar entre {ANIO_MINIMO} y {maximo}'
    return None


def _validar_calificacion(datos):
    calificacion = datos.get('calificacion')
    if calificacion is None and es_proximamente(datos):
        return None
    if isinstance(calificacion, bool) or not isinstance(calificacion, (int, float)):
        return 'El campo "calificacion" debe ser un número'
    if not 0 <= calificacion <= 10:
        return 'El campo "calificacion" debe estar entre 0 y 10'
    return None


def _validar_genero(datos):
    error = _validar_texto(datos, 'genero')
    if error:
        return error
    if datos['genero'] not in GENEROS:
        return 'El campo "genero" debe ser uno de: ' + ', '.join(GENEROS)
    return None


def _validar_estado(datos):
    estado = datos.get('estado')
    if estado is None:
        return None
    if estado not in ESTADOS:
        return 'El campo "estado" debe ser uno de: ' + ', '.join(ESTADOS)
    if estado == 'proximamente' and not datos.get('fecha_estreno'):
        return 'Un estreno próximo necesita el campo "fecha_estreno"'
    return None


def _validar_opcionales(datos):
    for campo in ('sinopsis', 'poster_url', 'fecha_estreno', 'plataformas',
                  'trailer_url', 'fondo_url'):
        if datos.get(campo) is not None and not isinstance(datos[campo], str):
            return f'El campo "{campo}" debe ser un texto'
    for campo in ('poster_url', 'fondo_url'):
        enlace = datos.get(campo)
        if enlace and not enlace.startswith(('http://', 'https://')):
            return f'El campo "{campo}" debe empezar por http:// o https://'
    trailer_url = datos.get('trailer_url')
    if trailer_url:
        host = (urlparse(trailer_url).hostname or '').lower()
        if not any(host == d or host.endswith('.' + d) for d in DOMINIOS_TRAILER):
            return 'El campo "trailer_url" debe ser un enlace de YouTube'
    for campo, maximo in (('sinopsis', 5000), ('poster_url', 500),
                          ('fondo_url', 500), ('trailer_url', 500),
                          ('plataformas', 500), ('fecha_estreno', 50)):
        if len(datos.get(campo) or '') > maximo:
            return f'El campo "{campo}" no puede pasar de {maximo} caracteres'
    return None


def _obligatorios(datos):
    campos = ['titulo', 'director', 'genero', 'anio']
    if not es_proximamente(datos):
        campos.append('calificacion')
    return campos


# Devuelve el primer error que encuentra, o None si todo está bien.
def validar_pelicula(datos):
    """Devuelve un mensaje de error o None si la película es válida."""
    if not isinstance(datos, dict):
        return 'Se esperaba un objeto JSON con los datos de la película'
    for campo in _obligatorios(datos):
        if datos.get(campo) is None:
            return f'El campo "{campo}" es obligatorio'
    for validacion in (_validar_estado, _validar_anio, _validar_calificacion,
                       _validar_genero, _validar_opcionales):
        error = validacion(datos)
        if error:
            return error
    for campo in ('titulo', 'director'):
        error = _validar_texto(datos, campo)
        if error:
            return error
        if len(datos[campo]) > 200:
            return f'El campo "{campo}" no puede pasar de 200 caracteres'
    return None

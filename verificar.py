"""Recorrido completo de la API de Legión+.

Comprueba el login, las cinco operaciones, los perfiles, los errores HTTP y
que los datos se conserven. Se ejecuta con el servidor encendido:

    python verificar.py
"""
import json
import random
import sqlite3
import urllib.error
import urllib.request

from config import ADMIN_PASSWORD, ADMIN_USER, DB_NAME

BASE = 'http://127.0.0.1:5000'
USUARIO, CLAVE = ADMIN_USER, ADMIN_PASSWORD
NAVEGADOR = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}

correctas, fallidas = [], []


def comprobar(nombre, condicion, detalle=''):
    (correctas if condicion else fallidas).append((nombre, detalle))
    print('  %s %-52s %s' % ('[ok] ' if condicion else '[FALLA]', nombre, detalle))


def pedir(ruta, datos=None, metodo='GET', token=None, cabeceras=None):
    cuerpo = json.dumps(datos).encode('utf-8') if datos is not None else None
    peticion = urllib.request.Request(BASE + ruta, data=cuerpo, method=metodo)
    if cuerpo:
        peticion.add_header('Content-Type', 'application/json')
    if token:
        peticion.add_header('Authorization', 'Bearer ' + token)
    for nombre, valor in (cabeceras or {}).items():
        peticion.add_header(nombre, valor)
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            return respuesta.status, respuesta.read().decode('utf-8'), respuesta.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode('utf-8'), error.headers
    except urllib.error.URLError:
        return 0, '', {}


def json_de(texto):
    try:
        return json.loads(texto)
    except ValueError:
        return {}


print('\nLEGION+  ·  verificacion de la API\n' + '=' * 62)

estado, cuerpo, _ = pedir('/')
if estado == 0:
    print('\nEl servidor no responde. Arrancalo con:  python app.py\n')
    raise SystemExit(1)

print('\n1. SESION CON JWT')
estado, cuerpo, _ = pedir('/login', {'username': USUARIO, 'password': CLAVE}, 'POST')
token = json_de(cuerpo).get('token', '')
comprobar('POST /login devuelve un token', estado == 200 and token.count('.') == 2, str(estado))
estado, cuerpo, _ = pedir('/login', {'username': USUARIO, 'password': 'mala'}, 'POST')
comprobar('contrasena incorrecta da 401', estado == 401, json_de(cuerpo).get('error', ''))

estado, _, _ = pedir('/sesion', token=token)
comprobar('GET /sesion acepta un token valido', estado == 200, str(estado))
estado, cuerpo, _ = pedir('/sesion', token='token.inventado.aqui')
comprobar('GET /sesion rechaza un token falso', estado == 401, json_de(cuerpo).get('error', ''))
estado, _, _ = pedir('/sesion')
comprobar('GET /sesion sin token da 401', estado == 401, str(estado))

print('\n2. LAS CINCO OPERACIONES')
estado, cuerpo, _ = pedir('/peliculas')
lista = json_de(cuerpo)
comprobar('GET /peliculas lista todas', estado == 200 and isinstance(lista, list),
          '%d peliculas' % len(lista))

nueva = {'titulo': 'Pelicula de verificacion', 'director': 'Equipo Legion',
         'genero': 'Drama', 'anio': 2024, 'calificacion': 7.5,
         'sinopsis': 'Registro creado por verificar.py.'}
estado, cuerpo, _ = pedir('/peliculas', nueva, 'POST', token)
creada = json_de(cuerpo)
comprobar('POST /peliculas crea (201)', estado == 201 and 'id' in creada, str(estado))

estado, cuerpo, _ = pedir('/peliculas/%s' % creada.get('id'))
comprobar('GET /peliculas/<id> consulta una', estado == 200, str(estado))

cambiada = dict(nueva, titulo='Pelicula de verificacion (editada)', calificacion=9.3)
estado, cuerpo, _ = pedir('/peliculas/%s' % creada.get('id'), cambiada, 'PUT', token)
comprobar('PUT /peliculas/<id> actualiza',
          estado == 200 and json_de(cuerpo).get('calificacion') == 9.3, str(estado))

otra = dict(nueva, titulo='Pelicula que se elimina')
_, cuerpo, _ = pedir('/peliculas', otra, 'POST', token)
borrable = json_de(cuerpo)
estado, _, _ = pedir('/peliculas/%s' % borrable.get('id'), None, 'DELETE', token)
comprobar('DELETE /peliculas/<id> elimina', estado == 200, str(estado))
estado, _, _ = pedir('/peliculas/%s' % borrable.get('id'))
comprobar('la eliminada ya no aparece', estado == 404, str(estado))
estado, cuerpo, _ = pedir('/peliculas/%s' % creada.get('id'))
comprobar('la otra sigue guardada con su cambio',
          estado == 200 and json_de(cuerpo).get('calificacion') == 9.3, str(estado))

print('\n3. EL TOKEN ES OBLIGATORIO')
for metodo, ruta, datos in (('POST', '/peliculas', nueva),
                            ('PUT', '/peliculas/%s' % creada.get('id'), nueva),
                            ('DELETE', '/peliculas/%s' % creada.get('id'), None)):
    estado, cuerpo, _ = pedir(ruta, datos, metodo)
    comprobar('%s sin token da 401' % metodo, estado == 401, json_de(cuerpo).get('error', ''))
estado, cuerpo, _ = pedir('/peliculas', nueva, 'POST', 'token.falso.roto')
comprobar('token invalido da 401', estado == 401, json_de(cuerpo).get('error', ''))

print('\n4. VALIDACIONES')
casos = [
    ('falta un campo obligatorio', {k: v for k, v in nueva.items() if k != 'calificacion'}),
    ('tipo de dato incorrecto', dict(nueva, anio='dos mil')),
    ('calificacion fuera de 0 a 10', dict(nueva, calificacion=11)),
    ('ano fuera de 1888 al actual', dict(nueva, anio=1500)),
    ('genero que no existe', dict(nueva, genero='Musical')),
    ('estado que no existe', dict(nueva, estado='otro')),
    ('poster que no es un enlace', dict(nueva, poster_url='ftp://x')),
    ('trailer que no es de YouTube', dict(nueva, trailer_url='https://vimeo.com/1')),
]
for nombre, datos in casos:
    estado, cuerpo, _ = pedir('/peliculas', datos, 'POST', token)
    comprobar('400 por %s' % nombre, estado == 400, json_de(cuerpo).get('error', ''))

print('\n5. ERRORES HTTP EN JSON')
pruebas_error = [
    ('400 cuerpo sin JSON', '/peliculas', 'POST', 400),
    ('401 ruta protegida sin token', '/peliculas', 'POST', 401),
    ('404 pelicula inexistente', '/peliculas/999999', 'GET', 404),
    ('404 ruta inexistente', '/no-existe', 'GET', 404),
    ('405 metodo no permitido', '/login', 'GET', 405),
]
for nombre, ruta, metodo, esperado in pruebas_error:
    usar = token if esperado == 400 else None
    estado, cuerpo, cabeceras = pedir(ruta, None, metodo, usar)
    datos = json_de(cuerpo)
    comprobar(nombre, estado == esperado and 'error' in datos,
              '%s %s' % (estado, datos.get('error', '')[:34]))

print('\n6. LOS MISMOS ERRORES COMO PAGINA, PARA EL NAVEGADOR')
for nombre, ruta, esperado in (('404 ruta inexistente', '/no-existe', 404),
                               ('404 pelicula inexistente', '/peliculas/999999', 404),
                               ('405 metodo no permitido', '/login', 405)):
    estado, cuerpo, cabeceras = pedir(ruta, cabeceras=NAVEGADOR)
    es_html = 'text/html' in cabeceras.get('Content-Type', '')
    comprobar('%s se ve como pagina' % nombre,
              estado == esperado and es_html and 'error-codigo' in cuerpo, str(estado))

print('\n7. CUENTAS Y ROLES')
nombre_prueba = 'verificacion%d' % random.randint(1000, 9999)
estado, cuerpo, _ = pedir('/registro', {'username': nombre_prueba,
                                        'password': 'clave-de-prueba-1'}, 'POST')
registro = json_de(cuerpo)
token_usuario = registro.get('token', '')
comprobar('POST /registro crea una cuenta', estado == 201, str(estado))
comprobar('la cuenta nueva nace con rol usuario',
          registro.get('usuario', {}).get('rol') == 'usuario',
          str(registro.get('usuario', {}).get('rol')))
estado, cuerpo, _ = pedir('/registro', {'username': nombre_prueba,
                                        'password': 'clave-de-prueba-1'}, 'POST')
comprobar('no deja repetir el nombre de usuario', estado == 409,
          json_de(cuerpo).get('error', ''))
estado, cuerpo, _ = pedir('/registro', {'username': nombre_prueba + 'x',
                                        'password': '123'}, 'POST')
comprobar('rechaza una contrasena corta', estado == 400,
          json_de(cuerpo).get('error', '')[:40])
estado, cuerpo, _ = pedir('/sesion', token=token_usuario)
comprobar('/sesion informa el rol', json_de(cuerpo).get('rol') == 'usuario',
          str(json_de(cuerpo).get('rol')))

estado, cuerpo, _ = pedir('/peliculas', nueva, 'POST', token_usuario)
comprobar('un usuario no puede crear peliculas', estado == 403,
          json_de(cuerpo).get('error', ''))
estado, _, _ = pedir('/peliculas/%s' % creada.get('id'), None, 'DELETE', token_usuario)
comprobar('un usuario no puede borrar peliculas', estado == 403, str(estado))
estado, _, _ = pedir('/sincronizar', {}, 'POST', token_usuario)
comprobar('un usuario no puede sincronizar', estado == 403, str(estado))
estado, cuerpo, _ = pedir('/perfiles', token=token)
comprobar('el admin SI puede tener perfiles', estado == 200, str(estado))
estado, cuerpo, _ = pedir('/perfiles/1/vistas', token=token)
comprobar('el admin NO lleva lista de vistas', estado == 403,
          json_de(cuerpo).get('error', ''))

print('\n8. PERFILES Y MI LISTA')
estado, cuerpo, _ = pedir('/avatares')
galeria = json_de(cuerpo)
comprobar('GET /avatares trae la galeria', estado == 200 and len(galeria) > 0,
          '%d avatares' % len(galeria))

estado, cuerpo, _ = pedir('/perfiles', token=token_usuario)
comprobar('una cuenta nueva arranca sin perfiles',
          estado == 200 and json_de(cuerpo) == [], cuerpo[:30])

perfil = {'nombre': 'Verificacion', 'avatar': galeria[0]['id'], 'clave': '1234'}
estado, cuerpo, _ = pedir('/perfiles', perfil, 'POST', token_usuario)
nuevo_perfil = json_de(cuerpo)
comprobar('POST /perfiles crea un perfil', estado == 201, str(estado))
comprobar('la clave nunca se devuelve',
          'clave' not in nuevo_perfil and nuevo_perfil.get('tiene_clave') is True,
          str(sorted(nuevo_perfil.keys())))

estado, cuerpo, _ = pedir('/perfiles/%s/entrar' % nuevo_perfil.get('id'),
                          {'clave': '0000'}, 'POST', token_usuario)
comprobar('clave incorrecta da 401', estado == 401, json_de(cuerpo).get('error', ''))
estado, _, _ = pedir('/perfiles/%s/entrar' % nuevo_perfil.get('id'),
                     {'clave': '1234'}, 'POST', token_usuario)
comprobar('clave correcta deja entrar', estado == 200, str(estado))

estado, _, _ = pedir('/perfiles/%s/vistas/%s' % (nuevo_perfil.get('id'), creada.get('id')),
                     {'estado': 'viendo'}, 'PUT', token_usuario)
comprobar('se marca una pelicula como vista', estado == 200, str(estado))
estado, cuerpo, _ = pedir('/perfiles/%s/vistas' % nuevo_perfil.get('id'), token=token_usuario)
comprobar('la marca queda guardada en ese perfil',
          json_de(cuerpo).get(str(creada.get('id'))) == 'viendo', cuerpo[:40])
estado, cuerpo, _ = pedir('/perfiles/%s/vistas/%s' % (nuevo_perfil.get('id'), creada.get('id')),
                          {'estado': 'inventado'}, 'PUT', token_usuario)
comprobar('400 por estado de vista invalido', estado == 400, json_de(cuerpo).get('error', ''))

otro_nombre = 'intruso%d' % random.randint(1000, 9999)
estado, cuerpo, _ = pedir('/registro', {'username': otro_nombre,
                                        'password': 'clave-de-prueba-2'}, 'POST')
token_otro = json_de(cuerpo).get('token', '')
estado, _, _ = pedir('/perfiles/%s' % nuevo_perfil.get('id'), None, 'DELETE', token_otro)
comprobar('otra cuenta no puede borrar ese perfil', estado == 404, str(estado))
estado, _, _ = pedir('/perfiles/%s/vistas' % nuevo_perfil.get('id'), token=token_otro)
comprobar('otra cuenta no puede ver esa lista', estado == 404, str(estado))

print('\n9. CATALOGO')
# Antes de mirarlo, se quitan los registros que creo esta misma verificacion.
pedir('/peliculas/%s' % creada.get('id'), None, 'DELETE', token)
pedir('/perfiles/%s' % nuevo_perfil.get('id'), None, 'DELETE', token_usuario)
conexion = sqlite3.connect(DB_NAME)
conexion.execute('DELETE FROM usuarios WHERE username IN (?, ?)',
                 (nombre_prueba, otro_nombre))
conexion.commit()
conexion.close()

estado, cuerpo, _ = pedir('/peliculas')
catalogo = json_de(cuerpo)
disponibles = [p for p in catalogo if p['estado'] == 'disponible']
estrenos = [p for p in catalogo if p['estado'] == 'proximamente']
comprobar('hay cartelera y proximos estrenos', len(disponibles) > 1 and len(estrenos) > 0,
          '%d disponibles, %d estrenos' % (len(disponibles), len(estrenos)))
comprobar('todas tienen poster', all(p['poster_url'] for p in catalogo))
comprobar('todas tienen trailer', all(p['trailer_url'] for p in catalogo),
          '%d sin trailer' % len([p for p in catalogo if not p['trailer_url']]))
comprobar('los estrenos tienen fecha', all(p['fecha_estreno'] for p in estrenos))

print('\n' + '=' * 62)
print('RESULTADO: %d correctas, %d fallidas' % (len(correctas), len(fallidas)))
if fallidas:
    print('\nRevisar:')
    for nombre, detalle in fallidas:
        print('  - %s  %s' % (nombre, detalle))
raise SystemExit(1 if fallidas else 0)

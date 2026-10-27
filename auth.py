"""Registro, inicio de sesión con JWT y los candados de las rutas protegidas."""

import datetime
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request

import limitador
import repositorio
from config import MINUTOS_EXPIRACION_TOKEN
from errores import cuerpo_valido, responder_error
from validaciones import validar_usuario

auth_bp = Blueprint('auth', __name__)


def _generar_token(usuario):
    """Dentro del token van quién es y qué rol tiene."""
    expiracion = datetime.datetime.now(datetime.timezone.utc) + \
        datetime.timedelta(minutes=MINUTOS_EXPIRACION_TOKEN)
    return jwt.encode({'id': usuario['id'], 'username': usuario['username'],
                       'rol': usuario['rol'], 'exp': expiracion},
                      current_app.config['SECRET_KEY'], algorithm='HS256')


def _datos_publicos(usuario):
    return {'id': usuario['id'], 'username': usuario['username'],
            'rol': usuario['rol']}


@auth_bp.route('/registro', methods=['POST'])
def registro():
    """Crea una cuenta de usuario normal. El rol admin no se pide por aquí."""
    datos, error = cuerpo_valido(validar_usuario)
    if error:
        return error
    username = datos['username'].strip()
    usuario_id = repositorio.crear_usuario(username, datos['password'])
    if usuario_id is None:
        return responder_error('Ese usuario ya está registrado', 409)
    usuario = repositorio.usuario_por_nombre(username)
    return jsonify({'token': _generar_token(usuario),
                    'usuario': _datos_publicos(usuario)}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return responder_error('Se esperaba un JSON con username y password', 400)
    freno = 'login:' + (request.remote_addr or '?')
    if limitador.bloqueado(freno):
        return responder_error('Demasiados intentos. Espera unos minutos.', 429)
    usuario = repositorio.usuario_por_nombre(datos.get('username'))
    if not repositorio.clave_de_usuario_correcta(usuario, datos.get('password')):
        limitador.registrar_fallo(freno)
        return responder_error('Usuario o contraseña incorrectos', 401)
    limitador.limpiar(freno)
    return jsonify({'token': _generar_token(usuario),
                    'usuario': _datos_publicos(usuario)}), 200


def _leer_token():
    cabecera = request.headers.get('Authorization', '')
    partes = cabecera.split()
    if len(partes) != 2 or partes[0] != 'Bearer':
        return None
    return partes[1]


# Se pone encima de una ruta con @token_requerido para protegerla.
def token_requerido(f):
    """Exige un header "Authorization: Bearer <token>" válido."""
    @wraps(f)
    def decorada(*args, **kwargs):
        token = _leer_token()
        if not token:
            return responder_error('Falta el token de autenticación', 401)
        try:
            g.usuario = jwt.decode(token, current_app.config['SECRET_KEY'],
                                   algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return responder_error('El token ha expirado', 401)
        except jwt.InvalidTokenError:
            return responder_error('Token inválido', 401)
        # Un token sin cuenta ni rol es de un formato anterior: hay que renovarlo.
        if not g.usuario.get('id') or not g.usuario.get('rol'):
            return responder_error('Token inválido', 401)
        return f(*args, **kwargs)
    return decorada


# Para lo que solo puede hacer quien administra la cartelera.
def solo_admin(f):
    """Además del token, exige que la cuenta tenga el rol de administrador."""
    @wraps(f)
    @token_requerido
    def decorada(*args, **kwargs):
        if g.usuario.get('rol') != 'admin':
            return responder_error('Esta operación es solo para administradores', 403)
        return f(*args, **kwargs)
    return decorada


# Llevar la lista de lo visto es cosa de quien ve peliculas, no de quien las administra.
def solo_usuario(f):
    """Exige token y que la cuenta NO sea de administrador."""
    @wraps(f)
    @token_requerido
    def decorada(*args, **kwargs):
        if g.usuario.get('rol') != 'usuario':
            return responder_error(
                'La lista de vistas es solo de las cuentas de usuario', 403)
        return f(*args, **kwargs)
    return decorada


# El panel la usa al abrirse: si el token no sirve, no se muestra nada.
@auth_bp.route('/sesion', methods=['GET'])
@token_requerido
def sesion():
    """Dice quién eres y qué rol tienes; si el token no vale, el candado da 401."""
    return jsonify({'username': g.usuario.get('username'),
                    'rol': g.usuario.get('rol'),
                    'id': g.usuario.get('id')}), 200

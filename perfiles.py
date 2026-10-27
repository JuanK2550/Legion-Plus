"""Rutas de los perfiles de cada cuenta, su clave y lo que cada uno marca.

Cualquier cuenta puede tener perfiles (nombre, avatar y clave). Las marcas de
"mi lista" son solo de las cuentas de usuario: el administrador gestiona la
cartelera, no lleva su propio historial de lo que ve.
"""

from flask import Blueprint, g, jsonify, request

import avatares
import limitador
import repositorio
from auth import solo_usuario, token_requerido
from errores import cuerpo_valido, responder_error
from validaciones import validar_estado_vista, validar_perfil

perfiles_bp = Blueprint('perfiles', __name__)

NO_ENCONTRADO = 'Perfil no encontrado'


def _mio(perfil_id):
    """El perfil solo existe para quien es su dueño; para el resto es un 404."""
    perfil = repositorio.obtener_perfil(perfil_id)
    if perfil is None or perfil.get('usuario_id') != g.usuario.get('id'):
        return None
    return perfil


@perfiles_bp.route('/avatares', methods=['GET'])
def listar_avatares():
    return jsonify(avatares.galeria()), 200


@perfiles_bp.route('/perfiles', methods=['GET'])
@token_requerido
def listar_perfiles():
    return jsonify(repositorio.listar_perfiles(g.usuario.get('id'))), 200


@perfiles_bp.route('/perfiles', methods=['POST'])
@token_requerido
def crear_perfil():
    datos, error = cuerpo_valido(validar_perfil)
    if error:
        return error
    datos['usuario_id'] = g.usuario.get('id')
    perfil_id = repositorio.crear_perfil(datos)
    return jsonify(repositorio.obtener_perfil(perfil_id)), 201


@perfiles_bp.route('/perfiles/<int:perfil_id>', methods=['PUT'])
@token_requerido
def actualizar_perfil(perfil_id):
    if _mio(perfil_id) is None:
        return responder_error(NO_ENCONTRADO, 404)
    datos, error = cuerpo_valido(validar_perfil)
    if error:
        return error
    repositorio.actualizar_perfil(perfil_id, datos)
    return jsonify(repositorio.obtener_perfil(perfil_id)), 200


@perfiles_bp.route('/perfiles/<int:perfil_id>/entrar', methods=['POST'])
@token_requerido
def entrar_al_perfil(perfil_id):
    """Comprueba la clave antes de dejar usar un perfil protegido."""
    perfil = _mio(perfil_id)
    if perfil is None:
        return responder_error(NO_ENCONTRADO, 404)
    datos = request.get_json(silent=True)
    datos = datos if isinstance(datos, dict) else {}
    # Una clave de 4 dígitos tiene solo 10.000 combinaciones: se limitan los intentos.
    freno = 'pin:%s:%s' % (perfil_id, request.remote_addr or '?')
    if limitador.bloqueado(freno):
        return responder_error('Demasiados intentos. Espera unos minutos.', 429)
    if not repositorio.clave_correcta(perfil_id, datos.get('clave')):
        limitador.registrar_fallo(freno)
        return responder_error('Clave incorrecta', 401)
    limitador.limpiar(freno)
    return jsonify(perfil), 200


@perfiles_bp.route('/perfiles/<int:perfil_id>', methods=['DELETE'])
@token_requerido
def eliminar_perfil(perfil_id):
    if _mio(perfil_id) is None:
        return responder_error(NO_ENCONTRADO, 404)
    repositorio.eliminar_perfil(perfil_id)
    return jsonify({'mensaje': 'Perfil eliminado correctamente',
                    'id': perfil_id}), 200


@perfiles_bp.route('/perfiles/<int:perfil_id>/vistas', methods=['GET'])
@solo_usuario
def listar_vistas(perfil_id):
    if _mio(perfil_id) is None:
        return responder_error(NO_ENCONTRADO, 404)
    return jsonify(repositorio.listar_vistas(perfil_id)), 200


@perfiles_bp.route('/perfiles/<int:perfil_id>/vistas/<int:pelicula_id>',
                   methods=['PUT'])
@solo_usuario
def marcar_vista(perfil_id, pelicula_id):
    if _mio(perfil_id) is None:
        return responder_error(NO_ENCONTRADO, 404)
    if repositorio.obtener_pelicula(pelicula_id) is None:
        return responder_error('Película no encontrada', 404)
    datos, error = cuerpo_valido(validar_estado_vista)
    if error:
        return error
    repositorio.marcar_vista(perfil_id, pelicula_id, datos['estado'])
    return jsonify({'pelicula_id': pelicula_id, 'estado': datos['estado']}), 200


@perfiles_bp.route('/perfiles/<int:perfil_id>/vistas/<int:pelicula_id>',
                   methods=['DELETE'])
@solo_usuario
def borrar_vista(perfil_id, pelicula_id):
    if _mio(perfil_id) is None:
        return responder_error(NO_ENCONTRADO, 404)
    repositorio.borrar_vista(perfil_id, pelicula_id)
    return jsonify({'mensaje': 'Marca eliminada', 'pelicula_id': pelicula_id}), 200

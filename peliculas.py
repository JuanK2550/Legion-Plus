"""Rutas de /peliculas: las cinco operaciones y la sincronización."""

from flask import Blueprint, jsonify, request

import repositorio
import tmdb
from auth import solo_admin
from errores import cuerpo_valido, responder_error
from validaciones import validar_pelicula

peliculas_bp = Blueprint('peliculas', __name__)

NO_ENCONTRADA = 'Película no encontrada'


@peliculas_bp.route('/sincronizar', methods=['POST'])
@solo_admin
def sincronizar():
    """Trae la cartelera y los estrenos desde The Movie Database."""
    peticion = request.get_json(silent=True) or {}
    buscar = peticion.get('buscar') or []
    if not isinstance(buscar, list):
        return responder_error('El campo "buscar" debe ser una lista de títulos', 400)
    if len(buscar) > 20 or not all(isinstance(t, str) for t in buscar):
        return responder_error('"buscar" admite hasta 20 títulos de texto', 400)
    try:
        resumen = tmdb.sincronizar(buscar=buscar)
    except tmdb.SinClave as error:
        return responder_error(str(error), 400)
    except Exception:
        return responder_error('No se pudo conectar con The Movie Database', 502)
    return jsonify(resumen), 200


@peliculas_bp.route('/peliculas', methods=['GET'])
def listar_peliculas():
    return jsonify(repositorio.listar_peliculas()), 200


@peliculas_bp.route('/peliculas/<int:pelicula_id>', methods=['GET'])
def obtener_pelicula(pelicula_id):
    pelicula = repositorio.obtener_pelicula(pelicula_id)
    if pelicula is None:
        return responder_error(NO_ENCONTRADA, 404)
    return jsonify(pelicula), 200


@peliculas_bp.route('/peliculas', methods=['POST'])
@solo_admin
def crear_pelicula():
    datos, error = cuerpo_valido(validar_pelicula)
    if error:
        return error
    pelicula_id = repositorio.crear_pelicula(datos)
    return jsonify(repositorio.obtener_pelicula(pelicula_id)), 201


# Primero se comprueba que exista: un id inventado es 404, no 400.
@peliculas_bp.route('/peliculas/<int:pelicula_id>', methods=['PUT'])
@solo_admin
def actualizar_pelicula(pelicula_id):
    if repositorio.obtener_pelicula(pelicula_id) is None:
        return responder_error(NO_ENCONTRADA, 404)
    datos, error = cuerpo_valido(validar_pelicula)
    if error:
        return error
    repositorio.actualizar_pelicula(pelicula_id, datos)
    return jsonify(repositorio.obtener_pelicula(pelicula_id)), 200


@peliculas_bp.route('/peliculas/<int:pelicula_id>', methods=['DELETE'])
@solo_admin
def eliminar_pelicula(pelicula_id):
    if repositorio.obtener_pelicula(pelicula_id) is None:
        return responder_error(NO_ENCONTRADA, 404)
    repositorio.eliminar_pelicula(pelicula_id)
    return jsonify({'mensaje': 'Película eliminada correctamente',
                    'id': pelicula_id}), 200

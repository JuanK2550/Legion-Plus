"""Un solo sitio para responder errores, en JSON o como página."""

from flask import jsonify, render_template, request

# Título grande que se muestra en la página de error de cada código.
TITULOS = {
    400: 'Petición incorrecta',
    401: 'Necesitas iniciar sesión',
    403: 'No tienes permiso',
    404: 'Aquí no hay nada',
    405: 'Método no permitido',
    413: 'Petición demasiado grande',
    429: 'Demasiados intentos',
    500: 'Algo falló en el servidor',
}


def _navegador():
    """True si quien pide es un navegador y no una llamada a la API."""
    aceptado = request.accept_mimetypes
    return aceptado['text/html'] > aceptado['application/json']


def cuerpo_valido(validacion):
    """Lee el JSON de la petición y lo valida.

    Devuelve (datos, None) si está bien, o (None, respuesta de error 400).
    """
    datos = request.get_json(silent=True)
    if datos is None:
        return None, responder_error('Se esperaba un cuerpo JSON', 400)
    error = validacion(datos)
    if error:
        return None, responder_error(error, 400)
    return datos, None


def responder_error(mensaje, codigo):
    if _navegador():
        pagina = render_template('error.html', codigo=codigo, mensaje=mensaje,
                                 titulo=TITULOS.get(codigo, 'Error'))
        return pagina, codigo
    return jsonify({'error': mensaje}), codigo


def registrar_manejadores(app):
    @app.errorhandler(400)
    def peticion_incorrecta(e):
        return responder_error('La petición no es válida', 400)

    @app.errorhandler(401)
    def no_autorizado(e):
        return responder_error('Necesitas un token válido', 401)

    @app.errorhandler(404)
    def no_encontrado(e):
        return responder_error('Ruta no encontrada', 404)

    @app.errorhandler(405)
    def metodo_no_permitido(e):
        return responder_error('Método no permitido en esta ruta', 405)

    @app.errorhandler(413)
    def demasiado_grande(e):
        return responder_error('La petición es demasiado grande', 413)

    @app.errorhandler(500)
    def error_interno(e):
        return responder_error('Error interno del servidor', 500)

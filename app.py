"""Punto de entrada: arma la aplicación Flask y la pone a correr."""

from flask import Flask, jsonify

import repositorio
from auth import auth_bp
from config import ADMIN_PASSWORD_HASH, ADMIN_USER, DEBUG, SECRET_KEY
from database import init_db
from errores import registrar_manejadores
from peliculas import peliculas_bp
from perfiles import perfiles_bp


CSP = ("default-src 'self'; script-src 'self'; object-src 'none'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
       "img-src 'self' data: https:; font-src https://fonts.gstatic.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "frame-src https://www.youtube.com https://www.youtube-nocookie.com")


def crear_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  # 1 MB por petición
    init_db()
    # La cuenta de administrador sale del .env y queda en la base.
    repositorio.asegurar_admin(ADMIN_USER, ADMIN_PASSWORD_HASH)
    # Cada blueprint es un grupo de rutas que vive en su propio archivo.
    app.register_blueprint(auth_bp)
    app.register_blueprint(peliculas_bp)
    app.register_blueprint(perfiles_bp)
    registrar_manejadores(app)

    @app.after_request
    def cabeceras_de_seguridad(respuesta):
        respuesta.headers.setdefault('Content-Security-Policy', CSP)
        respuesta.headers.setdefault('X-Content-Type-Options', 'nosniff')
        respuesta.headers.setdefault('X-Frame-Options', 'DENY')
        respuesta.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return respuesta

    @app.route('/', methods=['GET'])
    def bienvenida():
        return jsonify({'mensaje': 'Bienvenido a la API de Películas'}), 200

    return app


app = crear_app()

# Solo arranca el servidor si este archivo se ejecuta directamente.
if __name__ == '__main__':
    # debug solo si FLASK_DEBUG=1; el depurador de Flask permite ejecutar código.
    app.run(host='127.0.0.1', debug=DEBUG)

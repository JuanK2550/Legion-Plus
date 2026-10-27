"""Trae las películas desde The Movie Database y las guarda en la base."""
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import date

import repositorio
from config import TMDB_API_KEY

API = 'https://api.themoviedb.org/3'
POSTER = 'https://image.tmdb.org/t/p/w500'
FONDO = 'https://image.tmdb.org/t/p/w1280'
YOUTUBE = 'https://www.youtube.com/watch?v='
NAVEGADOR = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0'
IDIOMA = 'es-MX'
REGION = 'CO'

# Los géneros de TMDB traducidos a los siete que acepta nuestra API.
# TMDB maneja 19 géneros; aquí se reducen a los 7 que acepta la API.
GENEROS_TMDB = {
    28: 'Acción', 37: 'Acción',
    16: 'Animación',
    878: 'Ciencia ficción', 14: 'Ciencia ficción',
    35: 'Comedia', 10751: 'Comedia',
    18: 'Drama', 80: 'Drama', 36: 'Drama', 9648: 'Drama', 99: 'Drama',
    10402: 'Drama', 53: 'Drama', 10752: 'Drama',
    10749: 'Romance',
    27: 'Terror',
}
GENERO_POR_DEFECTO = 'Drama'
# Pedimos un mínimo de votos para no traer películas desconocidas o basura.
MINIMO_VOTOS = 1500
# Si una película tiene varios géneros, nos quedamos con el más específico.
PRIORIDAD = ('Animación', 'Terror', 'Romance', 'Acción', 'Ciencia ficción',
             'Comedia', 'Drama')
MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


class SinClave(Exception):
    """Falta configurar TMDB_API_KEY en config.py."""


def _pedir(ruta, **parametros):
    if not TMDB_API_KEY:
        raise SinClave('Falta la clave de TMDB en config.py')
    parametros['api_key'] = TMDB_API_KEY
    url = '%s%s?%s' % (API, ruta, urllib.parse.urlencode(parametros))
    with urllib.request.urlopen(url, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode('utf-8'))


def _genero(detalle):
    suyos = {GENEROS_TMDB[g['id']] for g in detalle.get('genres', [])
             if g['id'] in GENEROS_TMDB}
    for genero in PRIORIDAD:
        if genero in suyos:
            return genero
    return GENERO_POR_DEFECTO


def _director(detalle):
    equipo = detalle.get('credits', {}).get('crew', [])
    nombres = [p['name'] for p in equipo if p.get('job') == 'Director']
    return ', '.join(nombres[:2]) or 'Sin información'


def _buscar_video(videos):
    for tipo in ('Trailer', 'Teaser'):
        for v in videos:
            if v.get('site') == 'YouTube' and v.get('type') == tipo:
                return YOUTUBE + v['key']
    return None


def _buscar_en_youtube(titulo, anio):
    """Último recurso: buscar el tráiler en YouTube cuando TMDB no lo tiene."""
    consulta = urllib.parse.quote('%s %s trailer oficial' % (titulo, anio or ''))
    url = 'https://www.youtube.com/results?search_query=%s&sp=EgIQAQ%%253D%%253D' % consulta
    peticion = urllib.request.Request(url, headers={'User-Agent': NAVEGADOR})
    try:
        with urllib.request.urlopen(peticion, timeout=25) as respuesta:
            html = respuesta.read().decode('utf-8', 'replace')
    except Exception:
        return None
    encontrados = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
    return YOUTUBE + encontrados[0] if encontrados else None


def _trailer(detalle):
    """Primero el tráiler en español; si no hay, el original."""
    enlace = _buscar_video(detalle.get('videos', {}).get('results', []))
    if enlace:
        return enlace
    try:
        otros = _pedir('/movie/%d/videos' % detalle['id'])
        enlace = _buscar_video(otros.get('results', []))
    except Exception:
        enlace = None
    if enlace:
        return enlace
    return _buscar_en_youtube(detalle.get('title'), (detalle.get('release_date') or '')[:4])


def _plataformas(detalle):
    pais = detalle.get('watch/providers', {}).get('results', {}).get(REGION, {})
    nombres = [p['provider_name'] for p in pais.get('flatrate', [])]
    return ', '.join(nombres[:3]) or None


def _fecha_larga(texto):
    """2027-02-05 -> 5 de febrero de 2027"""
    try:
        f = date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None
    return '%d de %s de %d' % (f.day, MESES[f.month - 1], f.year)


def _a_pelicula(detalle, estado):
    estreno = detalle.get('release_date') or ''
    pelicula = {
        'titulo': detalle['title'],
        'director': _director(detalle),
        'genero': _genero(detalle),
        'anio': int(estreno[:4]) if estreno[:4].isdigit() else date.today().year,
        'sinopsis': detalle.get('overview') or None,
        'poster_url': POSTER + detalle['poster_path'] if detalle.get('poster_path') else None,
        'fondo_url': FONDO + detalle['backdrop_path'] if detalle.get('backdrop_path') else None,
        'trailer_url': _trailer(detalle),
        'estado': estado,
    }
    if estado == 'proximamente':
        pelicula['fecha_estreno'] = _fecha_larga(estreno) or 'Por confirmar'
    else:
        pelicula['calificacion'] = round(detalle.get('vote_average') or 0, 1)
        pelicula['plataformas'] = _plataformas(detalle)
    return pelicula


def _detalle(pelicula_id):
    return _pedir('/movie/%d' % pelicula_id, language=IDIOMA,
                  append_to_response='credits,videos,watch/providers')


def _ids_de(ruta, paginas, minimo_votos=0):
    """Recorre un listado de TMDB y devuelve los ids sin repetir."""
    ids = []
    for pagina in range(1, paginas + 1):
        datos = _pedir(ruta, language=IDIOMA, region=REGION, page=pagina)
        for p in datos.get('results', []):
            if p.get('vote_count', 0) < minimo_votos:
                continue
            if p['id'] not in ids:
                ids.append(p['id'])
    return ids


def _legible(titulo):
    """TMDB cuela conciertos con el título en otro alfabeto; aquí no se leen."""
    return all('LATIN' in unicodedata.name(letra, '')
               for letra in titulo if letra.isalpha())


def _sirve(datos):
    """Sin título legible, póster o tráiler no entra a la cartelera."""
    if not datos['titulo'] or not datos['poster_url'] or not datos['trailer_url']:
        return False
    return _legible(datos['titulo'])


def _guardar(detalle, estado):
    """Crea la película o actualiza la que ya exista con ese título."""
    datos = _a_pelicula(detalle, estado)
    if not _sirve(datos):
        return None
    existente = repositorio.pelicula_por_titulo(datos['titulo'])
    if existente:
        repositorio.actualizar_pelicula(existente['id'], datos)
        return 'actualizada'
    repositorio.crear_pelicula(datos)
    return 'nueva'


def _buscar_id(titulo):
    """De los resultados nos quedamos con el más votado, que es el conocido.

    Si el título termina en un año, se usa para afinar la búsqueda.
    """
    partes = titulo.rsplit(' ', 1)
    extra = {}
    if len(partes) == 2 and partes[1].isdigit() and len(partes[1]) == 4:
        titulo, extra['primary_release_year'] = partes[0], partes[1]
    datos = _pedir('/search/movie', language=IDIOMA, query=titulo, **extra)
    resultados = datos.get('results') or []
    if not resultados:
        return None
    return max(resultados, key=lambda p: p.get('vote_count', 0))['id']


def _sumar(resumen, resultado):
    if resultado == 'nueva':
        resumen['nuevas'] += 1
    elif resultado == 'actualizada':
        resumen['actualizadas'] += 1
    else:
        resumen['omitidas'] += 1


def _traer_estrenos(resumen, cuantos, hoy):
    """Los que todavía no se estrenan, de la lista oficial de TMDB."""
    traidos = []
    for pelicula_id in _ids_de('/movie/upcoming', 2):
        if len(traidos) >= cuantos:
            break
        detalle = _detalle(pelicula_id)
        if (detalle.get('release_date') or '') <= hoy:
            continue
        if _guardar(detalle, 'proximamente'):
            resumen['estrenos'] += 1
            traidos.append(pelicula_id)
        else:
            resumen['omitidas'] += 1
    return traidos


def _traer_buscados(resumen, titulos, vistas, hoy):
    """Los títulos concretos que pidió quien llama, ya estrenados o no."""
    for titulo in titulos:
        pelicula_id = _buscar_id(titulo)
        if not pelicula_id or pelicula_id in vistas:
            continue
        vistas.add(pelicula_id)
        detalle = _detalle(pelicula_id)
        futura = (detalle.get('release_date') or '') > hoy
        resultado = _guardar(detalle, 'proximamente' if futura else 'disponible')
        if futura and resultado:
            resumen['estrenos'] += 1
        else:
            _sumar(resumen, resultado)


def _traer_listas(resumen, cuantas, vistas, hoy):
    """Las populares y las mejor calificadas, ya estrenadas."""
    nuevas = 0
    for ruta in ('/movie/popular', '/movie/top_rated'):
        for pelicula_id in _ids_de(ruta, 3, MINIMO_VOTOS):
            if nuevas >= cuantas:
                return
            if pelicula_id in vistas:
                continue
            vistas.add(pelicula_id)
            detalle = _detalle(pelicula_id)
            if (detalle.get('release_date') or '') > hoy:
                continue
            _sumar(resumen, _guardar(detalle, 'disponible'))
            nuevas += 1


def sincronizar(cuantas=24, cuantos_estrenos=8, buscar=()):
    """Baja las mejores películas y los próximos estrenos, y los guarda."""
    resumen = {'nuevas': 0, 'actualizadas': 0, 'estrenos': 0, 'omitidas': 0}
    hoy = date.today().isoformat()
    vistas = set(_traer_estrenos(resumen, cuantos_estrenos, hoy))
    _traer_buscados(resumen, buscar, vistas, hoy)
    _traer_listas(resumen, cuantas, vistas, hoy)
    return resumen

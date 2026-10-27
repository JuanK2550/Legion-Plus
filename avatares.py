"""La galería de avatares: personajes traídos de APIs públicas y los locales."""
import json
import os
import urllib.request

CARPETA = os.path.join('static', 'img', 'avatares')
RUTA_LOCAL = '/static/img/avatares'
TIPOS = ('.png', '.jpg', '.jpeg', '.webp', '.svg')

POKEAPI = 'https://pokeapi.co/api/v2/pokemon/%s'
RICKMORTY = 'https://rickandmortyapi.com/api/character/%s'
POKEMONES = ('pikachu', 'charizard', 'bulbasaur', 'squirtle', 'eevee',
             'snorlax', 'mewtwo', 'gengar', 'lucario', 'jigglypuff')
PERSONAJES_RM = (1, 2, 3, 4, 5, 244)

_galeria = None


def _pedir(url):
    peticion = urllib.request.Request(url, headers={'User-Agent': 'Legion+/1.0'})
    with urllib.request.urlopen(peticion, timeout=15) as respuesta:
        return json.loads(respuesta.read().decode('utf-8'))


def _locales():
    """Los dibujos guardados en el propio proyecto."""
    if not os.path.isdir(CARPETA):
        return []
    return [{'id': archivo, 'nombre': os.path.splitext(archivo)[0].title(),
             'url': '%s/%s' % (RUTA_LOCAL, archivo)}
            for archivo in sorted(os.listdir(CARPETA))
            if archivo.lower().endswith(TIPOS)]


def _pokemon():
    salida = []
    for nombre in POKEMONES:
        try:
            datos = _pedir(POKEAPI % nombre)
            dibujo = datos['sprites']['other']['official-artwork']['front_default']
        except Exception:
            continue
        if dibujo:
            salida.append({'id': 'pokemon-' + nombre, 'nombre': nombre.title(),
                           'url': dibujo})
    return salida


def _rick_y_morty():
    salida = []
    for numero in PERSONAJES_RM:
        try:
            datos = _pedir(RICKMORTY % numero)
        except Exception:
            continue
        salida.append({'id': 'rickmorty-%d' % numero, 'nombre': datos['name'],
                       'url': datos['image']})
    return salida


def galeria(recargar=False):
    """Se arma una vez y se guarda en memoria para no pedirla en cada visita."""
    global _galeria
    if _galeria is None or recargar:
        _galeria = _locales() + _pokemon() + _rick_y_morty()
    return _galeria


def existe(identificador):
    return any(a['id'] == identificador for a in galeria())

"""Freno a la fuerza bruta: cuenta fallos por clave y bloquea temporalmente.

Vive en memoria (basta para un solo proceso). Con varios procesos o servidores
habría que usar Redis o Flask-Limiter.
"""

import threading
import time
from collections import defaultdict, deque

from config import MAX_INTENTOS, SEGUNDOS_BLOQUEO

_fallos = defaultdict(deque)
_candado = threading.Lock()


def _purgar(cola, ahora):
    while cola and ahora - cola[0] > SEGUNDOS_BLOQUEO:
        cola.popleft()


def bloqueado(clave):
    with _candado:
        cola = _fallos[clave]
        _purgar(cola, time.time())
        return len(cola) >= MAX_INTENTOS


def registrar_fallo(clave):
    with _candado:
        _fallos[clave].append(time.time())


def limpiar(clave):
    with _candado:
        _fallos.pop(clave, None)

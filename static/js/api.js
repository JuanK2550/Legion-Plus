// Llamadas a la API de Legión+ y manejo del token.

const BASE = window.location.origin;
const CLAVE_TOKEN = 'legion_token';
const CLAVE_PERFIL = 'legion_perfil';
const CLAVE_ROL = 'legion_rol';

// La galería de avatares la manda la API al cargar la página.
let GALERIA = [];

const ESTADOS_VISTA = {
  vista: 'Ya la vi',
  viendo: 'Viendo',
  no_interesa: 'No me interesa',
};

const GENEROS = ['Acción', 'Animación', 'Ciencia ficción', 'Comedia', 'Drama',
  'Romance', 'Terror'];

function leerToken() {
  return localStorage.getItem(CLAVE_TOKEN);
}

function guardarToken(token) {
  localStorage.setItem(CLAVE_TOKEN, token);
}

function borrarToken() {
  localStorage.removeItem(CLAVE_TOKEN);
  localStorage.removeItem(CLAVE_ROL);
}

// El rol se guarda solo para decidir qué botones mostrar; quien manda es el servidor.
function guardarRol(rol) {
  localStorage.setItem(CLAVE_ROL, rol || 'usuario');
}

function esAdmin() {
  return localStorage.getItem(CLAVE_ROL) === 'admin';
}

function haySesion() {
  return Boolean(leerToken());
}

function leerPerfilGuardado() {
  return localStorage.getItem(CLAVE_PERFIL);
}

function guardarPerfil(id) {
  localStorage.setItem(CLAVE_PERFIL, id);
}

function borrarPerfilGuardado() {
  localStorage.removeItem(CLAVE_PERFIL);
}

// El token viaja en la cabecera Authorization: Bearer <token>.
function cabeceras(conCuerpo) {
  const salida = {};
  if (conCuerpo) salida['Content-Type'] = 'application/json';
  const token = leerToken();
  if (token) salida.Authorization = 'Bearer ' + token;
  return salida;
}

// Lanza un Error con el mensaje que devuelve la API.
// Todas las llamadas pasan por aquí: añade el token y traduce los errores.
async function peticion(ruta, opciones = {}) {
  const { cuerpo, autenticando, ...resto } = opciones;
  const respuesta = await fetch(BASE + ruta, {
    ...resto,
    headers: cabeceras(Boolean(cuerpo)),
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });

  const datos = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    const error = new Error((datos && datos.error) || 'Error en la petición');
    error.codigo = respuesta.status;
    if (respuesta.status === 401 && !autenticando) {
      borrarToken();
      error.sesionCaducada = true;
      document.dispatchEvent(new CustomEvent('sesion-caducada'));
    }
    throw error;
  }
  return datos;
}

async function iniciarSesion(username, password) {
  const datos = await peticion('/login', {
    method: 'POST',
    cuerpo: { username, password },
    autenticando: true,
  });
  guardarToken(datos.token);
  guardarRol(datos.usuario && datos.usuario.rol);
  return datos.usuario;
}

// Crea una cuenta de usuario normal y deja la sesión abierta.
async function registrarse(username, password) {
  const datos = await peticion('/registro', {
    method: 'POST',
    cuerpo: { username, password },
    autenticando: true,
  });
  guardarToken(datos.token);
  guardarRol(datos.usuario && datos.usuario.rol);
  return datos.usuario;
}

function listarPeliculas() {
  return peticion('/peliculas');
}

async function cargarGaleria() {
  GALERIA = await peticion('/avatares');
}

function listarPerfiles() {
  return peticion('/perfiles');
}

function actualizarPerfil(id, perfil) {
  return peticion('/perfiles/' + id, { method: 'PUT', cuerpo: perfil });
}

function entrarAlPerfil(id, clave) {
  return peticion('/perfiles/' + id + '/entrar',
    { method: 'POST', cuerpo: { clave }, autenticando: true });
}

function crearPerfil(perfil) {
  return peticion('/perfiles', { method: 'POST', cuerpo: perfil });
}

function eliminarPerfil(id) {
  return peticion('/perfiles/' + id, { method: 'DELETE' });
}

function listarVistas(perfilId) {
  return peticion('/perfiles/' + perfilId + '/vistas');
}

function marcarVista(perfilId, peliculaId, estado) {
  return peticion(`/perfiles/${perfilId}/vistas/${peliculaId}`,
    { method: 'PUT', cuerpo: { estado } });
}

function borrarVista(perfilId, peliculaId) {
  return peticion(`/perfiles/${perfilId}/vistas/${peliculaId}`, { method: 'DELETE' });
}

// --- Administración de películas (requieren token) ---

function crearPelicula(pelicula) {
  return peticion('/peliculas', { method: 'POST', cuerpo: pelicula });
}

function actualizarPelicula(id, pelicula) {
  return peticion('/peliculas/' + id, { method: 'PUT', cuerpo: pelicula });
}

function eliminarPelicula(id) {
  return peticion('/peliculas/' + id, { method: 'DELETE' });
}

function sincronizarTmdb(buscar) {
  return peticion('/sincronizar', { method: 'POST', cuerpo: { buscar } });
}

// Le pregunta al servidor si el token guardado todavía sirve.
function comprobarSesion() {
  return peticion('/sesion');
}

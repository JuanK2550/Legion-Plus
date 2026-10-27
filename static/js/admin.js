// Panel de administración de Legión+: crear, editar y eliminar películas.
// Todo el texto que viene de la API se pinta con textContent (nunca innerHTML).

const $ = (id) => document.getElementById(id);

const adm = { peliculas: [], editando: null, borrando: null };

const CAMPOS = {
  titulo: 'f-titulo', director: 'f-director', genero: 'f-genero', anio: 'f-anio',
  estado: 'f-estado', calificacion: 'f-calificacion', fecha_estreno: 'f-fecha',
  plataformas: 'f-plataformas', poster_url: 'f-poster', fondo_url: 'f-fondo',
  trailer_url: 'f-trailer', sinopsis: 'f-sinopsis',
};

// --- Utilidades ---

function aviso(mensaje, tipo, codigo) {
  const caja = document.createElement('div');
  caja.className = 'aviso' + (tipo === 'exito' ? ' aviso-exito' : '');
  if (codigo) {
    const c = document.createElement('span');
    c.className = 'aviso-codigo';
    c.textContent = codigo;
    caja.appendChild(c);
  }
  const t = document.createElement('span');
  t.textContent = mensaje;
  caja.appendChild(t);
  $('avisos').appendChild(caja);
  setTimeout(() => caja.remove(), 5000);
}

function avisarError(error) {
  if (!error.sesionCaducada) aviso(error.message, 'error', error.codigo);
}

const abrir = (id) => $(id).classList.add('activo');
const cerrar = (id) => $(id).classList.remove('activo');

function mostrarVista() {
  const hay = haySesion();
  $('vista-login').classList.toggle('oculto', hay);
  $('vista-panel').classList.toggle('oculto', !hay);
  $('btn-salir').classList.toggle('oculto', !hay);
}

// --- Tabla ---

function celda(texto, clase) {
  const td = document.createElement('td');
  td.textContent = texto ?? '';
  if (clase) td.className = clase;
  return td;
}

function botonFila(texto, clase, alPulsar) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'boton ' + clase + ' boton-chico';
  b.textContent = texto;
  b.addEventListener('click', alPulsar);
  return b;
}

function filtradas() {
  const texto = $('a-buscar').value.trim().toLowerCase();
  const estado = $('a-filtro-estado').value;
  return adm.peliculas
    .filter((p) => !estado || p.estado === estado)
    .filter((p) => !texto || p.titulo.toLowerCase().includes(texto)
      || (p.director || '').toLowerCase().includes(texto))
    .sort((a, b) => b.id - a.id);
}

function pintarTabla() {
  const lista = filtradas();
  $('a-contador').textContent = `${lista.length} de ${adm.peliculas.length} películas`;
  const filas = lista.map((p) => {
    const tr = document.createElement('tr');
    tr.append(
      celda(p.id), celda(p.titulo, 'col-titulo'), celda(p.director), celda(p.genero),
      celda(p.anio),
      celda(p.estado === 'proximamente' ? '—' : Number(p.calificacion).toFixed(1)),
      celda(p.estado === 'proximamente' ? 'Próximamente' : 'Disponible'),
    );
    const acc = document.createElement('td');
    acc.className = 'col-acciones';
    acc.append(
      botonFila('Editar', 'boton-borde', () => abrirFormulario(p)),
      botonFila('Eliminar', 'boton-rojo', () => pedirBorrado(p)),
    );
    tr.appendChild(acc);
    return tr;
  });
  $('a-filas').replaceChildren(...filas);
}

async function cargar() {
  try {
    adm.peliculas = await listarPeliculas();
    pintarTabla();
  } catch (error) {
    avisarError(error);
  }
}

// --- Formulario crear / editar ---

function abrirFormulario(pelicula) {
  adm.editando = pelicula || null;
  $('form-titulo').textContent = pelicula ? 'Editar película' : 'Nueva película';
  for (const [campo, id] of Object.entries(CAMPOS)) {
    const valor = pelicula ? pelicula[campo] : '';
    $(id).value = valor ?? '';
  }
  if (!pelicula) $('f-estado').value = 'disponible';
  abrir('modal-pelicula');
  $('f-titulo').focus();
}

function numeroODefecto(id) {
  const texto = $(id).value.trim();
  return texto === '' ? null : Number(texto);
}

function leerFormulario() {
  const texto = (id) => $(id).value.trim() || null;
  return {
    titulo: $('f-titulo').value.trim(),
    director: $('f-director').value.trim(),
    genero: $('f-genero').value,
    anio: numeroODefecto('f-anio'),
    estado: $('f-estado').value,
    calificacion: numeroODefecto('f-calificacion'),
    fecha_estreno: texto('f-fecha'),
    plataformas: texto('f-plataformas'),
    poster_url: texto('f-poster'),
    fondo_url: texto('f-fondo'),
    trailer_url: texto('f-trailer'),
    sinopsis: texto('f-sinopsis'),
  };
}

async function guardar(evento) {
  evento.preventDefault();
  const datos = leerFormulario();
  const boton = $('btn-guardar');
  boton.disabled = true;
  try {
    if (adm.editando) await actualizarPelicula(adm.editando.id, datos);
    else await crearPelicula(datos);
    cerrar('modal-pelicula');
    aviso(adm.editando ? 'Película actualizada' : 'Película creada', 'exito');
    await cargar();
  } catch (error) {
    avisarError(error);
  } finally {
    boton.disabled = false;
  }
}

// --- Borrar ---

function pedirBorrado(pelicula) {
  adm.borrando = pelicula;
  $('borrar-texto').textContent =
    `¿Eliminar «${pelicula.titulo}»? También se quitarán las marcas de "mi lista" de los perfiles. No se puede deshacer.`;
  abrir('modal-borrar');
}

async function confirmarBorrado() {
  if (!adm.borrando) return;
  try {
    await eliminarPelicula(adm.borrando.id);
    cerrar('modal-borrar');
    aviso('Película eliminada', 'exito');
    adm.borrando = null;
    await cargar();
  } catch (error) {
    avisarError(error);
  }
}

// --- Sincronizar con TMDB ---

async function sincronizar() {
  const titulos = $('sync-titulos').value.split('\n').map((t) => t.trim()).filter(Boolean);
  const boton = $('btn-sync-ir');
  boton.disabled = true;
  boton.textContent = 'Sincronizando…';
  try {
    const resumen = await sincronizarTmdb(titulos);
    const partes = Object.entries(resumen || {})
      .filter(([, v]) => ['number', 'string'].includes(typeof v))
      .map(([k, v]) => `${k}: ${v}`);
    cerrar('modal-sync');
    aviso('Sincronización lista' + (partes.length ? ' (' + partes.join(', ') + ')' : ''), 'exito');
    await cargar();
  } catch (error) {
    avisarError(error);
  } finally {
    boton.disabled = false;
    boton.textContent = 'Sincronizar';
  }
}

// --- Sesión ---

async function entrar(evento) {
  evento.preventDefault();
  try {
    const usuario = await iniciarSesion($('a-usuario').value, $('a-password').value);
    if (!usuario || usuario.rol !== 'admin') {
      borrarToken();
      aviso('Esa cuenta no puede administrar la cartelera', 'error', 403);
      return;
    }
    $('form-login').reset();
    mostrarVista();
    await cargar();
  } catch (error) {
    aviso(error.message, 'error', error.codigo);
  }
}

function salir() {
  borrarToken();
  adm.peliculas = [];
  mostrarVista();
  aviso('Sesión cerrada', 'exito');
}

// --- Arranque ---

function iniciar() {
  for (const g of GENEROS) {
    const o = document.createElement('option');
    o.value = o.textContent = g;
    $('f-genero').appendChild(o);
  }

  $('form-login').addEventListener('submit', entrar);
  $('btn-salir').addEventListener('click', salir);
  $('btn-nueva').addEventListener('click', () => abrirFormulario(null));
  $('btn-sync').addEventListener('click', () => abrir('modal-sync'));
  $('btn-sync-ir').addEventListener('click', sincronizar);
  $('form-pelicula').addEventListener('submit', guardar);
  $('btn-confirmar-borrar').addEventListener('click', confirmarBorrado);
  $('a-buscar').addEventListener('input', pintarTabla);
  $('a-filtro-estado').addEventListener('change', pintarTabla);

  document.querySelectorAll('[data-cerrar]').forEach((b) =>
    b.addEventListener('click', () => cerrar(b.dataset.cerrar)));
  document.querySelectorAll('.modal').forEach((m) =>
    m.addEventListener('click', (e) => { if (e.target === m) cerrar(m.id); }));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') document.querySelectorAll('.modal.activo').forEach((m) => cerrar(m.id));
  });
  document.addEventListener('sesion-caducada', () => {
    mostrarVista();
    aviso('Tu sesión caducó, vuelve a iniciar sesión', 'error', 401);
  });

  comprobarAcceso();
}

// No basta con tener un token guardado: lo valida el servidor antes de
// mostrar el panel. Si no sirve, se borra y queda el formulario de acceso.
async function comprobarAcceso() {
  if (haySesion()) {
    try {
      const sesion = await comprobarSesion();
      if (sesion.rol !== 'admin') {
        borrarToken();
        aviso('Esta cuenta no es de administrador', 'error', 403);
      }
    } catch (error) {
      borrarToken();
    }
  }
  mostrarVista();
  if (haySesion()) await cargar();
}

iniciar();

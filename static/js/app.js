// Arranque y eventos de Legión+.

const SEGUNDOS_CARRUSEL = 7000;
const DESTACADAS = 5;

const estado = {
  peliculas: [],
  genero: 'Todas',
  orden: 'calificacion',
  busqueda: '',
  seleccionada: null,
  marcaFiltro: null,
  estrenos: [],
  destacadas: [],
  diapositiva: 0,
  reloj: null,
  perfiles: [],
  perfil: null,
  vistas: {},
  avatarElegido: null,
  editandoPerfil: null,
  perfilPendiente: null,
};

// Los tres filtros (género, búsqueda y mi lista) se aplican a la vez.
function filtrar(peliculas) {
  const texto = estado.busqueda.trim().toLowerCase();
  return peliculas.filter((pelicula) => {
    const coincideGenero = estado.genero === 'Todas' || pelicula.genero === estado.genero;
    const coincideTexto = !texto
      || pelicula.titulo.toLowerCase().includes(texto)
      || pelicula.director.toLowerCase().includes(texto);
    const coincideMarca = !estado.marcaFiltro
      || estado.vistas[pelicula.id] === estado.marcaFiltro;
    return coincideGenero && coincideTexto && coincideMarca;
  });
}

function ordenar(peliculas) {
  const copia = [...peliculas];
  if (estado.orden === 'titulo') return copia.sort((a, b) => a.titulo.localeCompare(b.titulo, 'es'));
  if (estado.orden === 'anio') return copia.sort((a, b) => b.anio - a.anio);
  return copia.sort((a, b) => b.calificacion - a.calificacion);
}

// Las mejor calificadas van al carrusel de la portada.
// "5 de febrero de 2027" -> 20270205, para poder ordenar los estrenos.
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
  'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

function fechaOrdenable(texto) {
  const partes = String(texto || '').toLowerCase().match(/(\d+) de ([a-zé]+) de (\d{4})/);
  if (!partes) return Number.MAX_SAFE_INTEGER;
  const mes = MESES.indexOf(partes[2]);
  return Number(partes[3]) * 10000 + (mes + 1) * 100 + Number(partes[1]);
}

function ordenarPorEstreno(peliculas) {
  return [...peliculas].sort((a, b) => fechaOrdenable(a.fecha_estreno) - fechaOrdenable(b.fecha_estreno));
}

function mejores(peliculas, cuantas) {
  return [...peliculas].sort((a, b) => b.calificacion - a.calificacion).slice(0, cuantas);
}

function mostrarDiapositiva(indice) {
  if (!estado.destacadas.length) return;
  estado.diapositiva = (indice + estado.destacadas.length) % estado.destacadas.length;
  activarDiapositiva(estado.diapositiva);
}

function pasar(salto) {
  mostrarDiapositiva(estado.diapositiva + salto);
  reiniciarReloj();
}

// El carrusel sigue girando salvo mientras haya un modal abierto encima.
function reiniciarReloj() {
  clearInterval(estado.reloj);
  estado.reloj = setInterval(() => {
    if (!document.querySelector('.modal.activo')) mostrarDiapositiva(estado.diapositiva + 1);
  }, SEGUNDOS_CARRUSEL);
}

function montarCarrusel() {
  estado.destacadas = mejores(estado.peliculas, DESTACADAS);
  dibujarCarrusel(estado.destacadas, {
    alVerTrailer: verTrailer,
    alVerDetalle: abrirDetalle,
    alElegir: (i) => pasar(i - estado.diapositiva),
  });
  mostrarDiapositiva(0);
  if (estado.destacadas.length) reiniciarReloj();
}

function verTrailer(titulo, idVideo) {
  reproducirTrailer(titulo, idVideo);
}

// Cuántas películas tiene el perfil en cada estado.
function contarVistas() {
  const conteos = { viendo: 0, vista: 0, no_interesa: 0 };
  Object.values(estado.vistas).forEach((marca) => {
    if (marca in conteos) conteos[marca] += 1;
  });
  return conteos;
}

function elegirMarca(marca) {
  estado.marcaFiltro = marca;
  pintar();
}

function pintar() {
  dibujarFiltrosLista(estado.marcaFiltro, Boolean(estado.perfil) && !esAdmin(),
    contarVistas(), elegirMarca);
  dibujarFiltros(estado.genero, elegirGenero);
  const lista = ordenar(filtrar(estado.peliculas));
  if (!lista.length) {
    mostrarEstado('vacio');
    return;
  }
  mostrarEstado('listo');
  dibujarCartelera(lista, abrirDetalle, estado.vistas);
}

// Un solo GET trae todo y aquí se separa en cartelera y estrenos.
async function cargarCartelera() {
  mostrarEstado('cargando');
  try {
    const todas = await listarPeliculas();
    estado.peliculas = todas.filter((p) => p.estado !== 'proximamente');
    estado.estrenos = ordenarPorEstreno(todas.filter((p) => p.estado === 'proximamente'));
    montarCarrusel();
    dibujarProximamente(estado.estrenos, abrirDetalle, verTrailer);
    pintar();
  } catch (error) {
    mostrarEstado('error');
    mostrarAviso(error.message, 'error', error.codigo);
  }
}

function elegirGenero(genero) {
  estado.genero = genero;
  pintar();
}

function abrirDetalle(pelicula) {
  estado.seleccionada = pelicula;
  mostrarDetalle(pelicula);
  actualizarMarcas(estado.vistas[pelicula.id], Boolean(estado.perfil) && !esAdmin());
}

// Muestra el error de la API, salvo si ya avisamos de la sesión caducada.
function avisarError(error) {
  if (!error.sesionCaducada) mostrarAviso(error.message, 'error', error.codigo);
}

async function entrar(evento) {
  evento.preventDefault();
  try {
    const usuario = await iniciarSesion($('campo-usuario').value, $('campo-password').value);
    $('formulario-login').reset();
    cerrarModal('modal-login');
    await despuesDeEntrar(usuario, 'Sesión iniciada');
  } catch (error) {
    mostrarAviso(error.message, 'error', error.codigo);
  }
}

async function crearCuenta(evento) {
  evento.preventDefault();
  try {
    const usuario = await registrarse($('registro-usuario').value,
      $('registro-password').value);
    $('formulario-registro').reset();
    cerrarModal('modal-registro');
    await despuesDeEntrar(usuario, 'Cuenta creada, ya puedes crear tu perfil');
  } catch (error) {
    mostrarAviso(error.message, 'error', error.codigo);
  }
}

// Lo que pasa igual al entrar y al registrarse: refrescar la barra y pedir perfil.
async function despuesDeEntrar(usuario, mensaje) {
  // Chrome a veces rellena el buscador con el usuario del formulario.
  limpiarBuscador();
  actualizarSesion();
  actualizarChipPerfil(null);
  mostrarAviso(mensaje + (usuario ? ' como ' + usuario.username : ''), 'exito');
  if (esAdmin()) mostrarAviso('Entraste como administrador: usa el botón Admin', 'exito');
  await cargarPerfiles();
  abrirModal('modal-perfiles');
}

function limpiarBuscador() {
  $('buscador').value = '';
  estado.busqueda = '';
}

function alternarSesion() {
  if (!haySesion()) {
    abrirModal('modal-login');
    return;
  }
  borrarToken();
  salirDelPerfil();
  actualizarChipPerfil(null);
  actualizarSesion();
  mostrarAviso('Sesión cerrada', 'exito');
}

// --- Perfiles ---

async function cargarPerfiles() {
  try {
    estado.perfiles = await listarPerfiles();
    refrescarSelector();
  } catch (error) {
    avisarError(error);
  }
}

function refrescarSelector() {
  if (!estado.avatarElegido && GALERIA.length) estado.avatarElegido = GALERIA[0].id;
  dibujarPerfiles(estado.perfiles, estado.perfil && estado.perfil.id, {
    alElegir: elegirPerfil,
    alBorrar: borrarPerfil,
    alEditar: editarPerfil,
  });
  dibujarOpcionesAvatar(estado.avatarElegido, elegirAvatar);
}

function elegirAvatar(nombre) {
  estado.avatarElegido = nombre;
  dibujarOpcionesAvatar(nombre, elegirAvatar);
}

// Si el perfil tiene clave, primero hay que escribirla.
async function elegirPerfil(perfil) {
  if (perfil.tiene_clave) {
    estado.perfilPendiente = perfil;
    $('clave-texto').textContent = 'Escribe la clave de ' + perfil.nombre;
    $('formulario-clave').reset();
    abrirModal('modal-clave');
    return;
  }
  await entrarComo(perfil);
}

async function comprobarClave(evento) {
  evento.preventDefault();
  try {
    await entrarAlPerfil(estado.perfilPendiente.id, $('campo-clave').value);
    cerrarModal('modal-clave');
    await entrarComo(estado.perfilPendiente);
  } catch (error) {
    mostrarAviso(error.message, 'error', error.codigo);
  }
}

async function entrarComo(perfil) {
  estado.perfil = perfil;
  guardarPerfil(perfil.id);
  actualizarChipPerfil(perfil);
  cerrarModal('modal-perfiles');
  await cargarVistas();
  pintar();
  mostrarAviso('Viendo como ' + perfil.nombre, 'exito');
}

function salirDelPerfil() {
  estado.perfil = null;
  estado.vistas = {};
  estado.marcaFiltro = null;
  borrarPerfilGuardado();
  actualizarChipPerfil(null);
  pintar();
}

async function cargarVistas() {
  // El administrador no lleva lista de lo que ve.
  if (!estado.perfil || esAdmin()) return;
  try {
    estado.vistas = await listarVistas(estado.perfil.id);
  } catch (error) {
    estado.vistas = {};
  }
}

async function borrarPerfil(perfil) {
  try {
    await eliminarPerfil(perfil.id);
    if (estado.perfil && estado.perfil.id === perfil.id) salirDelPerfil();
    await cargarPerfiles();
    mostrarAviso('Perfil eliminado', 'exito');
  } catch (error) {
    avisarError(error);
  }
}

function datosDelFormularioPerfil() {
  const datos = {
    nombre: $('campo-perfil-nombre').value,
    avatar: estado.avatarElegido,
  };
  const clave = $('campo-perfil-clave').value.trim();
  if (clave) datos.clave = clave;
  return datos;
}

async function guardarPerfilNuevo() {
  try {
    if (estado.editandoPerfil) {
      await actualizarPerfil(estado.editandoPerfil.id, datosDelFormularioPerfil());
      mostrarAviso('Perfil actualizado', 'exito');
    } else {
      await crearPerfil(datosDelFormularioPerfil());
      mostrarAviso('Perfil creado', 'exito');
    }
    limpiarFormularioPerfil();
    await cargarPerfiles();
  } catch (error) {
    avisarError(error);
  }
}

function limpiarFormularioPerfil() {
  estado.editandoPerfil = null;
  $('campo-perfil-nombre').value = '';
  $('campo-perfil-clave').value = '';
  $('campo-perfil-clave').placeholder = '····';
  $('resumen-perfil').textContent = 'Agregar un perfil';
  $('btn-crear-perfil').textContent = 'Crear perfil';
  $('btn-cancelar-perfil').classList.add('oculto');
  $('caja-perfil-nuevo').open = false;
  estado.avatarElegido = GALERIA.length ? GALERIA[0].id : null;
  dibujarOpcionesAvatar(estado.avatarElegido, elegirAvatar);
}

function editarPerfil(perfil) {
  estado.editandoPerfil = perfil;
  estado.avatarElegido = perfil.avatar;
  $('campo-perfil-nombre').value = perfil.nombre;
  $('campo-perfil-clave').value = '';
  $('campo-perfil-clave').placeholder = perfil.tiene_clave
    ? 'tiene clave, escribe una nueva o déjalo vacío para quitarla' : '····';
  $('resumen-perfil').textContent = 'Editando a ' + perfil.nombre;
  $('btn-crear-perfil').textContent = 'Guardar cambios';
  $('btn-cancelar-perfil').classList.remove('oculto');
  $('caja-perfil-nuevo').open = true;
  dibujarOpcionesAvatar(estado.avatarElegido, elegirAvatar);
}

// Marca la película abierta; si se pulsa la marca activa, se quita.
async function marcarPelicula(nuevoEstado) {
  const pelicula = estado.seleccionada;
  const actual = estado.vistas[pelicula.id];
  try {
    if (actual === nuevoEstado) {
      await borrarVista(estado.perfil.id, pelicula.id);
      delete estado.vistas[pelicula.id];
    } else {
      await marcarVista(estado.perfil.id, pelicula.id, nuevoEstado);
      estado.vistas[pelicula.id] = nuevoEstado;
    }
    actualizarMarcas(estado.vistas[pelicula.id], true);
    pintar();
  } catch (error) {
    avisarError(error);
  }
}

async function recuperarPerfilGuardado() {
  if (!haySesion()) return;
  actualizarChipPerfil(null);
  const id = leerPerfilGuardado();
  if (!id) return;
  await cargarPerfiles();
  const perfil = estado.perfiles.find((p) => String(p.id) === String(id));
  if (!perfil) return;
  estado.perfil = perfil;
  actualizarChipPerfil(perfil);
  await cargarVistas();
}

function registrarEventos() {
  $('buscador').addEventListener('input', (e) => {
    estado.busqueda = e.target.value;
    pintar();
  });

  $('orden').addEventListener('change', (e) => {
    estado.orden = e.target.value;
    pintar();
  });

  $('btn-sesion').addEventListener('click', alternarSesion);
  $('btn-perfil').addEventListener('click', async () => {
    await cargarPerfiles();
    abrirModal('modal-perfiles');
  });
  $('btn-crear-perfil').addEventListener('click', guardarPerfilNuevo);
  $('btn-cancelar-perfil').addEventListener('click', limpiarFormularioPerfil);
  $('formulario-clave').addEventListener('submit', comprobarClave);
  document.querySelectorAll('.marca').forEach((boton) => {
    boton.addEventListener('click', () => marcarPelicula(boton.dataset.estado));
  });
  $('formulario-login').addEventListener('submit', entrar);
  $('btn-registro').addEventListener('click', () => abrirModal('modal-registro'));
  $('formulario-registro').addEventListener('submit', crearCuenta);




  $('btn-trailer').addEventListener('click', () => {
    const pelicula = estado.seleccionada;
    cerrarModal('modal-detalle');
    verTrailer(pelicula.titulo, trailerDe(pelicula));
  });

  $('anterior').addEventListener('click', () => pasar(-1));
  $('siguiente').addEventListener('click', () => pasar(1));

  document.querySelectorAll('[data-cerrar]').forEach((boton) => {
    boton.addEventListener('click', () => cerrarModal(boton.dataset.cerrar));
  });

  document.querySelectorAll('.modal').forEach((modal) => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) cerrarModal(modal.id);
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') cerrarModales();
  });

  document.addEventListener('sesion-caducada', () => {
    actualizarSesion();
    cerrarModales();
    mostrarAviso('Tu sesión caducó, vuelve a iniciar sesión', 'error', 401);
  });
}

actualizarSesion();
registrarEventos();
cargarGaleria().catch(() => {}).then(recuperarPerfilGuardado).then(cargarCartelera);

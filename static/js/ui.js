// Dibuja el carrusel, la cartelera, los modales y los avisos.

function $(id) {
  return document.getElementById(id);
}

// Acepta youtube.com/watch?v=ID, youtu.be/ID o youtube.com/embed/ID
function idDeYoutube(url) {
  const encontrado = String(url || '').match(/(?:v=|youtu\.be\/|embed\/)([A-Za-z0-9_-]{11})/);
  return encontrado ? encontrado[1] : null;
}

function trailerDe(pelicula) {
  return idDeYoutube(pelicula.trailer_url);
}

function estrellas(calificacion) {
  const llenas = Math.round(calificacion / 2);
  return '★'.repeat(llenas) + '☆'.repeat(5 - llenas);
}

// Color estable a partir del título, para los pósters sin imagen.
function degradado(titulo) {
  let suma = 0;
  for (const letra of titulo) suma += letra.charCodeAt(0);
  const tono = suma % 360;
  return `linear-gradient(145deg, hsl(${tono}, 55%, 30%), hsl(${(tono + 40) % 360}, 60%, 12%))`;
}

function crearPosterFalso(pelicula) {
  const falso = document.createElement('div');
  falso.className = 'poster-falso';
  falso.style.background = degradado(pelicula.titulo);
  falso.textContent = pelicula.titulo;
  return falso;
}

// Si la imagen no carga, queda un degradado con el título encima.
function crearPoster(pelicula, conInsignia) {
  const caja = document.createElement('div');
  caja.className = 'poster';

  if (pelicula.poster_url) {
    const imagen = document.createElement('img');
    imagen.src = pelicula.poster_url;
    imagen.alt = 'Póster de ' + pelicula.titulo;
    imagen.loading = 'lazy';
    imagen.addEventListener('error', () => imagen.replaceWith(crearPosterFalso(pelicula)));
    caja.appendChild(imagen);
  } else {
    caja.appendChild(crearPosterFalso(pelicula));
  }

  if (conInsignia) {
    const insignia = document.createElement('span');
    insignia.className = 'insignia';
    insignia.textContent = pelicula.calificacion.toFixed(1);
    caja.appendChild(insignia);
  }
  return caja;
}

// Dibujo del avatar; si la imagen no carga, queda la inicial sobre un color.
function crearAvatar(idAvatar, nombre = '') {
  const circulo = document.createElement('span');
  circulo.className = 'avatar';
  circulo.style.background = colorDeAvatar(idAvatar || nombre);
  circulo.textContent = (nombre.trim()[0] || '?').toUpperCase();

  const dibujo = GALERIA.find((a) => a.id === idAvatar);
  if (!dibujo) return circulo;

  const imagen = document.createElement('img');
  imagen.src = dibujo.url;
  imagen.alt = '';
  imagen.addEventListener('load', () => circulo.replaceChildren(imagen));
  return circulo;
}

function colorDeAvatar(semilla) {
  let suma = 0;
  for (const letra of String(semilla)) suma += letra.codePointAt(0);
  return `hsl(${suma % 360}, 45%, 32%)`;
}

// Sello de "ya la vi / viendo / no me interesa" sobre el póster.
function crearSello(estado) {
  const sello = document.createElement('span');
  sello.className = 'sello sello-' + estado;
  sello.textContent = ESTADOS_VISTA[estado];
  return sello;
}

function crearTarjeta(pelicula, alAbrir, estadoVista) {
  const tarjeta = document.createElement('button');
  tarjeta.className = 'tarjeta' + (estadoVista === 'no_interesa' ? ' descartada' : '');
  tarjeta.type = 'button';

  const poster = crearPoster(pelicula, true);
  if (estadoVista) poster.appendChild(crearSello(estadoVista));
  tarjeta.appendChild(poster);

  const titulo = document.createElement('p');
  titulo.className = 'tarjeta-titulo';
  titulo.textContent = pelicula.titulo;

  const datos = document.createElement('p');
  datos.className = 'tarjeta-datos';
  datos.textContent = `${pelicula.anio} · ${pelicula.genero}`;

  const nota = document.createElement('p');
  nota.className = 'estrellas';
  nota.textContent = estrellas(pelicula.calificacion);

  tarjeta.append(titulo, datos, nota);
  tarjeta.addEventListener('click', () => alAbrir(pelicula));
  return tarjeta;
}

function dibujarCartelera(peliculas, alAbrir, vistas = {}) {
  const cartelera = $('cartelera');
  cartelera.replaceChildren();
  peliculas.forEach((pelicula) => cartelera.appendChild(
    crearTarjeta(pelicula, alAbrir, vistas[pelicula.id])));
}

function crearDiapositiva(pelicula, acciones) {
  const slide = document.createElement('div');
  slide.className = 'diapositiva';

  // Imagen ancha de la película; si no hay, el póster desenfocado.
  const imagenFondo = pelicula.fondo_url;
  const fondo = document.createElement('div');
  fondo.className = 'diapositiva-fondo' + (imagenFondo ? '' : ' borroso');
  if (imagenFondo) {
    fondo.style.background = `url("${imagenFondo}") center 22% / cover`;
  } else {
    fondo.style.background = pelicula.poster_url
      ? `url("${pelicula.poster_url}") center / cover`
      : degradado(pelicula.titulo);
  }

  const velo = document.createElement('div');
  velo.className = 'diapositiva-velo';

  const contenido = document.createElement('div');
  contenido.className = 'diapositiva-contenido';

  const texto = document.createElement('div');
  texto.className = 'diapositiva-texto';

  const etiqueta = document.createElement('p');
  etiqueta.className = 'etiqueta-destacada';
  etiqueta.textContent = 'Destacada en Legión+';

  const titulo = document.createElement('h2');
  titulo.className = 'diapositiva-titulo';
  titulo.textContent = pelicula.titulo;

  const datos = document.createElement('p');
  datos.className = 'diapositiva-datos';
  datos.textContent =
    `${pelicula.genero} · ${pelicula.anio} · ${pelicula.calificacion.toFixed(1)}/10 ${estrellas(pelicula.calificacion)}`;

  const sinopsis = document.createElement('p');
  sinopsis.className = 'diapositiva-sinopsis';
  sinopsis.textContent = pelicula.sinopsis || 'Sin sinopsis disponible.';

  const botones = document.createElement('div');
  botones.className = 'diapositiva-botones';
  if (trailerDe(pelicula)) {
    botones.appendChild(crearBotonTrailer(pelicula, acciones.alVerTrailer, 'boton-rojo'));
  }
  const verDetalle = document.createElement('button');
  verDetalle.className = 'boton boton-borde';
  verDetalle.type = 'button';
  verDetalle.textContent = 'Ver detalle';
  verDetalle.addEventListener('click', () => acciones.alVerDetalle(pelicula));
  botones.appendChild(verDetalle);

  texto.append(etiqueta, titulo, datos, sinopsis,
    crearPlataformas(pelicula, 'Disponible en'), botones);

  const poster = document.createElement('div');
  poster.className = 'diapositiva-poster';
  poster.appendChild(crearPoster(pelicula, false).firstChild);
  poster.addEventListener('click', () => acciones.alVerDetalle(pelicula));

  contenido.append(texto, poster);
  slide.append(fondo, velo, contenido);
  return slide;
}

function listaPlataformas(pelicula) {
  return (pelicula.plataformas || '').split(',').map((p) => p.trim()).filter(Boolean);
}

function esProximamente(pelicula) {
  return pelicula.estado === 'proximamente';
}

// Fila de plataformas donde está publicada la película.
function crearPlataformas(pelicula, etiqueta) {
  const plataformas = listaPlataformas(pelicula);
  const fila = document.createElement('p');
  fila.className = 'plataformas';
  if (!plataformas.length) return fila;

  const texto = document.createElement('span');
  texto.className = 'plataformas-texto';
  texto.textContent = etiqueta;
  fila.appendChild(texto);
  plataformas.forEach((nombre) => {
    const chip = document.createElement('span');
    chip.className = 'plataforma';
    chip.textContent = nombre;
    fila.appendChild(chip);
  });
  return fila;
}

function crearBotonTrailer(pelicula, alVerTrailer, estilo) {
  const boton = document.createElement('button');
  boton.className = 'boton ' + estilo;
  boton.type = 'button';
  boton.textContent = '▶ Ver tráiler';
  boton.addEventListener('click', () => alVerTrailer(pelicula.titulo, trailerDe(pelicula)));
  return boton;
}

// El carrusel muestra las mejor calificadas de la cartelera.
function dibujarCarrusel(peliculas, acciones) {
  const carrusel = $('carrusel');
  carrusel.classList.toggle('oculto', peliculas.length === 0);
  $('diapositivas').replaceChildren(...peliculas.map((p) => crearDiapositiva(p, acciones)));
  $('puntos').replaceChildren(...peliculas.map((p, i) => {
    const punto = document.createElement('button');
    punto.className = 'punto';
    punto.type = 'button';
    punto.setAttribute('aria-label', 'Ir a ' + p.titulo);
    punto.addEventListener('click', () => acciones.alElegir(i));
    return punto;
  }));
}

function activarDiapositiva(indice) {
  $('diapositivas').querySelectorAll('.diapositiva')
    .forEach((s, i) => s.classList.toggle('activa', i === indice));
  $('puntos').querySelectorAll('.punto')
    .forEach((p, i) => p.classList.toggle('activo', i === indice));
}

// Filtros de "mi lista", al lado de los de género.
function dibujarFiltrosLista(activo, hayPerfil, conteos, alElegir) {
  const caja = $('filtros-lista');
  caja.classList.toggle('oculto', !hayPerfil);
  caja.replaceChildren();
  if (!hayPerfil) return;

  const etiqueta = document.createElement('span');
  etiqueta.className = 'filtros-titulo';
  etiqueta.textContent = 'Mi lista';
  caja.appendChild(etiqueta);

  Object.entries(ESTADOS_VISTA).forEach(([estado, texto]) => {
    const boton = document.createElement('button');
    boton.className = 'filtro filtro-lista' + (estado === activo ? ' activo' : '');
    boton.type = 'button';
    boton.textContent = `${texto} (${conteos[estado] || 0})`;
    boton.addEventListener('click', () => alElegir(estado === activo ? null : estado));
    caja.appendChild(boton);
  });
}

function dibujarProximamente(estrenos, alAbrir, alVerTrailer) {
  document.querySelector('.proximamente').classList.toggle('oculto', !estrenos.length);
  $('estrenos').replaceChildren(...estrenos.map((pelicula) => {
    const tarjeta = document.createElement('article');
    tarjeta.className = 'estreno';

    const abrirFicha = document.createElement('button');
    abrirFicha.className = 'estreno-poster';
    abrirFicha.type = 'button';
    abrirFicha.setAttribute('aria-label', 'Ver ficha de ' + pelicula.titulo);
    abrirFicha.appendChild(crearPoster(pelicula, false));
    abrirFicha.addEventListener('click', () => alAbrir(pelicula));
    tarjeta.appendChild(abrirFicha);

    const cuerpo = document.createElement('div');
    cuerpo.className = 'estreno-cuerpo';

    const titulo = document.createElement('h3');
    titulo.className = 'estreno-titulo';
    titulo.textContent = pelicula.titulo;

    const genero = document.createElement('p');
    genero.className = 'estreno-genero';
    genero.textContent = pelicula.genero;

    const fecha = document.createElement('span');
    fecha.className = 'estreno-fecha';
    fecha.textContent = pelicula.fecha_estreno || 'Sin fecha';

    cuerpo.append(titulo, genero, fecha);
    if (trailerDe(pelicula)) {
      cuerpo.appendChild(crearBotonTrailer(pelicula, alVerTrailer, 'boton-rojo'));
    }
    tarjeta.appendChild(cuerpo);
    return tarjeta;
  }));
}

function reproducirTrailer(titulo, idVideo) {
  $('trailer-titulo').textContent = titulo;
  $('video').src = `https://www.youtube-nocookie.com/embed/${idVideo}?autoplay=1&rel=0`;
  abrirModal('modal-trailer');
}

// Navegar a about:blank corta la reproducción del vídeo.
function detenerTrailer() {
  $('video').src = 'about:blank';
}

function dibujarFiltros(generoActivo, alElegir) {
  const contenedor = $('filtros');
  contenedor.replaceChildren();
  ['Todas', ...GENEROS].forEach((genero) => {
    const boton = document.createElement('button');
    boton.className = 'filtro' + (genero === generoActivo ? ' activo' : '');
    boton.type = 'button';
    boton.textContent = genero;
    boton.addEventListener('click', () => alElegir(genero));
    contenedor.appendChild(boton);
  });
}

// Estados: 'cargando', 'vacio', 'error' o 'listo'.
function mostrarEstado(estado) {
  $('estado-cargando').classList.toggle('oculto', estado !== 'cargando');
  $('estado-vacio').classList.toggle('oculto', estado !== 'vacio');
  $('estado-error').classList.toggle('oculto', estado !== 'error');
  $('cartelera').classList.toggle('oculto', estado !== 'listo');
}

function abrirModal(id) {
  $(id).classList.add('activo');
}

function cerrarModal(id) {
  $(id).classList.remove('activo');
  if (id === 'modal-trailer') detenerTrailer();
}

function cerrarModales() {
  document.querySelectorAll('.modal.activo').forEach((modal) => modal.classList.remove('activo'));
  detenerTrailer();
}

function mostrarDetalle(pelicula) {
  $('detalle-poster').replaceChildren(crearPoster(pelicula, false));
  $('detalle-titulo').textContent = pelicula.titulo;
  $('detalle-datos').textContent = `${pelicula.genero} · ${pelicula.anio}`;
  $('detalle-estrellas').textContent = esProximamente(pelicula)
    ? 'Estreno: ' + (pelicula.fecha_estreno || 'por confirmar')
    : `${estrellas(pelicula.calificacion)} ${pelicula.calificacion.toFixed(1)}/10`;
  $('detalle-director').textContent = pelicula.director;
  $('detalle-sinopsis').textContent = pelicula.sinopsis || 'Sin sinopsis disponible.';
  const hayPlataformas = listaPlataformas(pelicula).length > 0;
  $('detalle-donde-etiqueta').classList.toggle('oculto', !hayPlataformas);
  $('detalle-donde').replaceChildren(crearPlataformas(pelicula, ''));
  $('btn-trailer').classList.toggle('oculto', !trailerDe(pelicula));
  abrirModal('modal-detalle');
}

function actualizarSesion() {
  const hay = haySesion();
  $('btn-sesion').textContent = hay ? 'Cerrar sesión' : 'Iniciar sesión';
  $('btn-registro').classList.toggle('oculto', hay);
  // El panel solo se ofrece a quien administra; el servidor lo vuelve a comprobar.
  $('enlace-admin').classList.toggle('oculto', !(hay && esAdmin()));
}

function dibujarPerfiles(perfiles, activo, acciones) {
  const lista = $('lista-perfiles');
  lista.replaceChildren();

  if (!perfiles.length) {
    const aviso = document.createElement('p');
    aviso.className = 'sin-perfiles';
    aviso.textContent = 'Todavía no hay perfiles. Crea el primero aquí abajo.';
    lista.appendChild(aviso);
  }

  perfiles.forEach((perfil) => {
    const caja = document.createElement('div');

    const boton = document.createElement('button');
    boton.className = 'perfil' + (String(perfil.id) === String(activo) ? ' activo' : '');
    boton.type = 'button';
    const nombre = document.createElement('span');
    nombre.textContent = (perfil.tiene_clave ? '🔒 ' : '') + perfil.nombre;
    boton.append(crearAvatar(perfil.avatar, perfil.nombre), nombre);
    boton.addEventListener('click', () => acciones.alElegir(perfil));

    const acciones2 = document.createElement('div');
    acciones2.className = 'perfil-acciones';
    [['Editar', acciones.alEditar], ['Eliminar', acciones.alBorrar]]
      .forEach(([texto, accion]) => {
        const chico = document.createElement('button');
        chico.className = 'perfil-borrar';
        chico.type = 'button';
        chico.textContent = texto;
        chico.addEventListener('click', () => accion(perfil));
        acciones2.appendChild(chico);
      });

    caja.append(boton, acciones2);
    lista.appendChild(caja);
  });
}

function dibujarOpcionesAvatar(elegido, alElegir) {
  const caja = $('elegir-avatar');
  caja.replaceChildren();
  GALERIA.forEach((avatar) => {
    const boton = document.createElement('button');
    boton.className = 'opcion-avatar' + (avatar.id === elegido ? ' activo' : '');
    boton.type = 'button';
    boton.setAttribute('aria-label', avatar.id);
    boton.appendChild(crearAvatar(avatar.id, avatar.id));
    boton.addEventListener('click', () => alElegir(avatar.id));
    caja.appendChild(boton);
  });
}

// Con sesión siempre se ve el chip: con el perfil activo o invitando a elegir uno.
function actualizarChipPerfil(perfil) {
  const chip = $('btn-perfil');
  chip.classList.toggle('oculto', !haySesion());
  const nombre = document.createElement('span');
  nombre.textContent = perfil ? perfil.nombre : 'Elegir perfil';
  chip.replaceChildren(crearAvatar(perfil ? perfil.avatar : 'fantasma'), nombre);
}

// Botones de "ya la vi / viendo / no me interesa" dentro del detalle.
function actualizarMarcas(estadoActual, hayPerfil) {
  $('detalle-marcas').classList.toggle('oculto', !hayPerfil);
  document.querySelectorAll('.marca').forEach((boton) => {
    boton.classList.toggle('activa', boton.dataset.estado === estadoActual);
  });
}

// El código HTTP se muestra junto al mensaje que devolvió la API.
function mostrarAviso(mensaje, tipo, codigo) {
  const aviso = document.createElement('div');
  aviso.className = 'aviso' + (tipo === 'exito' ? ' aviso-exito' : '');

  if (codigo) {
    const etiqueta = document.createElement('span');
    etiqueta.className = 'aviso-codigo';
    etiqueta.textContent = codigo;
    aviso.appendChild(etiqueta);
  }
  const texto = document.createElement('span');
  texto.textContent = mensaje;
  aviso.appendChild(texto);

  $('avisos').appendChild(aviso);
  setTimeout(() => aviso.remove(), 5000);
}

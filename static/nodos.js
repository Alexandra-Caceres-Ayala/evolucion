/*
 * Red de nodos animada para la sección de bienvenida (el "anuncio").
 * Réplica ligera y propia del efecto de partículas del portafolio de
 * Alexandra (que usa tsParticles, ~200 KB) escrita en ~70 líneas de
 * canvas puro, sin librerías externas. Nodos a la deriva que se conectan
 * con líneas cuando están cerca, con un brillo tenue que palpita.
 * Respeta prefers-reduced-motion (dibuja un solo fotograma estático).
 */
(function () {
  var contenedor = document.querySelector(".boletin-anuncio");
  if (!contenedor) return;
  var canvas = contenedor.querySelector(".nodos-canvas");
  if (!canvas || !canvas.getContext) return;

  var ctx = canvas.getContext("2d");
  var reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Paleta violeta/azul: guiño a la marca personal (rosa/púrpura del
  // portafolio) sin abandonar del todo la gama fría del boletín.
  var COLORES = ["#c9a0dc", "#a084c9", "#8b6fb8", "#7c9fd6"];
  var DISTANCIA_ENLACE = 130;

  var particulas = [];
  var ancho = 0, alto = 0;

  function dimensionar() {
    var dpr = window.devicePixelRatio || 1;
    ancho = contenedor.clientWidth;
    alto = contenedor.clientHeight;
    canvas.width = ancho * dpr;
    canvas.height = alto * dpr;
    canvas.style.width = ancho + "px";
    canvas.style.height = alto + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    crear();
  }

  function crear() {
    var cantidad = Math.max(18, Math.min(60, Math.round((ancho * alto) / 13000)));
    particulas = [];
    for (var i = 0; i < cantidad; i++) {
      particulas.push({
        x: Math.random() * ancho,
        y: Math.random() * alto,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: 1 + Math.random() * 1.6,
        color: COLORES[Math.floor(Math.random() * COLORES.length)],
        fase: Math.random() * Math.PI * 2,
      });
    }
  }

  function dibujar(t) {
    ctx.clearRect(0, 0, ancho, alto);

    for (var i = 0; i < particulas.length; i++) {
      var a = particulas[i];
      for (var j = i + 1; j < particulas.length; j++) {
        var b = particulas[j];
        var dx = a.x - b.x, dy = a.y - b.y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < DISTANCIA_ENLACE) {
          ctx.strokeStyle = "rgba(160,132,201," + (0.18 * (1 - d / DISTANCIA_ENLACE)) + ")";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    for (var k = 0; k < particulas.length; k++) {
      var p = particulas[k];
      ctx.globalAlpha = 0.35 + 0.28 * Math.sin(t / 1100 + p.fase);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
  }

  function mover() {
    for (var i = 0; i < particulas.length; i++) {
      var p = particulas[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > ancho) p.vx *= -1;
      if (p.y < 0 || p.y > alto) p.vy *= -1;
    }
  }

  function bucle(t) {
    mover();
    dibujar(t);
    requestAnimationFrame(bucle);
  }

  dimensionar();
  window.addEventListener("resize", dimensionar);
  // La altura de la tarjeta puede cambiar cuando terminan de cargar las
  // fuentes; recalculamos para que el lienzo cubra todo el bloque.
  window.addEventListener("load", dimensionar);

  // Un primer fotograma siempre, aunque requestAnimationFrame tarde en
  // arrancar (p. ej. si la pestaña carga en segundo plano).
  dibujar(0);

  if (!reducirMovimiento) {
    requestAnimationFrame(bucle);
  }
})();

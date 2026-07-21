"""Capa SEO/social: imagen Open Graph, sitemap, robots.txt y RSS.

Todo se genera a partir de la lista de boletines y de la URL del sitio,
así que se mantiene solo con reescribir el sitio. La imagen OG es la
que LinkedIn/redes usan para la tarjeta de vista previa al compartir.
"""

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

DIR_ASSETS = Path(__file__).resolve().parent / "assets"

# --- Imagen Open Graph (1200x630) para la tarjeta de LinkedIn ---------------

FONDO = (20, 23, 26)         # #14171a, el fondo oscuro del sitio
ACENTO = (110, 168, 224)     # #6ea8e0
TEXTO = (232, 232, 232)      # #e8e8e8
GRIS = (154, 154, 154)       # #9a9a9a


def _nodos_decorativos(draw: ImageDraw.ImageDraw, ancho: int, alto: int) -> None:
    """Dibuja una red de nodos tenue de fondo, como en la cabecera."""
    puntos = [
        (90, 110), (300, 70), (520, 150), (760, 90),
        (980, 170), (1130, 80), (200, 300), (620, 500),
        (900, 420), (1080, 540),
    ]
    enlaces = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 6), (2, 7), (4, 8), (8, 9)]
    for a, b in enlaces:
        draw.line([puntos[a], puntos[b]], fill=(46, 60, 78), width=2)
    for x, y in puntos:
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(60, 84, 112))


def generar_imagen_og(ruta_salida: Path) -> None:
    ancho, alto = 1200, 630
    img = Image.new("RGB", (ancho, alto), FONDO)
    draw = ImageDraw.Draw(img)
    _nodos_decorativos(draw, ancho, alto)

    fuente_titulo = ImageFont.truetype(str(DIR_ASSETS / "SpaceGrotesk-Bold.ttf"), 150)
    fuente_sub = ImageFont.truetype(str(DIR_ASSETS / "SpaceGrotesk-Medium.ttf"), 42)
    fuente_pie = ImageFont.truetype(str(DIR_ASSETS / "SpaceGrotesk-Medium.ttf"), 30)

    margen = 90
    draw.text((margen, 210), "EVOLUCIÓN", font=fuente_titulo, fill=ACENTO)
    draw.text((margen + 6, 380), "Observatorio del Ecosistema del Dato", font=fuente_sub, fill=TEXTO)
    draw.text(
        (margen + 6, 470),
        "Data Analytics · BI · IA  —  España, Europa y tendencias globales",
        font=fuente_pie, fill=GRIS,
    )

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    img.save(ruta_salida, "PNG")


# --- sitemap.xml ------------------------------------------------------------

def generar_sitemap(url_sitio: str, rutas: list[tuple[str, str]]) -> str:
    """rutas: lista de (ruta_relativa, fecha_iso). ruta_relativa "" = home."""
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for ruta, fecha in rutas:
        loc = url_sitio + ruta
        lineas.append("  <url>")
        lineas.append(f"    <loc>{escape(loc)}</loc>")
        if fecha:
            lineas.append(f"    <lastmod>{fecha}</lastmod>")
        lineas.append("  </url>")
    lineas.append("</urlset>")
    return "\n".join(lineas) + "\n"


# --- robots.txt -------------------------------------------------------------

def generar_robots(url_sitio: str) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {url_sitio}sitemap.xml\n"
    )


# --- RSS 2.0 ----------------------------------------------------------------

def _fecha_rss(fecha) -> str:
    dt = datetime(fecha.year, fecha.month, fecha.day, 9, 0, 0, tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def generar_rss(url_sitio: str, boletines: list[dict]) -> str:
    ahora = _fecha_rss(boletines[0]["fecha"]) if boletines else ""
    items = []
    for b in boletines:
        enlace = url_sitio + b["url"]
        items.append(
            "    <item>\n"
            f"      <title>{escape(b['titulo'])}</title>\n"
            f"      <link>{escape(enlace)}</link>\n"
            f"      <guid isPermaLink=\"true\">{escape(enlace)}</guid>\n"
            f"      <pubDate>{_fecha_rss(b['fecha'])}</pubDate>\n"
            f"      <description>{escape(b['resumen'])}</description>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>EVOLUCIÓN — Observatorio del Ecosistema del Dato</title>\n"
        f"    <link>{escape(url_sitio)}</link>\n"
        "    <description>Documentando, día a día, la evolución de Python, SQL, Power BI, "
        "IA y las tecnologías que están transformando la analítica de datos.</description>\n"
        "    <language>es</language>\n"
        f"    <lastBuildDate>{ahora}</lastBuildDate>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )

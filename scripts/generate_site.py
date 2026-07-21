#!/usr/bin/env python3
"""
Genera el sitio estático a partir de los boletines en Markdown.

Uso:
    python3 scripts/generate_site.py

Lee cada archivo en boletines/*.md (frontmatter YAML + cuerpo Markdown),
y escribe HTML estático en docs/ (servido por GitHub Pages).

Este script es la única pieza que traduce "Markdown" a "sitio publicado".
Escribir un boletín nuevo y volver a ejecutar este script es todo el
trabajo manual necesario para publicar.
"""

import hashlib
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

from comun import extraer_titulares, fecha_legible, paginas_visibles
from graficos import construir_grafico
from seo import generar_imagen_og, generar_robots, generar_rss, generar_sitemap

# URL pública final del sitio (GitHub Pages). Es la única fuente de verdad
# para las URLs absolutas de sitemap, RSS, canónicas y Open Graph. Si cambia
# el nombre del repo o se pone un dominio propio, se ajusta solo aquí.
URL_SITIO = "https://alexandra-caceres-ayala.github.io/evolucion/"
TITULO_SITIO = "EVOLUCIÓN — Observatorio del Ecosistema del Dato"
DESCRIPCION_SITIO = (
    "Documentando, día a día, la evolución de Python, SQL, Power BI, IA y "
    "las tecnologías que están transformando la analítica de datos."
)

PATRON_ENLACE_EXTERNO = re.compile(r'<a href="(https?://[^"]+)"')

# Íconos pequeños (heredan el color de acento) para señalar el enfoque
# geográfico de cada sección del boletín: un pin para la sección
# regional (España/Europa) y un globo para la de tendencias globales.
ICONO_REGION = (
    '<svg class="icono-seccion" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M12 2C8.1 2 5 5.1 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.9-3.1-7-7-7z"'
    ' fill="none" stroke="currentColor" stroke-width="2"/>'
    '<circle cx="12" cy="9" r="2.5" fill="currentColor"/>'
    "</svg>"
)
ICONO_GLOBAL = (
    '<svg class="icono-seccion" viewBox="0 0 24 24" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<ellipse cx="12" cy="12" rx="4" ry="9" fill="none" stroke="currentColor" stroke-width="1.5"/>'
    '<line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="1.5"/>'
    "</svg>"
)
PATRON_H2 = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)


def abrir_en_pestana_nueva(html: str) -> str:
    """Los enlaces "Fuente" del cuerpo son siempre externos: se abren en
    pestaña nueva para no sacar al lector del sitio."""
    return PATRON_ENLACE_EXTERNO.sub(
        r'<a href="\1" target="_blank" rel="noopener noreferrer"', html
    )


def marcar_secciones_geograficas(html: str) -> str:
    """Antepone un ícono a los encabezados de sección según su enfoque:
    pin para "España y Europa", globo para "Tendencias Globales". Se
    detecta por el texto, así aplica a todos los boletines sin editarlos."""

    def reemplazar(coincidencia: re.Match) -> str:
        contenido = coincidencia.group(1)
        texto = contenido.lower()
        if "españa" in texto or "europa" in texto:
            return f"<h2>{ICONO_REGION}{contenido}</h2>"
        if "global" in texto:
            return f"<h2>{ICONO_GLOBAL}{contenido}</h2>"
        return coincidencia.group(0)

    return PATRON_H2.sub(reemplazar, html)


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIR_BOLETINES = RAIZ_PROYECTO / "boletines"          # boletines diarios importados de los crudos
DIR_FIJOS = RAIZ_PROYECTO / "boletines-fijos"        # boletines escritos a mano (p. ej. la bienvenida)
DIR_PLANTILLAS = RAIZ_PROYECTO / "templates"
DIR_ESTATICOS = RAIZ_PROYECTO / "static"
DIR_SALIDA = RAIZ_PROYECTO / "docs"

BOLETINES_POR_PAGINA = 10


def leer_boletin(ruta_md: Path) -> dict:
    """Parsea un archivo de boletín: frontmatter YAML delimitado por '---' + cuerpo Markdown."""
    texto = ruta_md.read_text(encoding="utf-8")
    partes = texto.split("---", 2)
    if len(partes) < 3:
        raise ValueError(
            f"{ruta_md.name}: falta el frontmatter YAML (debe empezar y cerrar con '---')"
        )
    metadatos = yaml.safe_load(partes[1]) or {}
    cuerpo_md = partes[2].strip()

    for campo in ("titulo", "fecha", "resumen"):
        if campo not in metadatos:
            raise ValueError(f"{ruta_md.name}: falta el campo obligatorio '{campo}' en el frontmatter")

    fecha = metadatos["fecha"]
    if not isinstance(fecha, date):
        raise ValueError(f"{ruta_md.name}: 'fecha' debe tener formato AAAA-MM-DD")

    slug = ruta_md.stem

    return {
        "titulo": metadatos["titulo"],
        "fecha": fecha,
        "fecha_legible": fecha_legible(fecha),
        "resumen": metadatos["resumen"],
        "cuerpo_md": cuerpo_md,
        "tipo": metadatos.get("tipo"),
        "etiquetas": metadatos.get("etiquetas", []),
        "autor": metadatos.get("autor", "Alexandra Cáceres Ayala"),
        "slug": slug,
        "url": f"boletines/{slug}.html",
        "tldr": extraer_titulares(cuerpo_md, cantidad=3),
        "cuerpo_html": marcar_secciones_geograficas(
            abrir_en_pestana_nueva(markdown.markdown(cuerpo_md, extensions=["extra"]))
        ),
    }


def indexar_buscador() -> None:
    """Construye el índice de búsqueda de Pagefind sobre docs/ ya generado."""
    resultado = subprocess.run(
        [sys.executable, "-m", "pagefind", "--site", str(DIR_SALIDA)],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        print(resultado.stdout, resultado.stderr, file=sys.stderr)
        raise RuntimeError("Falló la indexación de Pagefind")


def cargar_boletines() -> list[dict]:
    archivos = sorted(DIR_BOLETINES.glob("*.md")) + sorted(DIR_FIJOS.glob("*.md"))
    if not archivos:
        print("Aviso: no hay boletines. No se genera nada.", file=sys.stderr)
    boletines = [leer_boletin(ruta) for ruta in archivos]
    boletines.sort(key=lambda b: b["fecha"], reverse=True)
    # Los anuncios (p. ej. la bienvenida) quedan anclados arriba del todo,
    # antes de los boletines diarios. El orden por fecha se conserva dentro
    # de cada grupo porque sort() de Python es estable.
    boletines.sort(key=lambda b: b.get("tipo") != "Anuncio")
    return boletines


def generar_sitio(boletines: list[dict]) -> None:
    if DIR_SALIDA.exists():
        shutil.rmtree(DIR_SALIDA)
    (DIR_SALIDA / "boletines").mkdir(parents=True)

    shutil.copytree(DIR_ESTATICOS, DIR_SALIDA / "static")

    # Cambia en cada edición de style.css, así el navegador nunca sirve
    # una versión vieja cacheada del CSS bajo la misma URL.
    version_css = hashlib.md5((DIR_ESTATICOS / "style.css").read_bytes()).hexdigest()[:8]

    specs = construir_grafico(boletines)
    if specs:
        dir_graficos = DIR_SALIDA / "static" / "graficos"
        dir_graficos.mkdir(parents=True, exist_ok=True)
        for tema, chart in specs.items():
            (dir_graficos / f"menciones-herramientas.{tema}.json").write_text(
                chart.to_json(), encoding="utf-8"
            )

    entorno = Environment(loader=FileSystemLoader(DIR_PLANTILLAS))
    anio_actual = date.today().year

    paginas = [
        boletines[i : i + BOLETINES_POR_PAGINA]
        for i in range(0, len(boletines), BOLETINES_POR_PAGINA)
    ] or [[]]
    total_paginas = len(paginas)

    comun = {"version_css": version_css, "url_sitio": URL_SITIO}

    plantilla_indice = entorno.get_template("index.html")
    for numero, pagina in enumerate(paginas, start=1):
        nombre_archivo = "index.html" if numero == 1 else f"index-{numero}.html"
        url_canonica = URL_SITIO if numero == 1 else URL_SITIO + nombre_archivo
        titulo = TITULO_SITIO if numero == 1 else f"{TITULO_SITIO} — página {numero}"
        (DIR_SALIDA / nombre_archivo).write_text(
            plantilla_indice.render(
                boletines=pagina, raiz="", anio_actual=anio_actual,
                hay_grafico=bool(specs) and numero == 1,
                pagina_actual=numero, total_paginas=total_paginas,
                paginas_visibles=paginas_visibles(numero, total_paginas),
                meta_titulo=titulo, meta_descripcion=DESCRIPCION_SITIO,
                url_canonica=url_canonica, og_tipo="website", **comun,
            ),
            encoding="utf-8",
        )

    plantilla_boletin = entorno.get_template("post.html")
    for boletin in boletines:
        salida = DIR_SALIDA / boletin["url"]
        salida.write_text(
            plantilla_boletin.render(
                boletin=boletin, raiz="../", anio_actual=anio_actual,
                meta_titulo=boletin["titulo"], meta_descripcion=boletin["resumen"],
                url_canonica=URL_SITIO + boletin["url"], og_tipo="article", **comun,
            ),
            encoding="utf-8",
        )

    generar_extras_seo(boletines, paginas)

    # GitHub Pages no debe procesar la carpeta con Jekyll.
    (DIR_SALIDA / ".nojekyll").touch()


def generar_extras_seo(boletines: list[dict], paginas: list[list[dict]]) -> None:
    """Imagen Open Graph (tarjeta de LinkedIn), sitemap, robots y RSS."""
    generar_imagen_og(DIR_SALIDA / "static" / "og-image.png")

    hoy = date.today().isoformat()
    rutas = [("", hoy)]
    for numero in range(2, len(paginas) + 1):
        rutas.append((f"index-{numero}.html", hoy))
    for boletin in boletines:
        rutas.append((boletin["url"], boletin["fecha"].isoformat()))

    (DIR_SALIDA / "sitemap.xml").write_text(generar_sitemap(URL_SITIO, rutas), encoding="utf-8")
    (DIR_SALIDA / "robots.txt").write_text(generar_robots(URL_SITIO), encoding="utf-8")
    (DIR_SALIDA / "rss.xml").write_text(generar_rss(URL_SITIO, boletines), encoding="utf-8")


def main() -> None:
    boletines = cargar_boletines()
    generar_sitio(boletines)
    indexar_buscador()
    print(f"Sitio generado en docs/ con {len(boletines)} boletín(es).")


if __name__ == "__main__":
    main()

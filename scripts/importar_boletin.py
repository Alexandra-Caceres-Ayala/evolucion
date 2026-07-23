#!/usr/bin/env python3
"""
Importa boletines crudos generados por la skill "boletin-diario-datos"
(carpeta "Noticias Data Analytics") y los convierte al formato con
frontmatter que espera generate_site.py, dentro de boletines/.

Uso:
    python3 scripts/importar_boletin.py
        Importa cualquier boletin-AAAA-MM-DD.md nuevo desde la carpeta
        de origen (no reimporta los que ya existen en boletines/).

    python3 scripts/importar_boletin.py <ruta1.md> <ruta2.md> ...
        Importa archivos concretos, pasados explícitamente.

Es un paso de traducción, no de redacción: no reescribe el contenido
que investigó la skill, solo le añade los metadatos (frontmatter,
etiquetas, enlaces) que la web necesita para publicarlo.
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

from comun import extraer_titulares, fecha_legible

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DIR_BOLETINES = RAIZ_PROYECTO / "boletines"

# De dónde se leen los boletines crudos (los que produce la skill).
# En el repo/CI existe "boletines-crudos/" (lo que llega al repositorio
# con la subida automática diaria); en local, si no existe, se usa la
# carpeta donde se generan los boletines.
_CRUDOS_REPO = RAIZ_PROYECTO / "boletines-crudos"
DIR_ORIGEN = _CRUDOS_REPO if _CRUDOS_REPO.exists() else (RAIZ_PROYECTO.parent / "Noticias Data Analytics")

AUTOR = "Alexandra Cáceres Ayala"
TIPO = "Boletín diario"

# Vocabulario de herramientas que reconoce el importador para generar
# etiquetas automáticamente. Búsqueda insensible a mayúsculas, con
# límites de palabra para evitar falsos positivos (p. ej. "IA" dentro
# de otra palabra).
ETIQUETAS_RECONOCIDAS = {
    "python": "python",
    "sql": "sql",
    "power bi": "power-bi",
    "microsoft fabric": "microsoft-fabric",
    "tableau": "tableau",
    "snowflake": "snowflake",
    "databricks": "databricks",
    "dbt": "dbt",
    "duckdb": "duckdb",
    "polars": "polars",
    "pandas": "pandas",
    "spark": "spark",
    "anaconda": "anaconda",
    "inteligencia artificial": "ia",
    r"\bia\b": "ia",
    "business intelligence": "business-intelligence",
}

# Nombres de presentación de cada tecnología reconocida. Los usa el
# gráfico de menciones (scripts/graficos.py) para mostrar etiquetas
# legibles en vez de slugs.
NOMBRE_VISIBLE = {
    "python": "Python",
    "sql": "SQL",
    "power-bi": "Power BI",
    "microsoft-fabric": "Microsoft Fabric",
    "tableau": "Tableau",
    "snowflake": "Snowflake",
    "databricks": "Databricks",
    "dbt": "dbt",
    "duckdb": "DuckDB",
    "polars": "Polars",
    "pandas": "Pandas",
    "spark": "Spark",
    "anaconda": "Anaconda",
    "ia": "IA",
}

PATRON_NEGRITA = re.compile(r"\*\*([^*\n]+)\*\*")

PATRON_URL_SUELTA = re.compile(
    r"^([ \t]*)(?:-\s*)?(?:Fuente:?\s*)?(https?://\S+)[ \t]*$", re.MULTILINE | re.IGNORECASE
)
# Nota de cierre que la skill añade cada día en cursiva, con redacción
# variable ("Filtro aplicado...", "Nota del boletín: se ha aplicado el
# filtro...", "Boletín generado automáticamente..."). Se elimina: la web
# ya muestra su propio aviso fijo en la plantilla. Reconoce cualquier
# bloque en cursiva al final que mencione el filtro/exclusión.
PATRON_NOTA_FILTRO = re.compile(
    r"\n*(?:-{3,}\s*)?"
    r"\*[^*]*?(?:filtro|criptomoneda|trading|exclusi[oó]n|econom[ií]a general)[^*]*?\*"
    r"\s*$",
    re.IGNORECASE | re.DOTALL,
)


def extraer_etiquetas(texto: str) -> list[str]:
    texto_min = texto.lower()
    encontradas = []
    for patron, etiqueta in ETIQUETAS_RECONOCIDAS.items():
        expresion = patron if patron.startswith(r"\b") else re.escape(patron)
        if re.search(expresion, texto_min) and etiqueta not in encontradas:
            encontradas.append(etiqueta)
    return encontradas


def extraer_resumen(cuerpo: str) -> str:
    titulares = extraer_titulares(cuerpo, cantidad=999)
    if not titulares:
        return "Resumen diario de noticias y tendencias en Data Analytics y Business Intelligence."
    principales = [t.rstrip(" .:;") for t in titulares[:2]]
    resumen = "; ".join(principales)
    resumen += " y más." if len(titulares) > 2 else "."
    return resumen


def limpiar_cuerpo(texto: str) -> str:
    lineas = texto.strip().splitlines()

    # Quita el título (H1) y la línea de fecha en negrita que ya cubre
    # la plantilla con "titulo" y "fecha_legible" del frontmatter.
    while lineas and (lineas[0].startswith("# ") or lineas[0].strip().startswith("*") or not lineas[0].strip() or lineas[0].strip() == "---"):
        if lineas[0].startswith("# ") or lineas[0].strip().startswith("*"):
            lineas.pop(0)
            continue
        if not lineas[0].strip() or lineas[0].strip() == "---":
            lineas.pop(0)
            continue
        break

    cuerpo = "\n".join(lineas).strip()

    # Quita la nota editorial repetida: ahora vive en la plantilla.
    cuerpo = PATRON_NOTA_FILTRO.sub("", cuerpo).strip()
    cuerpo = cuerpo.rstrip("-").strip()

    # Convierte URLs sueltas en enlaces Markdown reales.
    cuerpo = PATRON_URL_SUELTA.sub(r"\1[Fuente](\2)", cuerpo)

    return cuerpo


def _ya_reconocido(termino: str) -> bool:
    termino_min = termino.lower()
    return any(
        re.search(patron if patron.startswith(r"\b") else re.escape(patron), termino_min)
        for patron in ETIQUETAS_RECONOCIDAS
    )


def _candidatos_nuevas_herramientas(texto: str) -> set[str]:
    """Términos en negrita, cortos y sin punto final -- nombres de producto
    resaltados dentro de un párrafo (p. ej. "**DuckDB**"), a diferencia del
    titular completo de cada viñeta, que también va en negrita pero termina
    en punto (p. ej. "**Power BI incorpora....**")."""
    candidatos = set()
    for termino in PATRON_NEGRITA.findall(texto):
        termino = termino.strip()
        if not termino or termino.endswith("."):
            continue
        palabras = termino.split()
        if not (1 <= len(palabras) <= 4) or len(termino) > 40:
            continue
        if not re.search(r"[A-ZÁÉÍÓÚ]", termino):
            continue
        candidatos.add(termino)
    return candidatos


def sugerir_herramientas_nuevas(rutas: list[Path]) -> None:
    """Avisa (sin modificar nada) de términos resaltados que se repiten en
    varios boletines y no están en ETIQUETAS_RECONOCIDAS -- posibles
    herramientas nuevas que todavía no cuenta el gráfico de menciones."""
    apariciones: dict[str, int] = {}
    for ruta in rutas:
        texto = ruta.read_text(encoding="utf-8")
        candidatos = {t for t in _candidatos_nuevas_herramientas(texto) if not _ya_reconocido(t)}
        for termino in candidatos:
            apariciones[termino] = apariciones.get(termino, 0) + 1

    recurrentes = sorted(
        ((termino, n) for termino, n in apariciones.items() if n >= 2),
        key=lambda par: -par[1],
    )
    if not recurrentes:
        return

    print(
        "\nSugerencia: estos términos resaltados se repiten en varios boletines "
        "y no están en la lista de herramientas reconocidas. Si alguno es una "
        "herramienta relevante, añádela a ETIQUETAS_RECONOCIDAS / NOMBRE_VISIBLE "
        "en scripts/importar_boletin.py:",
        file=sys.stderr,
    )
    for termino, n in recurrentes:
        print(f"  - {termino} (en {n} boletines)", file=sys.stderr)


def construir_frontmatter(
    fecha: date, titulo: str, resumen: str, etiquetas: list[str]
) -> str:
    lista_etiquetas = "[" + ", ".join(etiquetas) + "]" if etiquetas else "[]"
    resumen_escapado = resumen.replace('"', "'")
    titulo_escapado = titulo.replace('"', "'")
    return (
        "---\n"
        f'titulo: "{titulo_escapado}"\n'
        f"fecha: {fecha.isoformat()}\n"
        f'resumen: "{resumen_escapado}"\n'
        f'tipo: "{TIPO}"\n'
        f"etiquetas: {lista_etiquetas}\n"
        f'autor: "{AUTOR}"\n'
        "---\n\n"
    )


def importar(ruta_origen: Path) -> Path:
    coincidencia = re.search(r"(\d{4}-\d{2}-\d{2})", ruta_origen.stem)
    if not coincidencia:
        raise ValueError(f"{ruta_origen.name}: no se encontró una fecha AAAA-MM-DD en el nombre del archivo")
    fecha = datetime.strptime(coincidencia.group(1), "%Y-%m-%d").date()

    texto_original = ruta_origen.read_text(encoding="utf-8")
    cuerpo = limpiar_cuerpo(texto_original)
    resumen = extraer_resumen(cuerpo)
    etiquetas = extraer_etiquetas(texto_original)
    titulo = f"Boletín Diario de Data Analytics — {fecha_legible(fecha)}"

    contenido_final = construir_frontmatter(fecha, titulo, resumen, etiquetas) + cuerpo + "\n"

    ruta_destino = DIR_BOLETINES / f"boletin-{fecha.isoformat()}.md"
    ruta_destino.write_text(contenido_final, encoding="utf-8")
    return ruta_destino


def main() -> None:
    DIR_BOLETINES.mkdir(parents=True, exist_ok=True)

    rutas_explicitas = [Path(arg) for arg in sys.argv[1:]]

    if rutas_explicitas:
        candidatos = rutas_explicitas
    else:
        if not DIR_ORIGEN.exists():
            print(f"Aviso: no existe la carpeta de origen {DIR_ORIGEN}", file=sys.stderr)
            return
        candidatos = sorted(DIR_ORIGEN.glob("boletin-*.md"))

    importados = 0
    for ruta_origen in candidatos:
        coincidencia = re.search(r"(\d{4}-\d{2}-\d{2})", ruta_origen.stem)
        if coincidencia and not rutas_explicitas:
            destino_esperado = DIR_BOLETINES / f"boletin-{coincidencia.group(1)}.md"
            if destino_esperado.exists():
                continue  # ya importado, no se pisa una edición manual posterior
        ruta_destino = importar(ruta_origen)
        print(f"Importado: {ruta_origen.name} -> {ruta_destino.relative_to(RAIZ_PROYECTO)}")
        importados += 1

    print(f"{importados} boletín(es) importado(s).")

    if DIR_ORIGEN.exists():
        sugerir_herramientas_nuevas(sorted(DIR_ORIGEN.glob("boletin-*.md")))


if __name__ == "__main__":
    main()

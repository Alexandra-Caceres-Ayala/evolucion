"""Utilidades compartidas entre generate_site.py e importar_boletin.py."""

import re
from datetime import date

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def fecha_legible(fecha: date) -> str:
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def extraer_titulares(cuerpo_md: str, cantidad: int) -> list[str]:
    """Extrae los primeros titulares en negrita ("- **Titular.** ...") de un boletín."""
    titulares = re.findall(r"^- \*\*(.+?)\*\*", cuerpo_md, re.MULTILINE)
    return [t.rstrip(" .:;") + "." for t in titulares[:cantidad]]


def paginas_visibles(actual: int, total: int, vecinos: int = 1) -> list[int | None]:
    """Números de página a mostrar en el paginador: siempre primera, última,
    la actual y sus vecinas; el resto se resume con None (puntos suspensivos),
    para no listar cientos de páginas cuando el archivo crezca."""
    if total <= 5 + vecinos * 2:
        return list(range(1, total + 1))

    conjunto = {1, total, actual}
    conjunto.update(p for p in range(actual - vecinos, actual + vecinos + 1) if 1 <= p <= total)

    ordenadas = sorted(conjunto)
    resultado: list[int | None] = []
    anterior = None
    for pagina in ordenadas:
        if anterior is not None and pagina - anterior > 1:
            resultado.append(None)
        resultado.append(pagina)
        anterior = pagina
    return resultado

#!/usr/bin/env python3
"""
Sube a GitHub (repositorio "evolucion") los boletines diarios que aún no
estén publicados, usando la API de GitHub — sin git ni terminal de git.

Diseño "a prueba de fallos": no depende de subir solo el de hoy. Compara la
carpeta local con lo que ya hay en el repo y sube TODO lo que falte. Así, si
algún día la subida no se ejecutó, la siguiente vez se pone al día sola.

Uso (un solo comando, pensado para la tarea programada diaria):
    python3 scripts/subir_boletin_github.py
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CARPETA_LOCAL = Path("/Users/alexandra/Claude/Projects/Noticias Data Analytics")
RUTA_TOKEN = CARPETA_LOCAL / "token-github-evolucion.txt"
OWNER, REPO = "Alexandra-Caceres-Ayala", "evolucion"
CARPETA_REPO = "boletines-crudos"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"


def _peticion(url, token, metodo="GET", cuerpo=None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    req = urllib.request.Request(
        url, data=datos, method=metodo,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "evolucion-uploader",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main() -> int:
    if not RUTA_TOKEN.exists():
        print(f"ERROR: no se encontró el token en {RUTA_TOKEN}", file=sys.stderr)
        return 1
    token = RUTA_TOKEN.read_text(encoding="utf-8").strip()

    # Lo que YA está en el repo.
    try:
        remoto = {f["name"] for f in _peticion(f"{API}/contents/{CARPETA_REPO}", token)}
    except urllib.error.HTTPError as e:
        print(f"ERROR al leer el repositorio: {e.code} {e.read().decode()}", file=sys.stderr)
        return 1

    locales = sorted(CARPETA_LOCAL.glob("boletin-*.md"))
    if not locales:
        print(f"Aviso: no hay boletines en {CARPETA_LOCAL}", file=sys.stderr)
        return 0

    subidos = 0
    for ruta in locales:
        if ruta.name in remoto:
            continue  # ya publicado
        fecha = ruta.stem.replace("boletin-", "")
        contenido_b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
        try:
            _peticion(
                f"{API}/contents/{CARPETA_REPO}/{ruta.name}", token, "PUT",
                {"message": f"Boletín automático {fecha}", "content": contenido_b64},
            )
            print(f"Subido: {ruta.name}")
            subidos += 1
        except urllib.error.HTTPError as e:
            print(f"ERROR al subir {ruta.name}: {e.code} {e.read().decode()}", file=sys.stderr)
            return 1

    if subidos:
        print(f"{subidos} boletín(es) subido(s). GitHub Actions reconstruirá la web.")
    else:
        print("Nada que subir: el repositorio ya está al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

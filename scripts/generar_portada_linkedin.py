#!/usr/bin/env python3
"""
Genera la imagen de portada del resumen semanal de EVOLUCIÓN para LinkedIn.

Es una plantilla de marca fija con datos variables: cada semana cambian la
fecha, los conteos y —sobre todo— la "palabra protagonista" (el tema que
marcó la semana). El marco visual se mantiene igual para que la portada sea
reconocible edición tras edición.

Uso:
    python3 generar_portada_linkedin.py \
        --tema "BI agéntico" \
        --fecha "14 – 21 de julio, 2026" \
        --boletines 8 \
        --tendencias 4 \
        --salida "/ruta/portada-linkedin-2026-07-21.png"

La "palabra protagonista" se auto-ajusta de tamaño, así que temas más largos
(p. ej. "Adopción de IA en producción") también encajan sin romper el diseño.
"""

import argparse
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DIR_ASSETS = Path(__file__).resolve().parent / "assets"
W, H = 1200, 630

# Paleta de marca (misma del sitio y de la animación de la bienvenida).
AZUL = (43, 108, 176)
AZUL_CL = (110, 168, 224)
VIOLETA = (91, 75, 138)
VIOLETA_CL = (160, 132, 201)
LILA = (201, 160, 220)
TINTA = (34, 40, 64)
GRIS = (91, 98, 112)


def fuente(sz: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    nombre = "SpaceGrotesk-Bold.ttf" if bold else "SpaceGrotesk-Medium.ttf"
    return ImageFont.truetype(str(DIR_ASSETS / nombre), sz)


def grad(w, h, c1, c2, modo="diag") -> Image.Image:
    if modo == "diag":
        x = np.linspace(0, 1, w)[None, :]
        y = np.linspace(0, 1, h)[:, None]
        t = (x + y) / 2
    else:  # horizontal
        t = np.repeat(np.linspace(0, 1, w)[None, :], h, 0)
    c1 = np.array(c1)
    c2 = np.array(c2)
    return Image.fromarray((c1 * (1 - t[..., None]) + c2 * t[..., None]).astype("uint8"), "RGB")


def texto_gradiente(img, xy, txt, font, c1, c2) -> None:
    g = grad(W, H, c1, c2, "h")
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text(xy, txt, font=font, fill=255)
    img.paste(g, (0, 0), mask)


def _blob(cx, cy, radio, color) -> Image.Image:
    y, x = np.ogrid[:H, :W]
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radio
    a = np.clip(1 - d, 0, 1) ** 1.6
    rgba = np.zeros((H, W, 4), "uint8")
    for i in range(3):
        rgba[..., i] = color[i]
    rgba[..., 3] = (a * 255).astype("uint8")
    return Image.fromarray(rgba, "RGBA")


def _ajustar_fuente(draw, txt, max_ancho, sz_max=112, sz_min=52) -> ImageFont.FreeTypeFont:
    sz = sz_max
    while sz > sz_min:
        f = fuente(sz, True)
        if draw.textlength(txt, font=f) <= max_ancho:
            return f
        sz -= 2
    return fuente(sz_min, True)


def generar_portada(tema, fecha, boletines, tendencias, ruta_salida) -> None:
    # La constelación varía de forma sutil según la semana (semilla derivada
    # de la fecha), pero es reproducible: misma fecha -> mismo patrón.
    semilla = int(hashlib.md5(fecha.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(semilla)

    # --- Fondo aurora: luces de color difuminadas sobre base clara ---------
    base = grad(W, H, (248, 248, 253), (243, 239, 251)).convert("RGBA")
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for b in (_blob(1060, 120, 520, AZUL_CL), _blob(1000, 560, 470, LILA),
              _blob(140, 600, 400, (150, 180, 230))):
        capa = Image.alpha_composite(capa, b)
    capa = capa.filter(ImageFilter.GaussianBlur(42))
    r, g, bb, al = capa.split()
    al = al.point(lambda v: int(v * 0.5))
    capa = Image.merge("RGBA", (r, g, bb, al))
    img = Image.alpha_composite(base, capa)

    # --- Constelación a la derecha ----------------------------------------
    cap_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cap_p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl, dp = ImageDraw.Draw(cap_l), ImageDraw.Draw(cap_p)
    paleta = [AZUL, VIOLETA, AZUL_CL]
    pts = [{"x": rng.uniform(760, 1170), "y": rng.uniform(70, 560),
            "r": rng.uniform(2.2, 3.8), "c": paleta[rng.integers(len(paleta))]}
           for _ in range(20)]
    for i, a in enumerate(pts):
        for b in pts[i + 1:]:
            d = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
            if d < 150:
                dl.line([(a["x"], a["y"]), (b["x"], b["y"])],
                        fill=VIOLETA_CL + (int(45 * (1 - d / 150)),), width=1)
    for p in pts:
        dp.ellipse([p["x"] - p["r"], p["y"] - p["r"], p["x"] + p["r"], p["y"] + p["r"]],
                   fill=p["c"] + (235,))
    img = Image.alpha_composite(img, cap_l)
    img = Image.alpha_composite(img, cap_p).convert("RGB")

    # --- Texto -------------------------------------------------------------
    d = ImageDraw.Draw(img)
    m = 80
    d.text((m, 74), "EVOLUCIÓN · RESUMEN SEMANAL", font=fuente(30, False), fill=AZUL)
    d.text((m, 120), fecha, font=fuente(40, True), fill=TINTA)
    d.text((m, 238), "EL TEMA QUE MARCÓ LA SEMANA", font=fuente(24, False), fill=GRIS)

    fh = _ajustar_fuente(d, tema, max_ancho=630)
    texto_gradiente(img, (m, 278), tema, fh, VIOLETA, AZUL)

    d = ImageDraw.Draw(img)
    d.text((m, 470), f"{boletines} boletines publicados", font=fuente(26, False), fill=GRIS)
    d.text((m, 510), f"{tendencias} grandes tendencias  ·  cobertura diaria en la web",
           font=fuente(26, False), fill=GRIS)

    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img.save(ruta, "PNG")


def main() -> None:
    p = argparse.ArgumentParser(description="Portada semanal de EVOLUCIÓN para LinkedIn.")
    p.add_argument("--tema", required=True, help='Palabra o frase corta del tema de la semana (p. ej. "BI agéntico").')
    p.add_argument("--fecha", required=True, help='Rango de fechas legible (p. ej. "14 – 21 de julio, 2026").')
    p.add_argument("--boletines", type=int, required=True, help="Número de boletines de la semana.")
    p.add_argument("--tendencias", type=int, required=True, help="Número de grandes tendencias del resumen.")
    p.add_argument("--salida", required=True, help="Ruta del PNG a generar.")
    args = p.parse_args()
    generar_portada(args.tema, args.fecha, args.boletines, args.tendencias, args.salida)
    print(f"Portada generada: {args.salida}")


if __name__ == "__main__":
    main()

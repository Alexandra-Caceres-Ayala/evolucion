"""Gráfico interactivo (Altair/Vega-Lite) de menciones por herramienta.

Sustituye a la versión estática de matplotlib: a cambio de cargar
~800 KB de JS (vega + vega-lite + vega-embed, vendorizados en
static/vendor/ para no depender de un CDN externo), el lector puede
pasar el ratón para ver el detalle exacto, hacer clic en una barra
del ranking para resaltar su tendencia en el tiempo, y hacer zoom/pan
sobre el eje de fechas. Decisión de diseño deliberada: priorizar la
interactividad sobre el peso de página para esta pieza.

El gráfico ocupa el ancho completo bajo la cabecera (width="container"),
no una tarjeta estrecha en el sidebar -- para darle a esta pieza el
protagonismo visual que merece como corazón analítico del sitio.
"""

import re

import pandas as pd
import altair as alt

from importar_boletin import ETIQUETAS_RECONOCIDAS, NOMBRE_VISIBLE

COLOR_APAGADO = "#c7d3de"

# Degradado sutil del azul del sitio hacia un violeta apagado: un
# guiño a la paleta rosa/púrpura de mi portafolio personal sin
# copiarla literalmente (mantiene la gama fría del boletín).
DEGRADADO_BARRA = alt.Gradient(
    gradient="linear",
    stops=[
        alt.GradientStop(color="#2b6cb0", offset=0),
        alt.GradientStop(color="#5b4b8a", offset=1),
    ],
    x1=0, x2=1, y1=0, y2=0,
)

# Dos configuraciones (clara/oscura) porque el gráfico es SVG real
# generado en el navegador -- a diferencia de la imagen estática de
# antes, sí puede adaptarse al interruptor de tema de la página.
CONFIG_POR_TEMA = {
    "light": {"texto": "#767676", "rejilla": "#e5e5e5"},
    "dark": {"texto": "#9a9a9a", "rejilla": "#2c2f33"},
}


def _config_tema(chart: alt.Chart, tema: str) -> alt.Chart:
    colores = CONFIG_POR_TEMA[tema]
    return (
        chart.configure(background="transparent", autosize={"type": "fit-x", "contains": "padding"})
        .configure_view(strokeWidth=0)
        .configure_axis(
            grid=True, gridColor=colores["rejilla"], domain=False,
            labelColor=colores["texto"], titleColor=colores["texto"],
            labelFontSize=10, tickColor=colores["rejilla"], labelLimit=140,
        )
        .configure_title(fontSize=12, anchor="start", color=colores["texto"])
        .configure_legend(labelColor=colores["texto"], titleColor=colores["texto"])
    )


def _contar_menciones(texto: str) -> dict[str, int]:
    """Cuenta ocurrencias reales (no solo presencia) por herramienta reconocida."""
    texto_min = texto.lower()
    conteos: dict[str, int] = {}
    for patron, etiqueta in ETIQUETAS_RECONOCIDAS.items():
        if etiqueta not in NOMBRE_VISIBLE:
            continue  # ia / business-intelligence: fuera del ranking de herramientas
        expresion = patron if patron.startswith(r"\b") else re.escape(patron)
        n = len(re.findall(expresion, texto_min))
        if n:
            nombre = NOMBRE_VISIBLE[etiqueta]
            conteos[nombre] = conteos.get(nombre, 0) + n
    return conteos


def construir_grafico(boletines: list[dict]) -> dict | None:
    """Devuelve {"light": chart, "dark": chart} (objetos Altair) o None si no hay datos.

    Cuenta ocurrencias reales de cada herramienta en el texto de cada
    boletín (no solo si aparece o no en la lista de etiquetas), para
    que la tendencia en el tiempo tenga variación real que mostrar."""
    filas = [
        {"fecha": b["fecha"], "herramienta": herramienta, "menciones": conteo}
        for b in boletines
        for herramienta, conteo in _contar_menciones(b["cuerpo_md"]).items()
    ]
    if not filas:
        return None

    df = pd.DataFrame(filas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    ranking = df.groupby("herramienta", as_index=False)["menciones"].sum()
    tendencia = df.groupby(["fecha", "herramienta"], as_index=False)["menciones"].sum()

    seleccion = alt.selection_point(fields=["herramienta"], on="click", empty=True, clear="dblclick", name="elegido")
    zoom = alt.selection_interval(bind="scales", encodings=["x"])

    barras = (
        alt.Chart(ranking)
        .mark_bar(cornerRadius=2)
        .encode(
            x=alt.X("menciones:Q", title=None, axis=None),
            y=alt.Y("herramienta:N", sort="-x", title=None),
            color=alt.condition(seleccion, alt.value(DEGRADADO_BARRA), alt.value(COLOR_APAGADO)),
            tooltip=[
                alt.Tooltip("herramienta:N", title="Herramienta"),
                alt.Tooltip("menciones:Q", title="Menciones totales"),
            ],
        )
        .add_params(seleccion)
        .properties(width="container", height=alt.Step(22))
    )

    linea = (
        alt.Chart(tendencia)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "fecha:T", title=None,
                axis=alt.Axis(format="%d %b %Y", tickCount={"interval": "day", "step": 1}, labelAngle=-40),
            ),
            y=alt.Y("menciones:Q", title="Menciones", axis=alt.Axis(tickMinStep=1)),
            detail="herramienta:N",
            color=alt.condition(seleccion, alt.value("#2b6cb0"), alt.value(COLOR_APAGADO)),
            opacity=alt.condition(seleccion, alt.value(1.0), alt.value(0.35)),
            tooltip=[
                alt.Tooltip("fecha:T", title="Fecha", format="%d/%m/%Y"),
                alt.Tooltip("herramienta:N", title="Herramienta"),
                alt.Tooltip("menciones:Q", title="Menciones"),
            ],
        )
        .add_params(zoom)
        .properties(width="container", height=220, title="Tendencia en el tiempo")
    )

    combinado = alt.vconcat(barras, linea).resolve_scale(color="independent")

    return {tema: _config_tema(combinado, tema) for tema in ("light", "dark")}

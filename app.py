
import html
import json
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="FUEGO SUR | Monitor de incendios",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reportes"
REPORTS_DIR.mkdir(exist_ok=True)

# Orden: oeste, sur, este, norte.
BBOX = "-76,-57,-62,-36"

SOURCES = {
    "VIIRS NOAA-20": "VIIRS_NOAA20_NRT",
    "VIIRS NOAA-21": "VIIRS_NOAA21_NRT",
    "MODIS": "MODIS_NRT",
}

DEFAULT_LAT = -45.8641
DEFAULT_LON = -67.4966


# =========================================================
# DISEÑO
# =========================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800;900&family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --fondo: #10100f;
        --panel: #1b1b18;
        --panel-claro: #25241f;
        --borde: #403b31;
        --texto: #f7f1e6;
        --secundario: #d0c8b9;
        --amarillo: #ffd166;
        --naranja: #ff812b;
        --rojo: #f04438;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--fondo);
        color: var(--texto);
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stHeader"] {
        background: rgba(16, 16, 15, 0.96);
    }

    [data-testid="stSidebar"] {
        background: #171715;
        border-right: 1px solid var(--borde);
    }

    [data-testid="stSidebar"] * {
        color: var(--texto);
    }

    h1, h2, h3 {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 800 !important;
        color: var(--texto) !important;
    }

    p, label, li {
        color: var(--texto);
    }

    .hero {
        padding: 30px;
        border: 1px solid #494033;
        border-radius: 16px;
        margin-bottom: 22px;
        background:
            radial-gradient(circle at 88% 12%,
                rgba(240, 68, 56, 0.22), transparent 34%),
            linear-gradient(115deg,
                #302417 0%, #251a13 45%, #171312 100%);
    }

    .hero-kicker {
        color: #ffd166;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    .hero-title {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: clamp(54px, 8vw, 92px);
        font-weight: 900;
        line-height: 0.92;
        letter-spacing: -1px;
        background: linear-gradient(
            90deg, #ffe58a 0%, #ffb13b 34%,
            #ff702d 68%, #f04438 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin-bottom: 16px;
    }

    .hero-description {
        color: #e8dfd0;
        max-width: 750px;
        font-size: 14px;
        line-height: 1.8;
    }

    .metric-card {
        background: var(--panel);
        border: 1px solid var(--borde);
        border-radius: 12px;
        padding: 16px;
        min-height: 108px;
    }

    .metric-label {
        font-size: 11px;
        font-weight: 800;
        color: var(--secundario);
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .metric-value {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 35px;
        line-height: 1.25;
        font-weight: 800;
        color: #fff4df;
        margin-top: 5px;
        overflow-wrap: anywhere;
    }

    .metric-note {
        font-size: 11px;
        color: var(--secundario);
        margin-top: 4px;
    }

    .info-panel {
        background: var(--panel);
        border: 1px solid var(--borde);
        border-radius: 12px;
        padding: 17px;
        margin-bottom: 12px;
    }

    .muted {
        color: var(--secundario);
        font-size: 13px;
        line-height: 1.7;
    }

    .report-card {
        background: linear-gradient(135deg, #26241f, #1a1a17);
        border: 1px solid #494235;
        border-left: 5px solid #ff9a35;
        border-radius: 13px;
        padding: 18px;
        margin: 12px 0;
    }

    .report-title {
        color: #ffe0a0;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .report-date {
        color: #d0c8b9;
        font-size: 12px;
        margin-bottom: 14px;
    }

    .report-description {
        color: #fff8ed;
        font-size: 15px;
        line-height: 1.8;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
    }

    .report-detail {
        background: #333027;
        color: #fff0d1;
        border-radius: 8px;
        padding: 10px 12px;
        margin-top: 12px;
        font-size: 13px;
        line-height: 1.7;
        overflow-wrap: anywhere;
    }

    .report-empty {
        background: #1c1b18;
        border: 1px dashed #655741;
        border-radius: 12px;
        padding: 26px;
        text-align: center;
        color: #e5d9c5;
        line-height: 1.8;
    }

    .stButton > button,
    .stFormSubmitButton > button {
        background: linear-gradient(100deg, #ffbd4a, #ff762e) !important;
        color: #21130b !important;
        border: 2px solid #ffbd5a !important;
        border-radius: 9px !important;
        font-weight: 800 !important;
        opacity: 1 !important;
    }

    .stButton > button *,
    .stFormSubmitButton > button * {
        color: #21130b !important;
        font-weight: 800 !important;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: #ffd166 !important;
        border-color: #ffffff !important;
        color: #17100a !important;
    }

    .stDownloadButton > button {
        background: #ffd166 !important;
        color: #17100a !important;
        border: 2px solid #ff9a35 !important;
        border-radius: 10px !important;
        font-weight: 800 !important;
        min-height: 46px !important;
        opacity: 1 !important;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.25) !important;
    }

    .stDownloadButton > button *,
    .stDownloadButton > button p,
    .stDownloadButton > button span {
        color: #17100a !important;
        font-weight: 800 !important;
    }

    .stDownloadButton > button:hover {
        background: #ff9a35 !important;
        border-color: #ffe0a0 !important;
        color: #17100a !important;
    }

    .stDownloadButton > button:focus {
        box-shadow: 0 0 0 2px #10100f, 0 0 0 4px #ffb83f !important;
    }

    input, textarea {
        color: #f5f1e8 !important;
        background: #20201d !important;
    }

    [data-baseweb="select"] > div {
        background: #20201d;
        border-color: #575144;
    }

    [data-baseweb="select"] * {
        color: #f5f1e8;
    }

    [data-testid="stTabs"] button {
        color: #d7d0c2;
        font-weight: 700;
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #ffc45a !important;
    }

    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--borde);
        border-radius: 12px;
        padding: 14px;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricValue"] {
        color: var(--texto) !important;
    }

    hr {
        border-color: var(--borde);
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# FUNCIONES
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def obtener_incendios(api_key, source, bbox, days):
    """Consulta y valida las detecciones de NASA FIRMS."""
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{api_key}/{source}/{bbox}/{days}"
    )

    respuesta = requests.get(url, timeout=40)
    respuesta.raise_for_status()
    contenido = respuesta.text.strip()

    if not contenido:
        return pd.DataFrame(), "NASA devolvió una respuesta vacía."

    inicio = contenido[:500].lower()
    mensajes_error = (
        "invalid",
        "error",
        "unauthorized",
        "limit exceeded",
        "not found",
        "api key",
        "permission",
    )

    if any(inicio.startswith(mensaje) for mensaje in mensajes_error):
        raise ValueError(
            "NASA FIRMS devolvió un mensaje en lugar de datos. "
            "Verificá la clave, la fuente elegida y el límite de consultas."
        )

    try:
        datos = pd.read_csv(StringIO(contenido))
    except pd.errors.ParserError:
        datos = pd.read_csv(StringIO(contenido), sep=None, engine="python")

    datos.columns = [
        str(columna).strip().lower() for columna in datos.columns
    ]

    renombrar = {}
    if "latitude" not in datos.columns and "lat" in datos.columns:
        renombrar["lat"] = "latitude"
    if "longitude" not in datos.columns and "lon" in datos.columns:
        renombrar["lon"] = "longitude"
    if "longitude" not in datos.columns and "long" in datos.columns:
        renombrar["long"] = "longitude"

    if renombrar:
        datos = datos.rename(columns=renombrar)

    if not {"latitude", "longitude"}.issubset(datos.columns):
        columnas = ", ".join(datos.columns.astype(str))
        raise ValueError(
            "La respuesta de NASA no contiene latitud y longitud. "
            f"Columnas recibidas: {columnas or 'ninguna'}. "
            "Revisá la clave y la fuente seleccionada."
        )

    datos["latitude"] = pd.to_numeric(
        datos["latitude"], errors="coerce"
    )
    datos["longitude"] = pd.to_numeric(
        datos["longitude"], errors="coerce"
    )

    datos = datos.dropna(subset=["latitude", "longitude"])

    datos = datos[
        datos["latitude"].between(-90, 90)
        & datos["longitude"].between(-180, 180)
    ].copy()

    if "frp" in datos.columns:
        datos["frp"] = pd.to_numeric(datos["frp"], errors="coerce")

    if datos.empty:
        return datos, (
            "NASA respondió, pero no hay detecciones con coordenadas "
            "válidas para esta consulta."
        )

    return datos, None


@st.cache_data(ttl=600, show_spinner=False)
def obtener_clima(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"

    parametros = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "wind_speed_10m,wind_direction_10m,"
            "precipitation,weather_code"
        ),
        "daily": (
            "temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "forecast_days": 3,
        "timezone": "auto",
    }

    respuesta = requests.get(url, params=parametros, timeout=25)
    respuesta.raise_for_status()
    return respuesta.json()


def geocodificar_direccion(direccion):
    """
    Convierte una dirección escrita en coordenadas usando Nominatim.
    Se limita la búsqueda a Argentina.
    """
    url = "https://nominatim.openstreetmap.org/search"

    parametros = {
        "q": direccion,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "ar",
    }

    encabezados = {
        "User-Agent": "FuegoSurApp/1.0 (geocodificacion de reportes)"
    }

    respuesta = requests.get(
        url,
        params=parametros,
        headers=encabezados,
        timeout=20,
    )
    respuesta.raise_for_status()
    resultados = respuesta.json()

    if not resultados:
        return None

    resultado = resultados[0]

    return {
        "latitud": float(resultado["lat"]),
        "longitud": float(resultado["lon"]),
        "direccion_encontrada": resultado.get("display_name", direccion),
    }


def cargar_reportes():
    """Carga los reportes guardados en la carpeta local."""
    registros = []

    for archivo in REPORTS_DIR.glob("*.json"):
        try:
            with archivo.open("r", encoding="utf-8") as f:
                reporte = json.load(f)

            if isinstance(reporte, dict):
                registros.append(reporte)
        except (OSError, json.JSONDecodeError):
            continue

    columnas = [
        "fecha", "tipo", "descripcion",
        "latitud", "longitud", "contacto", "ubicacion_texto",
    ]

    if not registros:
        return pd.DataFrame(columns=columnas)

    return pd.DataFrame(registros)


def guardar_reporte(datos):
    nombre = (
        f"reporte_{datetime.now():%Y%m%d_%H%M%S}_"
        f"{uuid.uuid4().hex[:6]}.json"
    )
    destino = REPORTS_DIR / nombre

    with destino.open("w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)


def mostrar_metrica(etiqueta, valor, nota=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(str(etiqueta))}</div>
            <div class="metric-value">{html.escape(str(valor))}</div>
            <div class="metric-note">{html.escape(str(nota))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def texto_celda(fila, columna, defecto="No disponible"):
    valor = fila.get(columna, defecto)

    if valor is None or pd.isna(valor):
        return defecto

    return str(valor)


def fecha_legible(valor):
    try:
        return pd.to_datetime(valor).strftime("%d/%m/%Y · %H:%M")
    except (ValueError, TypeError):
        return "Fecha no disponible"


# =========================================================
# ENCABEZADO
# =========================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">
            Sistema de monitoreo · Patagonia argentina
        </div>
        <div class="hero-title">FUEGO SUR</div>
        <div class="hero-description">
            Detecciones satelitales, información meteorológica
            y observaciones ciudadanas en un solo lugar.
            Una herramienta para explorar datos y prestar atención
            a lo que pasa en nuestro territorio.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# BARRA LATERAL
# =========================================================

with st.sidebar:
    st.markdown("## 🔥 FUEGO SUR")
    st.caption("PANEL DE CONTROL")
    st.divider()

    st.markdown("### Conexión satelital")

    api_key = st.text_input(
        "Clave de NASA FIRMS",
        type="password",
        help="Ingresá tu clave. No la compartas públicamente.",
    )

    fuente_nombre = st.selectbox(
        "Satélite / fuente",
        list(SOURCES.keys()),
        index=0,
    )
    fuente = SOURCES[fuente_nombre]

    dias = st.selectbox(
        "Período de búsqueda",
        [1, 2, 3, 5],
        index=1,
        format_func=lambda n: (
            "Último día" if n == 1 else f"Últimos {n} días"
        ),
    )

    st.caption(
        "Las detecciones son anomalías térmicas. "
        "No todas representan un incendio confirmado."
    )

    if st.button("↻ Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### Zona de monitoreo")
    st.write("Patagonia argentina")
    st.caption(f"Área consultada: {BBOX}")

    st.divider()
    st.markdown("### Fuentes")
    st.markdown(
        "- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)\n"
        "- [Open-Meteo](https://open-meteo.com/)\n"
        "- [OpenStreetMap](https://www.openstreetmap.org/)"
    )


# =========================================================
# DATOS SATELITALES
# =========================================================

df = pd.DataFrame()
error_firms = None
aviso_firms = None

if api_key.strip():
    try:
        with st.spinner("Buscando detecciones satelitales..."):
            df, aviso_firms = obtener_incendios(
                api_key.strip(), fuente, BBOX, dias
            )

    except requests.HTTPError as exc:
        codigo = (
            exc.response.status_code
            if exc.response is not None
            else "desconocido"
        )
        error_firms = (
            f"NASA FIRMS rechazó la consulta (HTTP {codigo}). "
            "Verificá tu clave, la fuente y el acceso a la API."
        )

    except requests.RequestException as exc:
        error_firms = (
            "No pudimos conectar con NASA FIRMS. "
            f"Detalle: {exc}"
        )

    except (ValueError, pd.errors.ParserError) as exc:
        error_firms = f"No pudimos leer los datos de NASA FIRMS: {exc}"

if error_firms:
    st.error(error_firms)
elif aviso_firms:
    st.info(aviso_firms)
elif not api_key.strip():
    st.info(
        "Ingresá tu clave de NASA FIRMS en la barra lateral "
        "para cargar los puntos de fuego."
    )
elif df.empty:
    st.info(
        "No se encontraron detecciones para esta consulta. "
        "Probá otra fuente o ampliá el período."
    )
else:
    st.success(
        f"NASA FIRMS devolvió {len(df)} detecciones con coordenadas válidas."
    )


# =========================================================
# MÉTRICAS
# =========================================================

cantidad = len(df)

if not df.empty and "frp" in df.columns:
    frp_total = df["frp"].sum()
    frp_texto = f"{frp_total:.1f} MW"
else:
    frp_texto = "—"

if not df.empty and "confidence" in df.columns:
    confianza = df["confidence"].astype(str).str.lower()
    confianza_alta = int(confianza.isin(["h", "high"]).sum())
else:
    confianza_alta = 0

m1, m2, m3, m4 = st.columns(4)

with m1:
    mostrar_metrica("Detecciones", cantidad, f"Fuente: {fuente_nombre}")
with m2:
    mostrar_metrica("Potencia FRP", frp_texto, "Potencia radiativa detectada")
with m3:
    mostrar_metrica("Confianza alta", confianza_alta, "Según la clasificación de NASA")
with m4:
    mostrar_metrica(
        "Última consulta",
        datetime.now().strftime("%H:%M"),
        datetime.now().strftime("%d/%m/%Y"),
    )


# =========================================================
# PESTAÑAS
# =========================================================

tab_mapa, tab_clima, tab_reportes, tab_datos, tab_acerca = st.tabs(
    [
        "🗺️ Mapa satelital",
        "🌦️ Clima",
        "📍 Reportes ciudadanos",
        "📊 Centro de datos",
        "ℹ️ Acerca del proyecto",
    ]
)


# =========================================================
# MAPA DE DETECCIONES
# =========================================================

with tab_mapa:
    st.markdown("## Mapa de detecciones")

    st.markdown(
        """
        <div class="muted">
            Cada círculo representa una detección térmica de un satélite.
            Tocá un punto para ver sus datos. Los círculos no muestran
            el tamaño real ni el perímetro de un incendio.
        </div>
        """,
        unsafe_allow_html=True,
    )

    filtro = st.selectbox(
        "Mostrar detecciones",
        [
            "Todas",
            "Confianza alta",
            "Confianza nominal",
            "Confianza baja",
        ],
        key="filtro_mapa",
    )

    mapa_df = df.copy()

    if not mapa_df.empty and filtro != "Todas":
        if "confidence" in mapa_df.columns:
            valores = mapa_df["confidence"].astype(str).str.lower()

            if filtro == "Confianza alta":
                mapa_df = mapa_df[valores.isin(["h", "high"])]
            elif filtro == "Confianza nominal":
                mapa_df = mapa_df[valores.isin(["n", "nominal"])]
            elif filtro == "Confianza baja":
                mapa_df = mapa_df[valores.isin(["l", "low"])]
        else:
            st.warning(
                "Esta fuente no incluye información de confianza; "
                "se muestran todas las detecciones."
            )
            mapa_df = df.copy()

    mapa = folium.Map(
        location=[DEFAULT_LAT, DEFAULT_LON],
        zoom_start=5,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.Marker(
        [DEFAULT_LAT, DEFAULT_LON],
        tooltip="Comodoro Rivadavia · Punto de referencia",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(mapa)

    puntos_agregados = 0
    coordenadas_mapa = []

    if not mapa_df.empty:
        for _, fila in mapa_df.iterrows():
            lat = fila.get("latitude")
            lon = fila.get("longitude")

            if pd.isna(lat) or pd.isna(lon):
                continue

            lat = float(lat)
            lon = float(lon)

            frp = fila.get("frp", 0)
            try:
                frp_num = float(frp)
            except (ValueError, TypeError):
                frp_num = 0.0

            if frp_num >= 50:
                color = "#f04438"
                radio = 8
            elif frp_num >= 10:
                color = "#ff812b"
                radio = 6
            else:
                color = "#ffd166"
                radio = 5

            fecha = texto_celda(fila, "acq_date")
            hora = texto_celda(fila, "acq_time")
            confianza_punto = texto_celda(fila, "confidence")
            satelite = texto_celda(fila, "satellite")
            frp_mostrar = texto_celda(fila, "frp")

            popup_html = f"""
            <div style="font-family:Arial;min-width:190px;color:#222">
                <h3 style="color:#9b3b16;margin-bottom:8px">
                    Detección térmica
                </h3>
                <b>Fecha:</b> {html.escape(fecha)}<br>
                <b>Hora UTC:</b> {html.escape(hora)}<br>
                <b>Confianza:</b> {html.escape(confianza_punto)}<br>
                <b>FRP:</b> {html.escape(frp_mostrar)}<br>
                <b>Satélite:</b> {html.escape(satelite)}
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=radio,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.95,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"Detección térmica · FRP: {frp_mostrar}",
            ).add_to(mapa)

            coordenadas_mapa.append([lat, lon])
            puntos_agregados += 1

    if coordenadas_mapa:
        mapa.fit_bounds(coordenadas_mapa, padding=(25, 25))

    mapa_col, leyenda_col = st.columns([2.2, 1])

    with mapa_col:
        st_folium(
            mapa,
            use_container_width=True,
            height=560,
            key="mapa_fuego_sur",
        )

    with leyenda_col:
        st.markdown("### ¿Qué significan los colores?")

        st.markdown(
            """
            <div class="info-panel">
                <p><b style="color:#ffd166">● Amarillo</b></p>
                <p class="muted">Potencia FRP menor a 10 MW o sin dato.</p>
                <hr>
                <p><b style="color:#ff812b">● Naranja</b></p>
                <p class="muted">Potencia FRP entre 10 y menos de 50 MW.</p>
                <hr>
                <p><b style="color:#f04438">● Rojo</b></p>
                <p class="muted">Potencia FRP igual o superior a 50 MW.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Datos visibles")
        st.metric("Puntos en el mapa", puntos_agregados)

        if puntos_agregados == 0:
            st.warning(
                "No hay puntos para mostrar con esta consulta y filtro. "
                "Elegí «Todas» y revisá el mensaje de NASA que aparece arriba."
            )

        st.markdown(
            """
            <div class="info-panel">
                <p class="muted">
                    FRP mide la potencia radiativa detectada por el satélite;
                    no indica directamente el tamaño del incendio.
                </p>
                <p class="muted">
                    Un mapa sin puntos no garantiza que no haya fuego.
                    Las nubes, la cobertura satelital y las demoras pueden
                    afectar las detecciones.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# CLIMA
# =========================================================

with tab_clima:
    st.markdown("## Condiciones meteorológicas")
    st.write("Consultá el tiempo actual y el pronóstico para una ubicación.")

    c1, c2 = st.columns(2)

    with c1:
        lat_clima = st.number_input(
            "Latitud",
            min_value=-90.0,
            max_value=90.0,
            value=DEFAULT_LAT,
            step=0.01,
            format="%.4f",
        )

    with c2:
        lon_clima = st.number_input(
            "Longitud",
            min_value=-180.0,
            max_value=180.0,
            value=DEFAULT_LON,
            step=0.01,
            format="%.4f",
        )

    if st.button("Consultar clima", key="boton_clima"):
        st.session_state["coords_clima"] = (lat_clima, lon_clima)

    coords = st.session_state.get(
        "coords_clima", (DEFAULT_LAT, DEFAULT_LON)
    )

    try:
        with st.spinner("Consultando el clima..."):
            clima = obtener_clima(coords[0], coords[1])

        actual = clima.get("current", {})
        diario = clima.get("daily", {})

        temp = actual.get("temperature_2m", "—")
        humedad = actual.get("relative_humidity_2m", "—")
        viento = actual.get("wind_speed_10m", "—")
        direccion = actual.get("wind_direction_10m", "—")
        lluvia = actual.get("precipitation", "—")

        a, b, c = st.columns(3)

        with a:
            mostrar_metrica("Temperatura", f"{temp} °C", "Temperatura actual")
        with b:
            mostrar_metrica("Humedad", f"{humedad} %", "Humedad relativa")
        with c:
            mostrar_metrica("Viento", f"{viento} km/h", f"Dirección: {direccion}°")

        st.write("")
        st.markdown("### Lluvia")
        st.write(f"Precipitación actual: **{lluvia} mm**")

        if diario.get("time"):
            st.markdown("### Pronóstico de los próximos días")

            pronostico = pd.DataFrame(
                {
                    "Día": diario.get("time", []),
                    "Máxima (°C)": diario.get("temperature_2m_max", []),
                    "Mínima (°C)": diario.get("temperature_2m_min", []),
                    "Probabilidad de lluvia (%)": diario.get(
                        "precipitation_probability_max", []
                    ),
                }
            )

            st.dataframe(
                pronostico,
                use_container_width=True,
                hide_index=True,
            )

        st.warning(
            "El clima es información de contexto, no una confirmación "
            "de incendios ni un índice oficial de peligro."
        )

    except requests.RequestException:
        st.error(
            "No pudimos consultar el clima. Revisá tu conexión e intentá nuevamente."
        )
    except (KeyError, ValueError, TypeError):
        st.error("No pudimos interpretar los datos meteorológicos.")


# =========================================================
# REPORTES CIUDADANOS
# =========================================================

with tab_reportes:
    st.markdown("## 📍 Reportes ciudadanos")

    st.markdown(
        """
        <div class="muted">
            ¿Viste humo o algo que te llamó la atención? Registrá lo que
            observaste y elegí cómo indicar el lugar. Podés usar coordenadas,
            escribir una dirección o marcar un punto directamente en el mapa.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Elegir un único método para indicar la ubicación.
    metodo_ubicacion = st.radio(
        "¿Cómo querés indicar la ubicación?",
        [
            "Escribir una dirección",
            "Ingresar coordenadas",
            "Marcar un punto en el mapa",
        ],
        horizontal=False,
        key="metodo_ubicacion_reporte",
    )

    lat_final = None
    lon_final = None
    ubicacion_texto = ""

    # -----------------------------------------------------
    # OPCIÓN 1: DIRECCIÓN
    # -----------------------------------------------------

    if metodo_ubicacion == "Escribir una dirección":
        direccion_reporte = st.text_input(
            "Dirección o lugar",
            placeholder="Ej.: Ruta 3, Comodoro Rivadavia, Chubut",
            key="direccion_reporte",
            help=(
                "Escribí una dirección, ruta, localidad o punto de referencia. "
                "La aplicación buscará sus coordenadas en el mapa."
            ),
        )

        st.caption(
            "La dirección se buscará en Argentina mediante OpenStreetMap. "
            "Los resultados dependen de la información disponible."
        )

    # -----------------------------------------------------
    # OPCIÓN 2: COORDENADAS
    # -----------------------------------------------------

    elif metodo_ubicacion == "Ingresar coordenadas":
        coord1, coord2 = st.columns(2)

        with coord1:
            lat_manual = st.number_input(
                "Latitud",
                min_value=-90.0,
                max_value=90.0,
                value=DEFAULT_LAT,
                step=0.001,
                format="%.5f",
                key="latitud_manual_reporte",
            )

        with coord2:
            lon_manual = st.number_input(
                "Longitud",
                min_value=-180.0,
                max_value=180.0,
                value=DEFAULT_LON,
                step=0.001,
                format="%.5f",
                key="longitud_manual_reporte",
            )

        lat_final = float(lat_manual)
        lon_final = float(lon_manual)
        ubicacion_texto = "Coordenadas ingresadas manualmente"

        mapa_manual = folium.Map(
            location=[lat_final, lon_final],
            zoom_start=12,
            tiles="OpenStreetMap",
            control_scale=True,
        )

        folium.Marker(
            [lat_final, lon_final],
            tooltip="Ubicación del reporte",
            popup="Ubicación elegida",
            icon=folium.Icon(color="orange", icon="map-marker"),
        ).add_to(mapa_manual)

        st_folium(
            mapa_manual,
            use_container_width=True,
            height=300,
            key="mapa_coordenadas_reporte",
        )

    # -----------------------------------------------------
    # OPCIÓN 3: MARCAR UN PUNTO EN EL MAPA
    # -----------------------------------------------------

    elif metodo_ubicacion == "Marcar un punto en el mapa":
        st.write(
            "Hacé clic en el mapa para elegir el lugar. "
            "Podés acercarte con los controles del mapa."
        )

        if "punto_reporte_mapa" not in st.session_state:
            st.session_state["punto_reporte_mapa"] = {
                "latitud": DEFAULT_LAT,
                "longitud": DEFAULT_LON,
            }

        punto_guardado = st.session_state["punto_reporte_mapa"]

        mapa_seleccion = folium.Map(
            location=[
                punto_guardado["latitud"],
                punto_guardado["longitud"],
            ],
            zoom_start=7,
            tiles="OpenStreetMap",
            control_scale=True,
        )

        folium.Marker(
            [
                punto_guardado["latitud"],
                punto_guardado["longitud"],
            ],
            tooltip="Punto seleccionado",
            popup="Ubicación actual del reporte",
            icon=folium.Icon(color="orange", icon="map-marker"),
        ).add_to(mapa_seleccion)

        resultado_mapa = st_folium(
            mapa_seleccion,
            use_container_width=True,
            height=430,
            key="mapa_elegir_ubicacion_reporte",
            returned_objects=["last_clicked"],
        )

        clic = resultado_mapa.get("last_clicked") if resultado_mapa else None

        if clic and "lat" in clic and "lng" in clic:
            st.session_state["punto_reporte_mapa"] = {
                "latitud": float(clic["lat"]),
                "longitud": float(clic["lng"]),
            }

        punto_guardado = st.session_state["punto_reporte_mapa"]
        lat_final = float(punto_guardado["latitud"])
        lon_final = float(punto_guardado["longitud"])
        ubicacion_texto = "Punto seleccionado en el mapa"

        st.success(
            f"Punto seleccionado: {lat_final:.5f}, {lon_final:.5f}"
        )

        if st.button(
            "Volver al punto inicial",
            key="reiniciar_punto_reporte",
        ):
            st.session_state["punto_reporte_mapa"] = {
                "latitud": DEFAULT_LAT,
                "longitud": DEFAULT_LON,
            }
            st.rerun()

    st.divider()

    # El formulario contiene los datos del reporte.
    with st.form("formulario_reporte", clear_on_submit=True):
        tipo = st.selectbox(
            "¿Qué observaste?",
            [
                "Posible incendio",
                "Humo visible",
                "Quema controlada",
                "Otra observación",
            ],
        )

        descripcion = st.text_area(
            "Contanos qué viste",
            placeholder=(
                "Ejemplo: Vi humo cerca del camino. "
                "No sé si es un incendio."
            ),
            max_chars=1500,
            height=120,
        )

        contacto = st.text_input(
            "Contacto (opcional)",
            max_chars=100,
            help="No escribas datos personales que no sean necesarios.",
        )

        enviado = st.form_submit_button(
            "Guardar observación",
            use_container_width=True,
        )

    if enviado:
        if not descripcion.strip():
            st.error("Primero contanos qué observaste.")

        else:
            try:
                # Resolver la ubicación según el método elegido.
                if metodo_ubicacion == "Escribir una dirección":
                    direccion = st.session_state.get(
                        "direccion_reporte", ""
                    ).strip()

                    if not direccion:
                        st.error("Escribí una dirección o un lugar.")
                        st.stop()

                    with st.spinner("Buscando la dirección en el mapa..."):
                        resultado_direccion = geocodificar_direccion(
                            direccion
                        )

                    if resultado_direccion is None:
                        st.error(
                            "No encontramos esa dirección. "
                            "Probá agregar la localidad o provincia, "
                            "o elegí el punto directamente en el mapa."
                        )
                        st.stop()

                    lat_final = resultado_direccion["latitud"]
                    lon_final = resultado_direccion["longitud"]
                    ubicacion_texto = resultado_direccion[
                        "direccion_encontrada"
                    ]

                elif metodo_ubicacion == "Ingresar coordenadas":
                    lat_final = float(
                        st.session_state["latitud_manual_reporte"]
                    )
                    lon_final = float(
                        st.session_state["longitud_manual_reporte"]
                    )
                    ubicacion_texto = "Coordenadas ingresadas manualmente"

                else:
                    punto_guardado = st.session_state["punto_reporte_mapa"]
                    lat_final = float(punto_guardado["latitud"])
                    lon_final = float(punto_guardado["longitud"])
                    ubicacion_texto = "Punto seleccionado en el mapa"

                nuevo = {
                    "fecha": datetime.now().isoformat(timespec="seconds"),
                    "tipo": tipo,
                    "descripcion": descripcion.strip(),
                    "latitud": float(lat_final),
                    "longitud": float(lon_final),
                    "contacto": contacto.strip(),
                    "ubicacion_texto": ubicacion_texto,
                }

                guardar_reporte(nuevo)

                st.success(
                    "¡Listo! La observación quedó guardada "
                    "en esta computadora."
                )

                st.markdown(
                    f"""
                    <div class="report-detail">
                        📍 <b>Ubicación guardada:</b>
                        {html.escape(ubicacion_texto)}<br>
                        <b>Coordenadas:</b>
                        {lat_final:.5f}, {lon_final:.5f}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            except requests.RequestException:
                st.error(
                    "No pudimos buscar esa dirección por un problema "
                    "de conexión. Probá de nuevo o elegí coordenadas "
                    "o el punto en el mapa."
                )
            except (KeyError, ValueError, TypeError, OSError) as exc:
                st.error(f"No se pudo guardar el reporte: {exc}")

    st.divider()
    st.markdown("## 📚 Historial de observaciones")

    reportes = cargar_reportes()

    if reportes.empty:
        st.markdown(
            """
            <div class="report-empty">
                <div style="font-size:42px">📝</div>
                <h3 style="color:#ffd166">Todavía no hay reportes</h3>
                <p>
                    Cuando guardes una observación, va a aparecer acá.
                    Podés descargar el archivo incluso si todavía está vacío.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        exportar = reportes.copy()

    else:
        reportes = reportes.copy()

        if "fecha" in reportes.columns:
            reportes["_fecha_orden"] = pd.to_datetime(
                reportes["fecha"], errors="coerce"
            )
            reportes = reportes.sort_values(
                "_fecha_orden",
                ascending=False,
                na_position="last",
            )

        cantidad_reportes = len(reportes)
        palabra = "reporte" if cantidad_reportes == 1 else "reportes"

        st.markdown(f"**Hay {cantidad_reportes} {palabra} guardados.**")

        iconos = {
            "Posible incendio": "🔥",
            "Humo visible": "💨",
            "Quema controlada": "🌿",
            "Otra observación": "📍",
        }

        for numero, (_, reporte) in enumerate(
            reportes.iterrows(), start=1
        ):
            tipo_reporte = texto_celda(
                reporte, "tipo", "Otra observación"
            )
            descripcion = texto_celda(
                reporte, "descripcion",
                "No se escribió una descripción."
            )
            fecha = fecha_legible(reporte.get("fecha", ""))
            icono = iconos.get(tipo_reporte, "📍")

            try:
                ubicacion = (
                    f"{float(reporte.get('latitud')):.4f}, "
                    f"{float(reporte.get('longitud')):.4f}"
                )
            except (ValueError, TypeError):
                ubicacion = "Ubicación no indicada"

            nombre_lugar = texto_celda(
                reporte, "ubicacion_texto", ""
            )

            st.markdown(
                f"""
                <div class="report-card">
                    <div class="report-title">
                        {icono} {html.escape(tipo_reporte)}
                    </div>
                    <div class="report-date">
                        🕒 {html.escape(fecha)}
                    </div>
                    <div class="report-description">
                        {html.escape(descripcion)}
                    </div>
                    <div class="report-detail">
                        📍 <b>Dónde:</b>
                        {html.escape(nombre_lugar)}<br>
                        <b>Coordenadas:</b> {html.escape(ubicacion)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(f"Ver más detalles del reporte {numero}"):
                st.write("**¿Qué se observó?**")
                st.write(tipo_reporte)
                st.write("**¿Cuándo?**")
                st.write(fecha)
                st.write("**¿Dónde?**")
                st.write(nombre_lugar)
                st.write("**Coordenadas:**")
                st.write(ubicacion)

                contacto_reporte = str(
                    reporte.get("contacto", "")
                ).strip()

                if contacto_reporte:
                    st.write("**Contacto indicado:**")
                    st.write(contacto_reporte)
                else:
                    st.write("No se indicó un contacto.")

        exportar = reportes.drop(
            columns=["_fecha_orden"], errors="ignore"
        )

    csv_reportes = exportar.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "📥 Descargar historial de reportes (CSV)",
        data=csv_reportes,
        file_name="historial_fuego_sur.csv",
        mime="text/csv",
        use_container_width=True,
        key="descargar_historial_reportes",
    )

    st.caption(
        "El archivo CSV se puede abrir con Excel o una hoja de cálculo."
    )

    st.info(
        "Los reportes se guardan en esta computadora. "
        "Esta versión no los envía automáticamente a los bomberos "
        "ni a otros servicios de emergencia."
    )


# =========================================================
# CENTRO DE DATOS
# =========================================================

with tab_datos:
    st.markdown("## 📊 Centro de datos")
    st.write("Acá podés explorar y descargar los datos satelitales.")

    if df.empty:
        st.info(
            "Todavía no hay detecciones para mostrar. "
            "Ingresá una clave válida de NASA FIRMS y verificá "
            "la fuente y el período."
        )

    else:
        columnas_disponibles = list(df.columns)

        columnas_iniciales = [
            c for c in [
                "latitude", "longitude", "acq_date", "acq_time",
                "confidence", "frp", "satellite", "instrument", "daynight",
            ]
            if c in columnas_disponibles
        ]

        columnas_elegidas = st.multiselect(
            "Elegí qué datos querés ver",
            options=columnas_disponibles,
            default=columnas_iniciales or columnas_disponibles[:8],
        )

        if columnas_elegidas:
            st.dataframe(
                df[columnas_elegidas],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Elegí al menos una columna.")

        csv_datos = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "📥 Descargar detecciones satelitales",
            data=csv_datos,
            file_name="detecciones_fuego_sur.csv",
            mime="text/csv",
            use_container_width=True,
            key="descargar_detecciones",
        )

        r1, r2 = st.columns(2)

        with r1:
            st.metric("Cantidad de detecciones", len(df))
        with r2:
            st.metric("Columnas de información", len(df.columns))

        if "confidence" in df.columns:
            st.markdown("### Nivel de confianza")
            st.bar_chart(
                df["confidence"].fillna("Sin dato").astype(str).value_counts()
            )

        if "acq_date" in df.columns:
            st.markdown("### Detecciones por fecha")
            por_fecha = (
                df["acq_date"].fillna("Sin fecha").astype(str).value_counts()
                .sort_index()
            )
            st.bar_chart(por_fecha)


# =========================================================
# ACERCA DEL PROYECTO
# =========================================================

with tab_acerca:
    st.markdown("## ℹ️ Sobre Fuego Sur")

    st.markdown(
        """
        <div class="info-panel">
            <div style="
                color:#ffb547;
                font-size:11px;
                font-weight:800;
                letter-spacing:2px;
            ">
                OBJETIVO DEL PROYECTO
            </div>
            <h3>Datos para observar el territorio</h3>
            <p class="muted">
                Fuego Sur reúne detecciones térmicas satelitales,
                información meteorológica y reportes ciudadanos para
                facilitar la exploración de posibles focos de calor
                en la Patagonia.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    acerca1, acerca2 = st.columns(2)

    with acerca1:
        st.markdown("### 🛰️ Datos satelitales")
        st.write(
            "NASA FIRMS distribuye detecciones de anomalías térmicas "
            "registradas por instrumentos satelitales. Los datos pueden "
            "tener demoras y limitaciones."
        )

        st.markdown("### 🌦️ Información meteorológica")
        st.write(
            "Open-Meteo proporciona las condiciones meteorológicas "
            "y el pronóstico de la ubicación elegida."
        )

    with acerca2:
        st.markdown("### 📍 Reportes ciudadanos")
        st.write(
            "Las observaciones se guardan como archivos JSON dentro "
            "de la carpeta local `reportes`."
        )

        st.markdown("### ⚠️ Limitaciones")
        st.write(
            "Esta aplicación es un prototipo informativo. No confirma "
            "incendios, no calcula un índice oficial de riesgo y no "
            "reemplaza a los servicios de emergencia."
        )

    st.divider()
    st.markdown("### Fuentes utilizadas")
    st.markdown(
        """
        - [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)
        - [Open-Meteo](https://open-meteo.com/)
        - [OpenStreetMap](https://www.openstreetmap.org/)
        """
    )


# =========================================================
# PIE DE PÁGINA
# =========================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        padding:12px 0 22px 0;
        color:#c1bdb2;
        font-size:11px;
        letter-spacing:1px;
    ">
        FUEGO SUR · MONITOREO SATELITAL · PATAGONIA ARGENTINA
    </div>
    """,
    unsafe_allow_html=True,
)


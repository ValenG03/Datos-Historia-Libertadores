# -*- coding: utf-8 -*-
"""
LA GLORIA ETERNA EN NÚMEROS
Análisis cuantitativo de la historia de la CONMEBOL Libertadores (1960 – 2026)

Deploy: subí app.py + requirements.txt a un repo de GitHub y conectalo en share.streamlit.io
Logo: si querés usar un archivo propio, guardalo como assets/libertadores_logo.png
      (o definí LOGO_URL en los Secrets de Streamlit). Si no, la app intenta cargarlo desde Wikimedia.
"""

import base64
import hashlib
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from PIL import Image

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Libertadores · La Gloria Eterna en Números",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

GOLD = "#E8C15A"
GOLD_SOFT = "#F6DE97"
GOLD_DEEP = "#A67C1F"
EMBER = "#E2553F"
INK = "#0A0C12"
PANEL = "#11141D"
LINE = "#232838"
TEXT = "#ECE7DA"
MUTED = "#8E8A80"

COUNTRY_COLORS = {
    "Argentina": "#7FB7E6",
    "Brasil": "#F2CF4A",
    "Uruguay": "#4F8FD6",
    "Paraguay": "#D9534F",
    "Colombia": "#F0A33A",
    "Chile": "#C7413A",
    "Ecuador": "#E9D24B",
    "Perú": "#E57373",
    "Bolivia": "#5CB85C",
    "Venezuela": "#9B59B6",
    "México": "#2E8B57",
}

FLAGS = {
    "Argentina": "🇦🇷", "Brasil": "🇧🇷", "Uruguay": "🇺🇾", "Paraguay": "🇵🇾",
    "Colombia": "🇨🇴", "Chile": "🇨🇱", "Ecuador": "🇪🇨", "Perú": "🇵🇪",
    "Bolivia": "🇧🇴", "Venezuela": "🇻🇪", "México": "🇲🇽",
}

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

# ──────────────────────────────────────────────────────────────────────────────
# DATA  (cada bloque indica fuente y fecha de corte)
# ──────────────────────────────────────────────────────────────────────────────

# Goleadores históricos — CONMEBOL Libertadores / El Gráfico / Wikipedia (worldfootball), corte nov-2025.
SCORERS = pd.DataFrame([
    # jugador, nacionalidad, goles, partidos, debut, clubes (goles por club)
    ["Alberto Spencer", "Ecuador", 54, 87, 1960, "Peñarol (48) · Barcelona SC (6)"],
    ["Fernando Morena", "Uruguay", 37, 77, 1973, "Peñarol (37)"],
    ["Pedro Virgilio Rocha", "Uruguay", 36, 89, 1962, "Peñarol (25) · São Paulo (10) · Palmeiras (1)"],
    ["Daniel Onega", "Argentina", 31, 47, 1966, "River Plate (31)"],
    ["Gabriel Barbosa «Gabigol»", "Brasil", 31, 60, 2018, "Santos (1) · Flamengo (30)"],
    ["Miguel Borja", "Colombia", 31, 69, 2015, "Atl. Nacional (5) · Palmeiras (11) · Junior (7) · River (8)"],
    ["Julio César Morales", "Uruguay", 30, 76, 1966, "Nacional (30)"],
    ["Lucas Pratto", "Argentina", 30, 96, 2011, "U. Católica (6) · Vélez (8) · Atl. Mineiro (7) · River (9)"],
    ["Luizão", "Brasil", 29, 43, 1998, "Vasco (5) · Corinthians (15) · Grêmio (4) · São Paulo (5)"],
    ["Juan Carlos Sarnari", "Argentina", 29, 62, 1966, "River (10) · U. Católica (12) · U. de Chile (4) · Santa Fe (3)"],
], columns=["Jugador", "País", "Goles", "PJ", "Debut", "Clubes"])
SCORERS["Promedio"] = (SCORERS["Goles"] / SCORERS["PJ"]).round(2)
SCORERS["Rank"] = range(1, len(SCORERS) + 1)

# Asistidores — no existe registro oficial CONMEBOL de asistencias anterior a ~2000.
# El Gráfico (ago-2025 y sep-2026) + ranking oficial CONMEBOL 2012-2022 (ene-2023).
ASSISTS = pd.DataFrame([
    ["Giorgian De Arrascaeta", "Uruguay", 26, 102, "Defensor Sporting · Cruzeiro · Flamengo", "sep-2026"],
    ["Juan Román Riquelme", "Argentina", 26, 73, "Boca Juniors", "retirado"],
    ["Bruno Henrique", "Brasil", 19, None, "Flamengo", "sep-2026"],
    ["Rony", "Brasil", 19, None, "Athletico Paranaense · Palmeiras", "sep-2026"],
    ["Alejandro Silva", "Uruguay", 15, None, "Olimpia", "corte 2022 (CONMEBOL)"],
    ["Everton Ribeiro", "Brasil", 15, None, "Flamengo", "corte 2022 (CONMEBOL)"],
    ["Marcelo Delgado", "Argentina", 13, 60, "Boca Juniors", "retirado"],
    ["Júnior Sornoza", "Ecuador", 13, 45, "Independiente del Valle y otros", "ago-2025"],
    ["Lucas Pratto", "Argentina", 11, 96, "U. Católica · Vélez · Atl. Mineiro · River", "ago-2025"],
    ["Martín Palermo", "Argentina", 11, 44, "Boca Juniors", "retirado"],
], columns=["Jugador", "País", "Asistencias", "PJ", "Clubes", "Corte"])

# Participaciones de gol desde 2000 — El Gráfico, ago-2025
GA_PART = pd.DataFrame([
    ["Riquelme", 25, 26], ["Rony", 23, 21], ["De Arrascaeta", 15, 27], ["Bruno Henrique", 23, 18],
    ["Gabigol", 31, 10], ["Pratto", 30, 11], ["Borja", 31, 5], ["Tevez", 26, 9],
    ["Palermo", 23, 11], ["Fred", 25, 8], ["M. Delgado", 20, 13], ["Sornoza", 19, 13],
], columns=["Jugador", "Goles", "Asistencias"])

# Más partidos — El Gráfico, 6-may-2026
APPS = pd.DataFrame([
    ["Fábio", "Brasil", "Arquero", 114, 13, "Vasco · Cruzeiro · Fluminense"],
    ["Éver Hugo Almeida", "Uruguay", "Arquero", 113, 16, "Olimpia"],
    ["Franco Armani", "Argentina", "Arquero", 112, 12, "Atl. Nacional · River Plate"],
    ["Enzo Pérez", "Argentina", "Campo", 110, 13, "Estudiantes · River Plate"],
    ["Sergio Aquino", "Paraguay", "Campo", 107, 16, "Libertad"],
    ["Weverton", "Brasil", "Arquero", 100, 10, "Athletico Paranaense · Palmeiras"],
    ["Lucas Pratto", "Argentina", "Campo", 99, 12, "U. Católica · Vélez · Atl. Mineiro · River"],
    ["Ignacio Fernández", "Argentina", "Campo", 98, 10, "River Plate · Atl. Mineiro"],
    ["Giorgian De Arrascaeta", "Uruguay", "Campo", 98, 11, "Defensor · Cruzeiro · Flamengo"],
    ["Vladimir Soria", "Bolivia", "Campo", 96, 12, "Bolívar"],
], columns=["Jugador", "País", "Puesto", "PJ", "Ediciones", "Clubes"])

# Campeones por año — CONMEBOL / Wikipedia
CHAMPIONS = [
    (1960, "Peñarol", "Uruguay"), (1961, "Peñarol", "Uruguay"), (1962, "Santos", "Brasil"),
    (1963, "Santos", "Brasil"), (1964, "Independiente", "Argentina"), (1965, "Independiente", "Argentina"),
    (1966, "Peñarol", "Uruguay"), (1967, "Racing", "Argentina"), (1968, "Estudiantes", "Argentina"),
    (1969, "Estudiantes", "Argentina"), (1970, "Estudiantes", "Argentina"), (1971, "Nacional", "Uruguay"),
    (1972, "Independiente", "Argentina"), (1973, "Independiente", "Argentina"), (1974, "Independiente", "Argentina"),
    (1975, "Independiente", "Argentina"), (1976, "Cruzeiro", "Brasil"), (1977, "Boca Juniors", "Argentina"),
    (1978, "Boca Juniors", "Argentina"), (1979, "Olimpia", "Paraguay"), (1980, "Nacional", "Uruguay"),
    (1981, "Flamengo", "Brasil"), (1982, "Peñarol", "Uruguay"), (1983, "Grêmio", "Brasil"),
    (1984, "Independiente", "Argentina"), (1985, "Argentinos Juniors", "Argentina"), (1986, "River Plate", "Argentina"),
    (1987, "Peñarol", "Uruguay"), (1988, "Nacional", "Uruguay"), (1989, "Atlético Nacional", "Colombia"),
    (1990, "Olimpia", "Paraguay"), (1991, "Colo-Colo", "Chile"), (1992, "São Paulo", "Brasil"),
    (1993, "São Paulo", "Brasil"), (1994, "Vélez Sarsfield", "Argentina"), (1995, "Grêmio", "Brasil"),
    (1996, "River Plate", "Argentina"), (1997, "Cruzeiro", "Brasil"), (1998, "Vasco da Gama", "Brasil"),
    (1999, "Palmeiras", "Brasil"), (2000, "Boca Juniors", "Argentina"), (2001, "Boca Juniors", "Argentina"),
    (2002, "Olimpia", "Paraguay"), (2003, "Boca Juniors", "Argentina"), (2004, "Once Caldas", "Colombia"),
    (2005, "São Paulo", "Brasil"), (2006, "Internacional", "Brasil"), (2007, "Boca Juniors", "Argentina"),
    (2008, "LDU Quito", "Ecuador"), (2009, "Estudiantes", "Argentina"), (2010, "Internacional", "Brasil"),
    (2011, "Santos", "Brasil"), (2012, "Corinthians", "Brasil"), (2013, "Atlético Mineiro", "Brasil"),
    (2014, "San Lorenzo", "Argentina"), (2015, "River Plate", "Argentina"), (2016, "Atlético Nacional", "Colombia"),
    (2017, "Grêmio", "Brasil"), (2018, "River Plate", "Argentina"), (2019, "Flamengo", "Brasil"),
    (2020, "Palmeiras", "Brasil"), (2021, "Palmeiras", "Brasil"), (2022, "Flamengo", "Brasil"),
    (2023, "Fluminense", "Brasil"), (2024, "Botafogo", "Brasil"), (2025, "Flamengo", "Brasil"),
]
CHAMPS = pd.DataFrame(CHAMPIONS, columns=["Año", "Campeón", "País"])

# Finales por club (títulos / subcampeonatos) — CONMEBOL / Wikipedia, hasta la final 2025
FINALS = pd.DataFrame([
    ["Independiente", "Argentina", 7, 0], ["Boca Juniors", "Argentina", 6, 6], ["Peñarol", "Uruguay", 5, 5],
    ["River Plate", "Argentina", 4, 3], ["Estudiantes", "Argentina", 4, 1], ["Flamengo", "Brasil", 4, 1],
    ["Olimpia", "Paraguay", 3, 4], ["Palmeiras", "Brasil", 3, 4], ["Nacional", "Uruguay", 3, 3],
    ["São Paulo", "Brasil", 3, 3], ["Santos", "Brasil", 3, 2], ["Grêmio", "Brasil", 3, 2],
    ["Cruzeiro", "Brasil", 2, 2], ["Internacional", "Brasil", 2, 1], ["Atlético Nacional", "Colombia", 2, 1],
    ["América de Cali", "Colombia", 0, 4],
], columns=["Club", "País", "Títulos", "Subcampeonatos"])
FINALS["Finales"] = FINALS["Títulos"] + FINALS["Subcampeonatos"]
FINALS["Efectividad"] = (FINALS["Títulos"] / FINALS["Finales"] * 100).round(1)

# Goleador de cada edición — El Gráfico (nov-2025)
TOP_BY_YEAR = [
    (1960, 7, "Alberto Spencer"), (1961, 4, "Osvaldo Panzutto"), (1962, 6, "Coutinho · Raymondi · Spencer"),
    (1963, 7, "José Sanfilippo"), (1964, 6, "Mario Rodríguez"), (1965, 8, "Pelé"), (1966, 17, "Daniel Onega"),
    (1967, 14, "Norberto Raffo"), (1968, 11, "Tupãzinho"), (1969, 9, "Alberto Ferrero · Miguel Loayza"),
    (1970, 9, "Francisco Bertocchi · Oscar Más"), (1971, 10, "Luis Artime · Raúl Castronovo"),
    (1972, 6, "T. Guerreiro · O. Ramírez · P. Rojas · T. Cubillas"), (1973, 9, "Carlos Caszely"),
    (1974, 7, "Fernando Morena · Pedro Rocha · Terto"), (1975, 8, "Fernando Morena · Oswaldo Ramírez"),
    (1976, 13, "Palhinha"), (1977, 5, "Néstor Scotta"), (1978, 8, "Guillermo La Rosa · Néstor Scotta"),
    (1979, 6, "Miltão · Juan José Oré"), (1980, 6, "Waldemar Victorino"), (1981, 11, "Zico"),
    (1982, 7, "Fernando Morena"), (1983, 8, "Arsenio Luzardo"), (1984, 8, "Tita"), (1985, 11, "Juan Carlos Sánchez"),
    (1986, 9, "Juan Carlos de Lima"), (1987, 7, "Ricardo Gareca"), (1988, 5, "Arnoldo Iguarán"),
    (1989, 10, "Carlos Aguilera · Raúl Amarilla"), (1990, 7, "Adriano Samaniego"), (1991, 8, "Gaúcho"),
    (1992, 7, "Palhinha"), (1993, 9, "Juan Carlos Almada"), (1994, 7, "Stalin Rivas"), (1995, 12, "Mário Jardel"),
    (1996, 11, "Antony de Ávila"), (1997, 11, "Alberto Acosta"), (1998, 10, "Sérgio João"),
    (1999, 6, "5 jugadores empatados"), (2000, 15, "Luizão"), (2001, 9, "Lopes Tigrão"), (2002, 10, "Rodrigo Mendes"),
    (2003, 9, "Marcelo Delgado · Ricardo Oliveira"), (2004, 8, "Luís Fabiano"), (2005, 9, "Santiago Salcedo"),
    (2006, 5, "14 jugadores empatados"), (2007, 10, "Salvador Cabañas"), (2008, 8, "S. Cabañas · Marcelo Moreno"),
    (2009, 8, "Mauro Boselli"), (2010, 8, "Thiago Ribeiro"), (2011, 7, "Roberto Nanni · Wallyson"),
    (2012, 8, "Neymar · Matías Alustiza"), (2013, 7, "Jô"), (2014, 5, "Julio dos Santos · Nicolás Olivera"),
    (2015, 8, "Gustavo Bou"), (2016, 9, "Jonathan Calleri"), (2017, 9, "José Sand"),
    (2018, 9, "Miguel Borja · Wilson Morelo"), (2019, 7, "Gabriel Barbosa"), (2020, 8, "Fidel Martínez"),
    (2021, 11, "Gabriel Barbosa"), (2022, 12, "Pedro"), (2023, 13, "Germán Cano"), (2024, 10, "Júnior Santos"),
    (2025, 7, "José López · Adrián Martínez"),
]
TOPYEAR = pd.DataFrame(TOP_BY_YEAR, columns=["Año", "Goles", "Goleador"])

# Nacionalidad del goleador de cada edición — El Gráfico (nov-2025)
SCORER_NATION = pd.DataFrame([
    ["Brasil", 33], ["Argentina", 29], ["Uruguay", 13], ["Ecuador", 7], ["Perú", 7],
    ["Paraguay", 6], ["Colombia", 5], ["Venezuela", 2], ["Bolivia", 1], ["Chile", 1],
], columns=["País", "Veces"])

# Tabla histórica (subset, clubes con 100+ PJ) — compilación Wikipedia/worldfootball.
# Corte desigual entre clubes: se usa solo para ratios defensivos (goles recibidos por partido).
DEFENSE = pd.DataFrame([
    ["Boca Juniors", "Argentina", 308, 270], ["Estudiantes", "Argentina", 131, 115],
    ["Internacional", "Brasil", 140, 124], ["Grêmio", "Brasil", 207, 189],
    ["Vélez Sarsfield", "Argentina", 139, 127], ["Independiente", "Argentina", 154, 143],
    ["Cruzeiro", "Brasil", 166, 158], ["São Paulo", "Brasil", 199, 192],
    ["Corinthians", "Brasil", 122, 120], ["San Lorenzo", "Argentina", 138, 138],
    ["Palmeiras", "Brasil", 210, 218], ["River Plate", "Argentina", 373, 392],
    ["Nacional", "Uruguay", 401, 438], ["Peñarol", "Uruguay", 369, 449],
], columns=["Club", "País", "PJ", "GC"])
DEFENSE["GC por partido"] = (DEFENSE["GC"] / DEFENSE["PJ"]).round(3)
DEFENSE = DEFENSE.sort_values("GC por partido")

# Rachas invictas récord — El Gráfico (2025)
STREAKS = pd.DataFrame([
    ["Atlético Mineiro", "Brasil", "2019–2022", 18, 11, 7],
    ["Palmeiras", "Brasil", "2021–2022", 18, 13, 5],
    ["Sporting Cristal", "Perú", "1962–1969", 17, 9, 8],
    ["Flamengo", "Brasil", "2020–2021", 17, 12, 5],
    ["Palmeiras", "Brasil", "2023–2024", 17, 11, 6],
    ["São Paulo", "Brasil", "2024–2025", 17, 9, 8],
], columns=["Club", "País", "Período", "Partidos", "Ganados", "Empatados"])

# ──────────────────────────────────────────────────────────────────────────────
# LOGO (archivo local → Secrets → Wikimedia → emblema tipográfico)
# ──────────────────────────────────────────────────────────────────────────────
def _wikimedia_urls(filename: str):
    h = hashlib.md5(filename.encode("utf-8")).hexdigest()
    urls = []
    for proj in ("en", "commons"):
        base = f"https://upload.wikimedia.org/wikipedia/{proj}"
        if filename.lower().endswith(".svg"):
            urls.append(f"{base}/thumb/{h[0]}/{h[:2]}/{filename}/400px-{filename}.png")
        urls.append(f"{base}/{h[0]}/{h[:2]}/{filename}")
    return urls


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_logo_data_uri():
    local = Path(__file__).parent / "assets" / "libertadores_logo.png"
    if local.exists():
        return "data:image/png;base64," + base64.b64encode(local.read_bytes()).decode()

    candidates = []
    try:
        if "LOGO_URL" in st.secrets:
            candidates.append(st.secrets["LOGO_URL"])
    except Exception:
        pass
    for name in (
        "CONMEBOL_Libertadores_logo.svg", "Conmebol_Libertadores_logo.svg",
        "Copa_Libertadores_logo.svg", "CONMEBOL_Libertadores_logo.png",
        "Logo_CONMEBOL_Libertadores.svg", "Copa_Libertadores_logo.png",
    ):
        candidates.extend(_wikimedia_urls(name))

    headers = {"User-Agent": "LibertadoresDataApp/1.0 (Streamlit educational dashboard)"}
    for url in candidates:
        try:
            r = requests.get(url, headers=headers, timeout=4)
            ctype = r.headers.get("Content-Type", "")
            if r.status_code == 200 and ctype.startswith("image/") and len(r.content) > 500:
                mime = "image/svg+xml" if "svg" in ctype else ctype.split(";")[0]
                return f"data:{mime};base64," + base64.b64encode(r.content).decode()
        except Exception:
            continue
    return None



# ──────────────────────────────────────────────────────────────────────────────
# ESCUDOS DE LOS CAMPEONES (Wikipedia/Wikimedia → PNG normalizado; fallback: monograma)
# Para forzar un escudo propio: guardalo como assets/escudos/<slug>.png
# ──────────────────────────────────────────────────────────────────────────────
CHAMPION_CLUBS = [
    # club mostrado, país, slug, título en Wikipedia (es/pt)
    ("Independiente", "Argentina", "independiente", "Club Atlético Independiente"),
    ("Boca Juniors", "Argentina", "boca", "Club Atlético Boca Juniors"),
    ("Peñarol", "Uruguay", "penarol", "Club Atlético Peñarol"),
    ("Estudiantes", "Argentina", "estudiantes", "Club Estudiantes de La Plata"),
    ("River Plate", "Argentina", "river", "Club Atlético River Plate"),
    ("Flamengo", "Brasil", "flamengo", "Clube de Regatas do Flamengo"),
    ("Olimpia", "Paraguay", "olimpia", "Club Olimpia"),
    ("Palmeiras", "Brasil", "palmeiras", "Sociedade Esportiva Palmeiras"),
    ("Nacional", "Uruguay", "nacional", "Club Nacional de Football"),
    ("São Paulo", "Brasil", "saopaulo", "São Paulo Futebol Clube"),
    ("Santos", "Brasil", "santos", "Santos Futebol Clube"),
    ("Grêmio", "Brasil", "gremio", "Grêmio Foot-Ball Porto Alegrense"),
    ("Cruzeiro", "Brasil", "cruzeiro", "Cruzeiro Esporte Clube"),
    ("Internacional", "Brasil", "internacional", "Sport Club Internacional"),
    ("Atlético Nacional", "Colombia", "atlnacional", "Atlético Nacional"),
    ("Colo-Colo", "Chile", "colocolo", "Club Social y Deportivo Colo-Colo"),
    ("Atlético Mineiro", "Brasil", "atlmineiro", "Clube Atlético Mineiro"),
    ("Fluminense", "Brasil", "fluminense", "Fluminense Football Club"),
    ("Racing Club", "Argentina", "racing", "Racing Club"),
    ("Argentinos Juniors", "Argentina", "argentinos", "Asociación Atlética Argentinos Juniors"),
    ("Vélez Sarsfield", "Argentina", "velez", "Club Atlético Vélez Sarsfield"),
    ("Vasco da Gama", "Brasil", "vasco", "Club de Regatas Vasco da Gama"),
    ("Once Caldas", "Colombia", "oncecaldas", "Once Caldas"),
    ("LDU Quito", "Ecuador", "ldu", "Liga Deportiva Universitaria de Quito"),
    ("Corinthians", "Brasil", "corinthians", "Sport Club Corinthians Paulista"),
    ("San Lorenzo", "Argentina", "sanlorenzo", "Club Atlético San Lorenzo de Almagro"),
    ("Botafogo", "Brasil", "botafogo", "Botafogo de Futebol e Regatas"),
]
WIKI_UA = {"User-Agent": "LibertadoresDataApp/1.0 (Streamlit educational dashboard)"}


def _normalize_png(raw: bytes, size: int = 256) -> str:
    """Recorta márgenes transparentes y centra el escudo en un lienzo cuadrado idéntico para todos."""
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    pad = int(size * 0.06)
    im.thumbnail((size - 2 * pad, size - 2 * pad), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _wiki_thumbs(lang: str, titles):
    """Devuelve {título pedido: url de miniatura PNG} usando la API de PageImages."""
    out = {}
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={"action": "query", "titles": "|".join(titles), "prop": "pageimages",
                    "piprop": "thumbnail", "pithumbsize": 400, "format": "json",
                    "redirects": 1, "formatversion": 2},
            headers=WIKI_UA, timeout=8,
        )
        data = r.json().get("query", {})
        alias = {}
        for n in data.get("normalized", []) + data.get("redirects", []):
            alias[n["to"]] = alias.get(n["from"], n["from"])
        for page in data.get("pages", []):
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                original = page["title"]
                while original in alias:
                    original = alias[original]
                out[original] = thumb
    except Exception:
        pass
    return out


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 7)
def load_crests():
    crests = {}
    pending = []
    folder = Path(__file__).parent / "assets" / "escudos"
    for name, _, slug, title in CHAMPION_CLUBS:
        local = folder / f"{slug}.png"
        if local.exists():
            try:
                crests[slug] = _normalize_png(local.read_bytes())
                continue
            except Exception:
                pass
        pending.append((slug, title))

    for lang in ("es", "pt"):
        if not pending:
            break
        thumbs = _wiki_thumbs(lang, [t for _, t in pending])
        still = []
        for slug, title in pending:
            url = thumbs.get(title)
            if url:
                try:
                    img = requests.get(url, headers=WIKI_UA, timeout=8)
                    if img.status_code == 200 and img.headers.get("Content-Type", "").startswith("image/"):
                        crests[slug] = _normalize_png(img.content)
                        continue
                except Exception:
                    pass
            still.append((slug, title))
        pending = still
    return crests

# ──────────────────────────────────────────────────────────────────────────────
# STYLE
# ──────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root{
  --gold:#E8C15A; --gold-soft:#F6DE97; --gold-deep:#A67C1F; --ember:#E2553F;
  --ink:#0A0C12; --panel:#11141D; --panel-2:#151926; --line:#232838;
  --text:#ECE7DA; --muted:#8E8A80;
}
html, body, [data-testid="stAppViewContainer"], .stApp{
  background:
    radial-gradient(1200px 600px at 85% -10%, rgba(232,193,90,.10), transparent 60%),
    radial-gradient(900px 500px at -10% 30%, rgba(226,85,63,.06), transparent 60%),
    var(--ink) !important;
  color:var(--text);
  font-family:'Manrope', system-ui, sans-serif;
}
header[data-testid="stHeader"]{ background:transparent; }
[data-testid="stToolbar"]{ right:120px; }
.block-container{ padding-top:2.2rem; padding-bottom:4rem; max-width:1240px; }
h1,h2,h3,h4{ font-family:'Barlow Condensed', sans-serif !important; letter-spacing:.02em; color:var(--text); }
p, li, label, .stMarkdown{ color:var(--text); }

/* ── LOGO con neón dorado ── */
.lib-logo{
  position:fixed; top:14px; right:22px; z-index:999999;
  width:92px; height:92px; border-radius:22px;
  display:flex; align-items:center; justify-content:center;
  background:radial-gradient(circle at 50% 40%, rgba(232,193,90,.10), rgba(10,12,18,.85) 70%);
  border:1px solid rgba(232,193,90,.45);
  box-shadow:0 0 6px rgba(246,222,151,.35), 0 0 18px rgba(232,193,90,.22), inset 0 0 12px rgba(232,193,90,.10);
  animation:neon 3.6s ease-in-out infinite;
  backdrop-filter:blur(6px);
}
.lib-logo img{ max-width:72px; max-height:72px; filter:drop-shadow(0 0 4px rgba(246,222,151,.55)) drop-shadow(0 0 10px rgba(232,193,90,.30)); }
.lib-logo .emblem{ font-family:'Barlow Condensed'; text-align:center; line-height:.9; color:var(--gold-soft); text-shadow:0 0 6px rgba(232,193,90,.6); }
.lib-logo .emblem small{ display:block; font-size:9px; letter-spacing:.28em; color:var(--gold); }
.lib-logo .emblem b{ display:block; font-size:12px; letter-spacing:.02em; margin-top:3px; }
@keyframes neon{
  0%,100%{ box-shadow:0 0 6px rgba(246,222,151,.30), 0 0 16px rgba(232,193,90,.18), inset 0 0 10px rgba(232,193,90,.08); }
  50%   { box-shadow:0 0 9px rgba(246,222,151,.50), 0 0 26px rgba(232,193,90,.32), inset 0 0 14px rgba(232,193,90,.14); }
}
@media (max-width: 640px){ .lib-logo{ width:64px; height:64px; top:10px; right:10px; } .lib-logo img{ max-width:50px; max-height:50px; } }

/* ── HERO ── */
.hero{ padding:28px 0 8px 0; margin-right:110px; display:flex; align-items:center; justify-content:space-between; gap:24px; }
.hero-cup{ text-align:center; flex:0 0 auto; filter:drop-shadow(0 0 18px rgba(232,193,90,.28)); animation:float 6s ease-in-out infinite; }
.hero-cup-cap{ font-family:'IBM Plex Mono'; font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--gold); margin-top:8px; }
@keyframes float{ 0%,100%{ transform:translateY(0); } 50%{ transform:translateY(-6px); } }
@media (max-width: 900px){ .hero-cup{ display:none; } }
.sec .num svg{ vertical-align:-2px; margin-right:6px; }
.crests{ display:grid; grid-template-columns:repeat(auto-fill, minmax(96px, 1fr)); gap:14px; margin:22px 0 10px 0; }
.crest{ background:linear-gradient(180deg, var(--panel-2), var(--panel)); border:1px solid var(--line); border-radius:14px; padding:12px 8px 10px; text-align:center; transition:border-color .2s, transform .2s; }
.crest:hover{ border-color:var(--gold); transform:translateY(-2px); }
.crest img{ width:64px; height:64px; object-fit:contain; display:block; margin:0 auto; }
.crest .mono{ width:64px; height:64px; margin:0 auto; border-radius:50%; border:1px solid var(--gold-deep); display:flex; align-items:center; justify-content:center; font-family:'Barlow Condensed'; font-weight:800; font-size:22px; color:var(--gold-soft); }
.crest .n{ font-size:11.5px; color:var(--text); margin-top:8px; line-height:1.2; }
.crest .t{ font-family:'IBM Plex Mono'; font-size:10.5px; color:var(--gold); margin-top:3px; }
.signature{ text-align:center; margin:34px 0 6px 0; font-family:'Barlow Condensed'; font-size:22px; letter-spacing:.06em; color:var(--gold); text-shadow:0 0 10px rgba(232,193,90,.35); }
.eyebrow{ font-family:'IBM Plex Mono'; font-size:12px; letter-spacing:.32em; text-transform:uppercase; color:var(--gold); }
.hero h1{ font-size:clamp(46px, 7vw, 92px); line-height:.9; margin:10px 0 14px 0; font-weight:800; text-transform:uppercase; }
.hero h1 span{ background:linear-gradient(180deg, var(--gold-soft), var(--gold) 55%, var(--gold-deep)); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero p.lead{ max-width:720px; color:#CFC8B8; font-size:17px; line-height:1.6; }
.rule{ height:1px; background:linear-gradient(90deg, var(--gold), transparent); margin:26px 0 8px 0; opacity:.6; }

/* ── KPI ── */
.kpis{ display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:14px; margin:18px 0 6px 0; }
@media (max-width: 980px){ .kpis{ grid-template-columns:repeat(2, minmax(0,1fr)); } }
.kpi{ background:linear-gradient(180deg, var(--panel-2), var(--panel)); border:1px solid var(--line); border-radius:16px; padding:16px 16px 14px; position:relative; overflow:hidden; }
.kpi:before{ content:""; position:absolute; inset:0 0 auto 0; height:2px; background:linear-gradient(90deg, var(--gold), transparent); }
.kpi .v{ font-family:'Barlow Condensed'; font-weight:800; font-size:44px; line-height:1; color:var(--gold-soft); }
.kpi .l{ font-size:12.5px; color:var(--muted); margin-top:6px; line-height:1.35; }
.kpi .l b{ color:var(--text); font-weight:600; }

/* ── SECTION ── */
.sec{ margin:56px 0 10px 0; }
.sec .num{ font-family:'IBM Plex Mono'; color:var(--ember); font-size:13px; letter-spacing:.2em; }
.sec h2{ font-size:clamp(32px, 4.4vw, 50px); margin:4px 0 6px 0; text-transform:uppercase; font-weight:800; }
.sec p{ color:#BDB6A6; max-width:760px; line-height:1.6; }

/* ── CARDS ── */
.card{ background:linear-gradient(180deg, var(--panel-2), var(--panel)); border:1px solid var(--line); border-radius:18px; padding:20px 22px; height:100%; }
.card .tag{ font-family:'IBM Plex Mono'; font-size:11px; letter-spacing:.2em; text-transform:uppercase; color:var(--gold); }
.card .big{ font-family:'Barlow Condensed'; font-size:58px; font-weight:800; line-height:.95; color:var(--gold-soft); margin-top:6px; }
.card .who{ font-family:'Barlow Condensed'; font-size:26px; font-weight:700; margin-top:2px; }
.card .meta{ color:var(--muted); font-size:13.5px; margin-top:6px; line-height:1.5; }
.card.ember .big{ color:#F08A76; }
.card.ember .tag{ color:var(--ember); }

.fact{ border-left:2px solid var(--gold); padding:4px 0 4px 14px; margin:10px 0; }
.fact b{ font-family:'Barlow Condensed'; font-size:22px; color:var(--gold-soft); letter-spacing:.02em; }
.fact span{ display:block; color:#BDB6A6; font-size:14px; line-height:1.5; }

.note{ font-size:12.5px; color:var(--muted); border:1px dashed var(--line); border-radius:12px; padding:10px 14px; margin-top:10px; line-height:1.55; }
.foot{ color:var(--muted); font-size:12.5px; line-height:1.7; }
.foot a{ color:var(--gold); text-decoration:none; }

/* Widgets */
div[role="radiogroup"] label p{ font-family:'IBM Plex Mono'; font-size:12.5px; }
[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:14px; overflow:hidden; }
.stTabs [data-baseweb="tab-list"]{ gap:6px; }
.stTabs [data-baseweb="tab"]{ font-family:'IBM Plex Mono'; font-size:12.5px; letter-spacing:.08em; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:8px 14px; }
.stTabs [aria-selected="true"]{ border-color:var(--gold) !important; color:var(--gold-soft) !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

logo_uri = load_logo_data_uri()
if logo_uri:
    logo_html = f'<div class="lib-logo" title="CONMEBOL Libertadores"><img src="{logo_uri}" alt="CONMEBOL Libertadores"></div>'
else:
    logo_html = ('<div class="lib-logo" title="CONMEBOL Libertadores"><div class="emblem">'
                 '<small>CONMEBOL</small><b>LIBERTADORES</b></div></div>')
st.markdown(logo_html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def style_fig(fig, height=460, legend=False):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color=TEXT, size=13),
        margin=dict(l=10, r=20, t=30, b=10),
        hoverlabel=dict(bgcolor="#151926", bordercolor=GOLD, font=dict(family="Manrope", color=TEXT, size=13)),
        showlegend=legend,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=12, color=MUTED), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=LINE, zeroline=False, linecolor=LINE, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=LINE, zeroline=False, linecolor=LINE, tickfont=dict(color=TEXT)),
    )
    return fig


def gold_scale(n):
    base = [GOLD_SOFT, GOLD, "#D4A845", "#C39638", "#B0852C", GOLD_DEEP]
    return [base[min(i, len(base) - 1)] for i in range(n)]



def trophy_svg(size=40, uid="t"):
    """Ícono de copa genérico (dibujo propio), en dorado."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="g{uid}" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#F6DE97"/><stop offset=".55" stop-color="#E8C15A"/><stop offset="1" stop-color="#A67C1F"/></linearGradient></defs>
<path d="M18 6h28v14c0 9-6 16-14 17-8-1-14-8-14-17V6z" fill="url(#g{uid})"/>
<path d="M18 11H9c0 9 4 14 11 15M46 11h9c0 9-4 14-11 15" fill="none" stroke="url(#g{uid})" stroke-width="3" stroke-linecap="round"/>
<rect x="29" y="37" width="6" height="9" rx="1" fill="url(#g{uid})"/>
<path d="M21 46h22l3 6H18z" fill="url(#g{uid})"/>
<rect x="15" y="52" width="34" height="6" rx="2" fill="url(#g{uid})"/>
<path d="M26 12c-1 6 0 12 4 16" stroke="#FFF6D8" stroke-opacity=".55" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>"""

def section(num, title, desc):
    st.markdown(f'<div class="sec"><div class="num">{trophy_svg(16, num[:2])} {num}</div><h2>{title}</h2><p>{desc}</p></div>',
                unsafe_allow_html=True)


def card(tag, big, who, meta, ember=False):
    cls = "card ember" if ember else "card"
    return f'<div class="{cls}"><div class="tag">{tag}</div><div class="big">{big}</div><div class="who">{who}</div><div class="meta">{meta}</div></div>'


# ──────────────────────────────────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-txt">
    <div class="eyebrow">Análisis cuantitativo · 1960 — 2026</div>
    <h1>La Gloria Eterna<br><span>en números</span></h1>
    <p class="lead">Sesenta y seis ediciones terminadas y una en juego. Goleadores, asistidores, arqueros,
    clubes y finales de la copa más importante de Sudamérica, contados con datos.</p>
  </div>
  <div class="hero-cup">{trophy_svg(210, "hero")}<div class="hero-cup-cap">66 copas levantadas</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpis">
  <div class="kpi"><div class="v">66</div><div class="l"><b>Ediciones completas</b><br>1960 → 2025 · la 2026 está en semifinales</div></div>
  <div class="kpi"><div class="v">54</div><div class="l"><b>Goles de Alberto Spencer</b><br>Máximo goleador histórico {FLAGS['Ecuador']}</div></div>
  <div class="kpi"><div class="v">7/7</div><div class="l"><b>Independiente</b><br>Finales jugadas, finales ganadas {FLAGS['Argentina']}</div></div>
  <div class="kpi"><div class="v">681</div><div class="l"><b>Goles de River Plate</b><br>El club más goleador {FLAGS['Argentina']}</div></div>
  <div class="kpi"><div class="v">25·25</div><div class="l"><b>Argentina · Brasil</b><br>Títulos por país, empatados</div></div>
</div>
<div class="rule"></div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 01 · GOLEADORES
# ──────────────────────────────────────────────────────────────────────────────
section("01 — GOLEADORES", "Los diez cañoneros de la historia",
        "Spencer sigue solo arriba desde los años 60. Pasá el cursor por cada barra para ver en qué clubes "
        "hizo sus goles cada jugador; cambiá la métrica para ver quién fue más eficiente.")

metric = st.radio("Métrica", ["Goles totales", "Promedio de gol por partido"], horizontal=True,
                  label_visibility="collapsed", key="scorer_metric")
col_a, col_b = st.columns([1.55, 1], gap="large")

with col_a:
    df = SCORERS.copy()
    df["Etiqueta"] = df.apply(lambda r: f"{FLAGS.get(r['País'], '')}  {r['Jugador']}", axis=1)
    xcol = "Goles" if metric == "Goles totales" else "Promedio"
    df = df.sort_values(xcol, ascending=True)
    colors = [GOLD_SOFT if j == "Alberto Spencer" else "#C9A24A" for j in df["Jugador"]]
    fig = go.Figure(go.Bar(
        x=df[xcol], y=df["Etiqueta"], orientation="h",
        marker=dict(color=colors, line=dict(color=GOLD_DEEP, width=1)),
        text=df[xcol].map(lambda v: f"{v:.2f}" if isinstance(v, float) and v < 5 else f"{int(v)}"),
        textposition="outside", textfont=dict(family="Barlow Condensed", size=18, color=GOLD_SOFT),
        customdata=df[["País", "PJ", "Goles", "Promedio", "Clubes", "Debut"]].values,
        hovertemplate=("<b>%{y}</b><br>%{customdata[0]} · debut %{customdata[5]}<br>"
                       "Goles: <b>%{customdata[2]}</b> en %{customdata[1]} PJ (%{customdata[3]} por partido)<br>"
                       "<span style='color:#8E8A80'>%{customdata[4]}</span><extra></extra>"),
    ))
    style_fig(fig, height=500)
    fig.update_xaxes(showgrid=False, showticklabels=False)
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)

with col_b:
    bub = SCORERS.copy()
    fig2 = px.scatter(bub, x="PJ", y="Goles", size="Goles", color="País",
                      color_discrete_map=COUNTRY_COLORS, hover_name="Jugador",
                      hover_data={"Clubes": True, "Promedio": True, "País": False, "Goles": True, "PJ": True},
                      size_max=46)
    fig2.update_traces(marker=dict(line=dict(width=1, color=INK), opacity=.9))
    style_fig(fig2, height=500, legend=True)
    fig2.update_xaxes(title=dict(text="Partidos jugados", font=dict(color=MUTED, size=12)))
    fig2.update_yaxes(title=dict(text="Goles", font=dict(color=MUTED, size=12)))
    st.plotly_chart(fig2, width="stretch", config=PLOT_CONFIG)

with st.expander("Ver tabla completa de goleadores"):
    show = SCORERS[["Rank", "Jugador", "País", "Goles", "PJ", "Promedio", "Debut", "Clubes"]].copy()
    show["País"] = show["País"].map(lambda p: f"{FLAGS.get(p, '')} {p}")
    st.dataframe(show, hide_index=True, width="stretch")
st.markdown('<div class="note">Empates en goles ordenados por promedio. Corte: noviembre de 2025 '
            '(los goles de la edición 2026 pueden mover las posiciones del 4° al 10°). Fuente: registros '
            'CONMEBOL compilados por El Gráfico y worldfootball.net.</div>', unsafe_allow_html=True)

# Goleador por edición
st.markdown("#### El goleador de cada edición")
yr = st.slider("Rango de años", 1960, 2025, (1960, 2025), key="yr_range", label_visibility="collapsed")
ty = TOPYEAR[(TOPYEAR["Año"] >= yr[0]) & (TOPYEAR["Año"] <= yr[1])]
fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=ty["Año"], y=ty["Goles"], mode="lines+markers",
    line=dict(color=GOLD, width=2, shape="spline", smoothing=.6),
    marker=dict(size=[16 if g >= 13 else 8 for g in ty["Goles"]],
                color=[EMBER if g >= 13 else GOLD_SOFT for g in ty["Goles"]],
                line=dict(color=INK, width=1)),
    fill="tozeroy", fillcolor="rgba(232,193,90,0.07)",
    customdata=ty["Goleador"],
    hovertemplate="<b>%{x}</b> · %{y} goles<br>%{customdata}<extra></extra>",
))
if 1966 >= yr[0] and 1966 <= yr[1]:
    fig3.add_annotation(x=1966, y=17, text="Onega · 17 (récord)", showarrow=True, arrowcolor=EMBER,
                        ax=50, ay=-18, font=dict(family="IBM Plex Mono", size=11, color=EMBER))
style_fig(fig3, height=340)
fig3.update_yaxes(title=dict(text="Goles del goleador", font=dict(color=MUTED, size=12)), rangemode="tozero")
st.plotly_chart(fig3, width="stretch", config=PLOT_CONFIG)

c1, c2 = st.columns([1, 1], gap="large")
with c1:
    sn = SCORER_NATION.sort_values("Veces")
    fig4 = go.Figure(go.Bar(
        x=sn["Veces"], y=[f"{FLAGS.get(p, '')} {p}" for p in sn["País"]], orientation="h",
        marker=dict(color=[COUNTRY_COLORS.get(p, GOLD) for p in sn["País"]]),
        text=sn["Veces"], textposition="outside", textfont=dict(family="Barlow Condensed", size=16, color=TEXT),
        hovertemplate="%{y}: %{x} goleadores de edición<extra></extra>",
    ))
    style_fig(fig4, height=360)
    fig4.update_layout(title=dict(text="Nacionalidad del goleador de cada edición", font=dict(family="Barlow Condensed", size=20, color=TEXT)))
    fig4.update_xaxes(showgrid=False, showticklabels=False)
    st.plotly_chart(fig4, width="stretch", config=PLOT_CONFIG)
with c2:
    st.markdown("""
    <div class="fact"><b>Fernando Morena · 3 veces</b><span>El único que fue goleador en tres ediciones distintas (1974, 1975 y 1982), siempre con Peñarol.</span></div>
    <div class="fact"><b>Daniel Onega · 17 goles en 1966</b><span>Récord de goles en una sola edición. River perdió esa final contra Peñarol en el desempate de Santiago.</span></div>
    <div class="fact"><b>Brasil · 33 goleadores</b><span>El país que más veces aportó al máximo artillero del torneo, seguido de Argentina con 29.</span></div>
    <div class="fact"><b>Rogério Ceni · 14 goles</b><span>El arquero más goleador de la historia de la Copa, todos con São Paulo.</span></div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 02 · ASISTIDORES
# ──────────────────────────────────────────────────────────────────────────────
section("02 — ASISTIDORES", "Los que pusieron la pelota",
        "CONMEBOL no tiene un registro oficial de asistencias para las primeras décadas de la Copa, así que este "
        "ranking cubre la era con datos confiables (desde 2000). Riquelme y De Arrascaeta comparten la cima.")

c1, c2 = st.columns([1.4, 1], gap="large")
with c1:
    da = ASSISTS.sort_values("Asistencias", ascending=True).copy()
    da["Etiqueta"] = da.apply(lambda r: f"{FLAGS.get(r['País'], '')}  {r['Jugador']}", axis=1)
    top_names = {"Giorgian De Arrascaeta", "Juan Román Riquelme"}
    fig5 = go.Figure(go.Bar(
        x=da["Asistencias"], y=da["Etiqueta"], orientation="h",
        marker=dict(color=[GOLD_SOFT if n in top_names else "#7E93B8" for n in da["Jugador"]]),
        text=da["Asistencias"], textposition="outside",
        textfont=dict(family="Barlow Condensed", size=18, color=GOLD_SOFT),
        customdata=da[["País", "Clubes", "Corte"]].values,
        hovertemplate="<b>%{y}</b><br>%{x} asistencias<br>%{customdata[1]}<br><span style='color:#8E8A80'>Dato al: %{customdata[2]}</span><extra></extra>",
    ))
    style_fig(fig5, height=480)
    fig5.update_xaxes(showgrid=False, showticklabels=False)
    st.plotly_chart(fig5, width="stretch", config=PLOT_CONFIG)
with c2:
    gp = GA_PART.copy()
    gp["Total"] = gp["Goles"] + gp["Asistencias"]
    gp = gp.sort_values("Total", ascending=True)
    fig6 = go.Figure()
    fig6.add_trace(go.Bar(y=gp["Jugador"], x=gp["Goles"], name="Goles", orientation="h",
                          marker_color=GOLD, hovertemplate="%{y}: %{x} goles<extra></extra>"))
    fig6.add_trace(go.Bar(y=gp["Jugador"], x=gp["Asistencias"], name="Asistencias", orientation="h",
                          marker_color="#7E93B8", hovertemplate="%{y}: %{x} asistencias<extra></extra>"))
    style_fig(fig6, height=480, legend=True)
    fig6.update_layout(barmode="stack", margin=dict(l=10, r=20, t=60, b=10),
                       legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom"),
                       title=dict(text="Participaciones de gol desde 2000", y=.98,
                                  font=dict(family="Barlow Condensed", size=20, color=TEXT)))
    st.plotly_chart(fig6, width="stretch", config=PLOT_CONFIG)

st.markdown("""<div class="note">Cortes distintos según el jugador (columna “Dato al” en el detalle). Los jugadores
en actividad pueden haber sumado en la edición 2026. Fuentes: ranking oficial de asistencias CONMEBOL 2012-2022,
El Gráfico (agosto 2025 y septiembre 2026).</div>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 03 · CLUBES
# ──────────────────────────────────────────────────────────────────────────────
section("03 — CLUBES", "Récords colectivos",
        "La tabla histórica acumulada hasta la final de 2025: quién más goles hizo, quién más recibió y quién más títulos ganó.")

k1, k2, k4 = st.columns(3, gap="medium")
k1.markdown(card("Más goles a favor", "681", f"{FLAGS['Argentina']} River Plate",
                 "Argentina · 202 victorias y 647 puntos, también récords. Diferencia de gol +250."), unsafe_allow_html=True)
k2.markdown(card("Más goles en contra", "475", f"{FLAGS['Uruguay']} Nacional",
                 "Uruguay · consecuencia de ser el club con más participaciones (52) y más partidos jugados.", ember=True),
            unsafe_allow_html=True)
k4.markdown(card("Más títulos", "7", f"{FLAGS['Argentina']} Independiente",
                 "Argentina · «Rey de Copas»: 1964, 65, 72, 73, 74, 75 y 84."), unsafe_allow_html=True)

st.markdown("""<div class="note">Goles a favor/en contra: tabla histórica basada en RSSSF (actualizada a la final 2025).</div>""", unsafe_allow_html=True)

st.markdown("#### Títulos por país y línea de tiempo de campeones")
c1, c2 = st.columns([1, 1.6], gap="large")
with c1:
    tp = CHAMPS.groupby("País").size().reset_index(name="Títulos").sort_values("Títulos", ascending=False)
    fig7 = go.Figure(go.Pie(
        labels=[f"{FLAGS.get(p, '')} {p}" for p in tp["País"]], values=tp["Títulos"], hole=.62,
        marker=dict(colors=[COUNTRY_COLORS.get(p, GOLD) for p in tp["País"]], line=dict(color=INK, width=2)),
        textinfo="value", textfont=dict(family="Barlow Condensed", size=18, color=INK),
        hovertemplate="%{label}: %{value} títulos (%{percent})<extra></extra>", sort=False,
    ))
    fig7.add_annotation(text="<b>66</b><br><span style='font-size:12px;color:#8E8A80'>títulos</span>",
                        showarrow=False, font=dict(family="Barlow Condensed", size=40, color=GOLD_SOFT))
    style_fig(fig7, height=400, legend=True)
    fig7.update_layout(legend=dict(orientation="v", y=.5, x=1.0))
    st.plotly_chart(fig7, width="stretch", config=PLOT_CONFIG)
with c2:
    countries = sorted(CHAMPS["País"].unique())
    sel = st.multiselect("Filtrar países", countries, default=countries, key="champ_countries",
                         label_visibility="collapsed")
    cd = CHAMPS[CHAMPS["País"].isin(sel)] if sel else CHAMPS
    fig8 = go.Figure()
    for pais in sorted(cd["País"].unique()):
        sub = cd[cd["País"] == pais]
        fig8.add_trace(go.Scatter(
            x=sub["Año"], y=[pais] * len(sub), mode="markers", name=pais,
            marker=dict(size=15, symbol="diamond", color=COUNTRY_COLORS.get(pais, GOLD), line=dict(color=INK, width=1)),
            customdata=sub["Campeón"], hovertemplate="<b>%{x}</b> · %{customdata}<extra></extra>",
        ))
    style_fig(fig8, height=360)
    fig8.add_vrect(x0=2018.5, x1=2025.5, fillcolor="rgba(242,207,74,.07)", line_width=0)
    fig8.add_annotation(x=2022, y=1.08, yref="paper", text="7 títulos brasileños seguidos",
                        showarrow=False, font=dict(family="IBM Plex Mono", size=11, color=GOLD))
    st.plotly_chart(fig8, width="stretch", config=PLOT_CONFIG)

# ──────────────────────────────────────────────────────────────────────────────
# 04 · VALLA INVICTA
# ──────────────────────────────────────────────────────────────────────────────
section("04 — VALLA INVICTA", "La defensa más difícil de vulnerar",
        "Medimos la solidez con el promedio de goles recibidos por partido entre los clubes con más de 100 partidos "
        "de Copa. Boca y Estudiantes quedan prácticamente empatados arriba.")

c1, c2 = st.columns([1.45, 1], gap="large")
with c1:
    dd = DEFENSE.sort_values("GC por partido", ascending=False)
    best = DEFENSE.iloc[0]["Club"]
    fig9 = go.Figure(go.Bar(
        x=dd["GC por partido"], y=[f"{FLAGS.get(p, '')} {c}" for c, p in zip(dd["Club"], dd["País"])],
        orientation="h",
        marker=dict(color=[GOLD_SOFT if c == best else ("#6F7891" if v > 1 else "#B79343")
                           for c, v in zip(dd["Club"], dd["GC por partido"])]),
        text=dd["GC por partido"].map(lambda v: f"{v:.2f}"), textposition="outside",
        textfont=dict(family="Barlow Condensed", size=16, color=TEXT),
        customdata=dd[["PJ", "GC"]].values,
        hovertemplate="<b>%{y}</b><br>%{customdata[1]} goles recibidos en %{customdata[0]} partidos<br>%{x:.3f} por partido<extra></extra>",
    ))
    fig9.add_vline(x=1, line=dict(color=EMBER, width=1, dash="dot"))
    fig9.add_annotation(x=1, y=1.04, yref="paper", text="1 gol por partido", showarrow=False,
                        font=dict(family="IBM Plex Mono", size=11, color=EMBER))
    style_fig(fig9, height=520)
    fig9.update_xaxes(showgrid=False, showticklabels=False, range=[0, 1.4])
    st.plotly_chart(fig9, width="stretch", config=PLOT_CONFIG)
with c2:
    st.markdown(card("Mejor promedio defensivo", "0,88", f"{FLAGS['Argentina']} Boca Juniors",
                     "Argentina · goles recibidos por partido en la Copa. Seis títulos sostenidos desde el arco."),
                unsafe_allow_html=True)
    st.markdown("""
    <div class="fact"><b>Hugo Gatti</b><span>El arco del bicampeonato 1977–1978.</span></div>
    <div class="fact"><b>Óscar Córdoba</b><span>Figura del bicampeonato 2000–2001, con definiciones por penales en ambas finales.</span></div>
    <div class="fact"><b>Roberto Abbondanzieri</b><span>Campeón en 2003 y 2007.</span></div>
    <div class="fact"><b>Esteban Andrada</b><span>En 2019 encadenó 1.128 minutos sin goles sumando Libertadores y torneo local, récord del fútbol argentino.</span></div>
    """, unsafe_allow_html=True)

st.markdown("""<div class="note">Ratio calculado sobre la tabla histórica compilada en Wikipedia (fuente worldfootball.net),
cuyo corte no es uniforme entre clubes. Sirve para comparar, no como cifra oficial. CONMEBOL no publica un conteo histórico
de vallas invictas por club.</div>""", unsafe_allow_html=True)

st.markdown("#### Rachas invictas récord (partidos seguidos sin perder)")
sk = STREAKS.copy()
sk["Etiqueta"] = sk["Club"] + " · " + sk["Período"]
fig10 = go.Figure()
fig10.add_trace(go.Bar(x=sk["Etiqueta"], y=sk["Ganados"], name="Ganados", marker_color=GOLD,
                       hovertemplate="%{x}<br>%{y} ganados<extra></extra>"))
fig10.add_trace(go.Bar(x=sk["Etiqueta"], y=sk["Empatados"], name="Empatados", marker_color="#5C6680",
                       hovertemplate="%{x}<br>%{y} empatados<extra></extra>"))
style_fig(fig10, height=330, legend=True)
fig10.update_layout(barmode="stack")
fig10.update_xaxes(tickfont=dict(color=TEXT, size=11))
st.plotly_chart(fig10, width="stretch", config=PLOT_CONFIG)

# ──────────────────────────────────────────────────────────────────────────────
# 05 · PRESENCIAS
# ──────────────────────────────────────────────────────────────────────────────
section("05 — PRESENCIAS", "Los hombres récord",
        "En mayo de 2026 Fábio superó a Éver Hugo Almeida, dueño del récord desde 1989. Cuatro de los seis primeros "
        "son arqueros: la longevidad en la Copa se juega bajo los tres palos.")

c1, c2 = st.columns([1, 1.5], gap="large")
with c1:
    st.markdown(card("Más partidos en la historia", "118", f"{FLAGS['Brasil']} Fábio",
                     "Brasil · arquero · Vasco, Cruzeiro y Fluminense. Superó el récord con 114 el 6 de mayo de 2026 "
                     "y siguió sumando; además es el jugador más veterano en disputar la Copa (45 años)."),
                unsafe_allow_html=True)
    only_gk = st.toggle("Resaltar solo arqueros", value=False, key="gk_toggle")
with c2:
    ap = APPS.sort_values("PJ", ascending=True).copy()
    ap["Etiqueta"] = ap.apply(lambda r: f"{FLAGS.get(r['País'], '')}  {r['Jugador']}", axis=1)
    if only_gk:
        cols = [GOLD_SOFT if p == "Arquero" else "#2C3245" for p in ap["Puesto"]]
    else:
        cols = [GOLD_SOFT if p == "Arquero" else "#7E93B8" for p in ap["Puesto"]]
    fig11 = go.Figure(go.Bar(
        x=ap["PJ"], y=ap["Etiqueta"], orientation="h", marker=dict(color=cols),
        text=ap["PJ"], textposition="outside", textfont=dict(family="Barlow Condensed", size=17, color=TEXT),
        customdata=ap[["Puesto", "Ediciones", "Clubes"]].values,
        hovertemplate="<b>%{y}</b><br>%{x} partidos · %{customdata[1]} ediciones<br>%{customdata[0]} · %{customdata[2]}<extra></extra>",
    ))
    style_fig(fig11, height=460)
    fig11.update_xaxes(showgrid=False, showticklabels=False, range=[80, 122])
    st.plotly_chart(fig11, width="stretch", config=PLOT_CONFIG)
st.markdown("""<div class="note">Ranking: El Gráfico, 6 de mayo de 2026 (Fábio figura con 114, el día que rompió el récord).
La cifra de 118 de la tarjeta corresponde a su conteo posterior en la edición 2026 (Wikipedia). Almeida nació en Uruguay
y se nacionalizó paraguayo.</div>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 06 · FINALES
# ──────────────────────────────────────────────────────────────────────────────
section("06 — FINALES", "El mejor puntuado en las finales",
        "Rendimiento = títulos ganados sobre finales disputadas. Independiente nunca perdió una final: 7 de 7.")

mode = st.radio("Vista", ["Efectividad en finales", "Finales ganadas vs. perdidas"], horizontal=True,
                label_visibility="collapsed", key="finals_mode")
fd = FINALS.copy()
if mode == "Efectividad en finales":
    fd = fd[fd["Finales"] >= 3].sort_values(["Efectividad", "Títulos"], ascending=[True, True])
    fig12 = go.Figure(go.Bar(
        x=fd["Efectividad"], y=[f"{FLAGS.get(p, '')} {c}" for c, p in zip(fd["Club"], fd["País"])],
        orientation="h",
        marker=dict(color=[GOLD_SOFT if e == 100 else ("#C9A24A" if e >= 50 else "#5C6680") for e in fd["Efectividad"]]),
        text=[f"{e:.0f}%  ·  {t}/{f}" for e, t, f in zip(fd["Efectividad"], fd["Títulos"], fd["Finales"])],
        textposition="outside", textfont=dict(family="Barlow Condensed", size=16, color=TEXT),
        hovertemplate="<b>%{y}</b><br>Efectividad: %{x:.1f}%<extra></extra>",
    ))
    style_fig(fig12, height=560)
    fig12.update_xaxes(range=[0, 125], showgrid=False, showticklabels=False)
else:
    fd = fd.sort_values(["Finales", "Títulos"], ascending=[True, True])
    labels = [f"{FLAGS.get(p, '')} {c}" for c, p in zip(fd["Club"], fd["País"])]
    fig12 = go.Figure()
    fig12.add_trace(go.Bar(y=labels, x=fd["Títulos"], name="Ganadas", orientation="h", marker_color=GOLD,
                           hovertemplate="%{y}: %{x} ganadas<extra></extra>"))
    fig12.add_trace(go.Bar(y=labels, x=fd["Subcampeonatos"], name="Perdidas", orientation="h", marker_color=EMBER,
                           hovertemplate="%{y}: %{x} perdidas<extra></extra>"))
    style_fig(fig12, height=560, legend=True)
    fig12.update_layout(barmode="stack")
st.plotly_chart(fig12, width="stretch", config=PLOT_CONFIG)

c1, c2, c3 = st.columns(3, gap="medium")
c1.markdown(card("Invicto en finales", "100%", f"{FLAGS['Argentina']} Independiente",
                 "7 finales, 7 títulos. Tetracampeón seguido entre 1972 y 1975."), unsafe_allow_html=True)
c2.markdown(card("Más finales jugadas", "12", f"{FLAGS['Argentina']} Boca Juniors",
                 "6 ganadas y 6 perdidas: también es el club con más finales perdidas.", ember=True), unsafe_allow_html=True)
c3.markdown(card("Último campeón", "4ª", f"{FLAGS['Brasil']} Flamengo",
                 "Le ganó 1-0 a Palmeiras en Lima (2025). La edición 2026 está en semifinales."), unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 07 · DATOS QUE VALEN ORO
# ──────────────────────────────────────────────────────────────────────────────
section("07 — DATOS QUE VALEN ORO", "Curiosidades de la Gloria Eterna", "")
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.markdown("""
    <div class="fact"><b>11 – 2</b><span>Peñarol a Valencia de Venezuela en 1970: la goleada más abultada y el partido con más goles de la historia.</span></div>
    <div class="fact"><b>3 Copas seguidas</b><span>Estudiantes (1968-70) e Independiente (1972-75) se quedaron con trofeos en propiedad.</span></div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="fact"><b>18 partidos invicto</b><span>Récord compartido por Atlético Mineiro (2019-22) y Palmeiras (2021-22).</span></div>
    <div class="fact"><b>Flamengo 2022 · campeón invicto</b><span>13 partidos, 12 victorias y 1 empate (94,9% de los puntos): la mejor campaña de los siete campeones que nunca perdieron en toda la Copa.</span></div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="fact"><b>Brasil 2019 → 2025</b><span>Siete campeones brasileños consecutivos: la racha más larga de un país.</span></div>
    <div class="fact"><b>52 participaciones</b><span>Nacional de Montevideo es el club que más veces jugó la Copa y el que más partidos acumula.</span></div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# FOOTER · FUENTES
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
st.markdown("""
<div class="foot">
<b style="color:#E8C15A;font-family:'IBM Plex Mono';letter-spacing:.2em;">METODOLOGÍA Y FUENTES</b><br>
CONMEBOL no publica un dataset histórico abierto y descargable de la Libertadores. Los datos provienen de los registros
oficiales difundidos por CONMEBOL y de compilaciones estadísticas que los replican: El Gráfico (goleadores, presencias,
asistencias, rachas), RSSSF / Wikipedia (tabla histórica, finales), worldfootball.net y ESPN. Cada gráfico indica su fecha
de corte. Datos actualizados a octubre de 2026; la edición 2026 todavía no terminó.<br><br>
<a href="https://www.conmebol.com/conmebol-libertadores/" target="_blank">conmebol.com</a> ·
<a href="https://www.rsssf.org/sacups/copalib.html" target="_blank">RSSSF</a> ·
<a href="https://www.elgrafico.com.ar/categoria/1065/conmebol-libertadores" target="_blank">El Gráfico</a> ·
<a href="https://en.wikipedia.org/wiki/Copa_Libertadores" target="_blank">Wikipedia</a>
</div>
""", unsafe_allow_html=True)

titles_by_club = CHAMPS.groupby("Campeón").size().to_dict()
alias_titles = {"Racing Club": "Racing"}
crest_imgs = load_crests()
tiles = []
for name, pais, slug, _ in sorted(CHAMPION_CLUBS, key=lambda c: (-titles_by_club.get(alias_titles.get(c[0], c[0]), 0), c[0])):
    n_tit = titles_by_club.get(alias_titles.get(name, name), 0)
    if slug in crest_imgs:
        visual = f'<img src="{crest_imgs[slug]}" alt="Escudo de {name}" loading="lazy">'
    else:
        initials = "".join(w[0] for w in name.replace("-", " ").split()[:2]).upper()
        visual = f'<div class="mono">{initials}</div>'
    tiles.append(f'<div class="crest" title="{name} · {n_tit} título(s)">{visual}'
                 f'<div class="n">{FLAGS.get(pais, "")} {name}</div>'
                 f'<div class="t">{"🏆" * n_tit if n_tit <= 4 else f"🏆 × {n_tit}"}</div></div>')
st.markdown(f"""
<div class="sec" style="margin-top:40px"><div class="num">{trophy_svg(16, "cl")} CAMPEONES</div>
<h2>Los 27 campeones de América</h2></div>
<div class="crests">{"".join(tiles)}</div>
""", unsafe_allow_html=True)
st.markdown('<div class="signature">Análisis de datos hecho por Valentín Gerold en colaboración con la IA</div>',
            unsafe_allow_html=True)

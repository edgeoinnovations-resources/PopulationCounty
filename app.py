"""
US County Population 3D Map — Streamlit App
Displays a 3D extruded choropleth of US counties colored and extruded by population.
"""
import json

import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="US County Population 3D",
    page_icon="🗺️",
    layout="wide",
)

st.title("US County Population — 3D Extruded Map")
st.caption("ACS 2024 5-Year Estimates · Total Population (B01003_001E)")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
DATA_PATH = "data/us_counties_population.geojson"
GITHUB_RAW_URL = ""  # Set to raw GitHub URL for cloud deployment


@st.cache_data
def load_geojson():
    with open(DATA_PATH) as f:
        return json.load(f)


geojson = load_geojson()

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Map Controls")

elevation_scale = st.sidebar.slider(
    "Elevation Scale",
    min_value=1000,
    max_value=80000,
    value=20000,
    step=1000,
    help="Multiplier for county extrusion height (based on log₁₀ population)",
)

pitch = st.sidebar.slider(
    "Pitch (tilt)",
    min_value=0,
    max_value=60,
    value=45,
    step=5,
)

opacity = st.sidebar.slider(
    "Opacity",
    min_value=0.1,
    max_value=1.0,
    value=0.85,
    step=0.05,
)

map_styles = {
    "Dark": "dark",
    "Light": "light",
    "Satellite": "satellite",
    "Road": "road",
}
map_style_label = st.sidebar.selectbox("Map Style", list(map_styles.keys()), index=0)
map_style = map_styles[map_style_label]

wireframe = st.sidebar.toggle("Wireframe", value=True)

# ---------------------------------------------------------------------------
# PyDeck layer
# ---------------------------------------------------------------------------
layer = pdk.Layer(
    "GeoJsonLayer",
    data=geojson,
    opacity=opacity,
    stroked=True,
    filled=True,
    extruded=True,
    wireframe=wireframe,
    get_elevation="properties.log_pop",
    elevation_scale=elevation_scale,
    get_fill_color="properties.fill_color",
    get_line_color=[255, 255, 255, 40],
    line_width_min_pixels=0.5,
    pickable=True,
    auto_highlight=True,
    highlight_color=[255, 255, 0, 100],
)

view_state = pdk.ViewState(
    latitude=38.5,
    longitude=-96.0,
    zoom=3.8,
    pitch=pitch,
    bearing=0,
    min_zoom=2,
    max_zoom=15,
)

tooltip = {
    "html": (
        "<div style='font-family: Arial, sans-serif; padding: 6px;'>"
        "<b style='font-size: 14px;'>{properties.county_name}</b><br/>"
        "<span style='color: #aaa; font-size: 11px;'>FIPS: {properties.fips}</span><br/>"
        "<hr style='margin: 4px 0; border-color: #444;'/>"
        "<span style='font-size: 16px; color: #4fc3f7;'>"
        "Population: <b>{properties.population_formatted}</b></span>"
        "</div>"
    ),
    "style": {
        "backgroundColor": "#1a1a2e",
        "color": "white",
        "fontSize": "12px",
        "borderRadius": "8px",
        "border": "1px solid #333",
    },
}

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style=map_style,
    parameters={"depthTest": True},
)

components.html(deck.to_html(), height=700, scrolling=False)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 12px; margin-top: 1rem;'>"
    "Data: US Census Bureau, American Community Survey 2024 5-Year Estimates · "
    "Table B01003 (Total Population) · Counties: Plotly geojson-counties-fips"
    "</div>",
    unsafe_allow_html=True,
)

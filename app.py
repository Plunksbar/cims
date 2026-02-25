import streamlit as st
import pandas as pd
import folium
import json
import os
import polyline
from streamlit_folium import st_folium

# --- CONFIGURATION ---
JSON_FOLDER = "data"

st.set_page_config(layout="wide", page_title="100 Cims Explorer")

import urllib.parse


def get_external_links(row):
    # 1. Google Maps Link (Search by coordinates and name)
    name_encoded = urllib.parse.quote(row['Name'])
    google_url = f"https://www.google.com/maps/search/?api=1&query={row['Lat']},{row['Lon']},{name_encoded}"

    # 2. Wikiloc Link (Creating a bounding box around the peak)
    # Offset of ~0.01 degrees is roughly 1km
    sw_lat, sw_lon = row['Lat'] - 0.01, row['Lon'] - 0.01
    ne_lat, ne_lon = row['Lat'] + 0.01, row['Lon'] + 0.01

    wikiloc_url = (
        f"https://es.wikiloc.com/wikiloc/map.do?"
        f"sw={sw_lat},{sw_lon}&"
        f"ne={ne_lat},{ne_lon}&"
        f"place={name_encoded}&page=1"
    )

    return google_url, wikiloc_url


@st.cache_data
def load_data(folder_path):
    all_data = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                # Safely get route data
                route = data.get("routes", [{}])[0].get("legs", [{}])[0]

                entry = {
                    "Name": data.get("nom"),
                    "Altitude": data.get("altitud"),
                    "Comarca": data.get("comarca", ""),
                    "Ascents": int(data.get("assencions", 0)),
                    "Lat": data.get("latitud"),
                    "Lon": data.get("longitud"),
                    "Essential": data.get("essencial", False),
                    "Duration_Hrs": round(route.get("duration", 0) / 3600, 2),
                    "Distance_KM": round(route.get("distance", 0) / 1000, 2),
                    "geometry": data.get("routes", [{}])[0].get("geometry")
                }
                all_data.append(entry)
    return pd.DataFrame(all_data)


df_raw = load_data(JSON_FOLDER)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Options")

# 1. Text Search
name_search = st.sidebar.text_input("Search by Name")

# 2. Categorical Filters
all_comarcas = sorted(df_raw["Comarca"].unique())
selected_comarcas = st.sidebar.multiselect("Comarca", all_comarcas)

# 3. Numeric Sliders
max_duration = st.sidebar.slider("Max Driving Time (Hours)", 0.0, float(df_raw["Duration_Hrs"].max()),
                                 float(df_raw["Duration_Hrs"].max()))
max_distance = st.sidebar.slider("Max Distance (KM)", 0, int(df_raw["Distance_KM"].max()),
                                 int(df_raw["Distance_KM"].max()))
min_alt = st.sidebar.number_input("Min Altitude (m)", 0, int(df_raw["Altitude"].max()), 0)
min_asc = st.sidebar.number_input("Min Ascensions", 0, int(df_raw["Ascents"].max()), 0)

# 4. Checkbox
essential_only = st.sidebar.checkbox("Essential Peaks Only")

# --- APPLY FILTERS ---
df = df_raw.copy()
if name_search:
    df = df[df['Name'].str.contains(name_search, case=False)]
if selected_comarcas:
    df = df[df['Comarca'].isin(selected_comarcas)]
if essential_only:
    df = df[df['Essential'] == True]

df = df[
    (df["Duration_Hrs"] <= max_duration) &
    (df["Distance_KM"] <= max_distance) &
    (df["Altitude"] >= min_alt) &
    (df["Ascents"] >= min_asc)
    ]

# --- UI LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(f"Results ({len(df)} peaks)")
    selection = st.dataframe(
        df[["Name", "Altitude", "Comarca", "Duration_Hrs", "Distance_KM", "Essential"]],
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        use_container_width=True
    )

    selected_rows = selection.selection.rows

    if selected_rows:
        selected_idx = selected_rows[0]
        row = df.iloc[selected_idx]

        st.markdown(f"### 📍 {row['Name']}")

        g_map, w_loc = get_external_links(row)

        # Create buttons or nice looking links
        l_col1, l_col2 = st.columns(2)
        with l_col1:
            st.link_button("🌐 Open in Google Maps", g_map, use_container_width=True)
        with l_col2:
            st.link_button("🥾 Search on Wikiloc", w_loc, use_container_width=True)

        st.info(f"**Comarca:** {row['Comarca']} | **Altitude:** {row['Altitude']}m")

with col2:
    st.subheader("Map View")

    # Initialize Map
    m = folium.Map(location=[41.7, 1.8], zoom_start=8)

    selected_rows = selection.selection.rows

    if selected_rows:
        # SHOW SPECIFIC ROUTE
        selected_idx = selected_rows[0]
        row = df.iloc[selected_idx]

        folium.Marker(
            [row["Lat"], row["Lon"]],
            popup=row["Name"],
            icon=folium.Icon(color="darkred" if row["Essential"] else "blue")
        ).add_to(m)

        if row["geometry"]:
            path = polyline.decode(row["geometry"])
            folium.PolyLine(path, color="red", weight=5).add_to(m)
            m.fit_bounds(path)
    else:
        # SHOW ALL FILTERED POINTS
        for _, row in df.iterrows():
            color = "orange" if row["Essential"] else "blue"
            folium.CircleMarker(
                location=[row["Lat"], row["Lon"]],
                radius=5,
                popup=f"{row['Name']} ({row['Altitude']}m)",
                color=color,
                fill=True,
                fill_color=color
            ).add_to(m)

        # Fit map to all filtered points if they exist
        if not df.empty:
            m.fit_bounds(df[['Lat', 'Lon']].values.tolist())

    st_folium(m, height=600, use_container_width=True, key="main_map")
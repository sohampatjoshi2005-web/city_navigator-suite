"""
MapQuest Suite -- 4 Google Maps hackathon concepts in one app.
No credit card required anywhere: routing/elevation via OpenRouteService
(free API key, email signup only), geocoding via Nominatim/OpenStreetMap
(no key at all), historical data via Wikipedia (no key).

1. Greenest Route Optimizer     -- real, fully functional
2. Ghost Jam Predictor          -- real route + simulated risk model (labeled)
3. AR Local History (Web Demo)  -- real Wikipedia geosearch, web analogy of AR
4. Offline Emergency Navigator  -- real route compression demo (no live mesh/SMS)

Deploy target: Streamlit Community Cloud.
Locally: pip install -r requirements.txt && streamlit run app.py
Needs ORS_API_KEY as an environment variable / Streamlit secret.
Get a free key at https://openrouteservice.org/dev/#/signup (no card needed).
"""

import os
import json
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import requests
import polyline
import pydeck as pdk
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
WIKI_API = "https://en.wikipedia.org/w/api.php"

NOMINATIM_HEADERS = {"User-Agent": "MapQuestSuite/1.0 (educational demo project)"}

# ORS maneuver 'type' codes that correspond to a stop / yield / signal point.
# 0 Left, 1 Right, 2 Sharp left, 3 Sharp right, 4 Slight left, 5 Slight right,
# 6 Straight (not stop-like), 7 Enter roundabout, 8 Exit roundabout,
# 9 U-turn, 10 Goal (not stop-like), 11 Depart (not stop-like),
# 12 Keep left, 13 Keep right.
STOP_LIKE_MANEUVER_TYPES = {0, 1, 2, 3, 4, 5, 7, 8, 9, 12, 13}


def get_ors_key() -> str:
    try:
        if "ORS_API_KEY" in st.secrets:
            return st.secrets["ORS_API_KEY"]
    except Exception:
        pass
    return os.getenv("ORS_API_KEY", "")


# ============================================================
# Shared helpers
# ============================================================

@dataclass
class RouteResult:
    summary: str
    distance_m: float
    duration_s: float
    duration_in_traffic_s: Optional[float]
    stop_count: int
    polyline_points: List[List[float]]      # [[lat, lng], ...]
    encoded_polyline: str
    elevation_profile: List[float] = field(default_factory=list)
    elevation_gain_m: float = 0.0
    co2_grams: float = 0.0


def geocode(place: str) -> tuple:
    """Free geocoding via Nominatim (OpenStreetMap). No API key needed."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": place, "format": "json", "limit": 1},
        headers=NOMINATIM_HEADERS,
        timeout=15,
    )
    results = resp.json()
    if not results:
        raise RuntimeError(f"Could not geocode '{place}' -- try a more specific place name.")
    return float(results[0]["lat"]), float(results[0]["lon"])


def compute_elevation_gain(profile: List[float]) -> float:
    gain = 0.0
    for prev, curr in zip(profile, profile[1:]):
        if curr - prev > 0:
            gain += curr - prev
    return gain


def fetch_routes(origin: str, destination: str, ors_key: str) -> List[RouteResult]:
    o_lat, o_lng = geocode(origin)
    d_lat, d_lng = geocode(destination)

    body = {
        "coordinates": [[o_lng, o_lat], [d_lng, d_lat]],
        "elevation": True,
        "instructions": True,
        "alternative_routes": {"target_count": 3, "share_factor": 0.6, "weight_factor": 1.4},
    }
    headers = {"Authorization": ors_key, "Content-Type": "application/json"}
    resp = requests.post(ORS_DIRECTIONS_URL, json=body, headers=headers, timeout=20)
    data = resp.json()

    if resp.status_code != 200:
        msg = data.get("error", {}).get("message", str(data))
        raise RuntimeError(f"OpenRouteService error: {msg}")

    features = data.get("features", [])
    if not features:
        raise RuntimeError("No routes returned -- try different origin/destination.")

    results = []
    for i, feature in enumerate(features):
        props = feature["properties"]
        summary = props.get("summary", {})
        distance_m = summary.get("distance", 0.0)
        duration_s = summary.get("duration", 0.0)

        stop_count = 0
        for segment in props.get("segments", []):
            for step in segment.get("steps", []):
                if step.get("type") in STOP_LIKE_MANEUVER_TYPES:
                    stop_count += 1

        coords = feature["geometry"]["coordinates"]  # [[lng, lat, elevation], ...]
        points = [[c[1], c[0]] for c in coords]
        elevation_profile = [c[2] for c in coords if len(c) > 2]

        encoded = polyline.encode([(lat, lng) for lat, lng in points])
        route_summary = f"Route option {i + 1}"

        r = RouteResult(
            summary=route_summary, distance_m=distance_m, duration_s=duration_s,
            duration_in_traffic_s=None,  # not available on ORS free tier
            stop_count=stop_count, polyline_points=points, encoded_polyline=encoded,
            elevation_profile=elevation_profile,
        )
        r.elevation_gain_m = compute_elevation_gain(elevation_profile)
        results.append(r)
    return results


def sample_points(points: List[List[float]], max_samples: int = 100) -> List[List[float]]:
    if len(points) <= max_samples:
        return points
    step = len(points) / max_samples
    return [points[int(i * step)] for i in range(max_samples)]


# ============================================================
# Streamlit page setup
# ============================================================

st.set_page_config(page_title="MapQuest Suite", layout="wide")
st.title("🗺️ MapQuest Suite")
st.caption(
    "Four Google Maps concepts in one app -- rebuilt on free, no-credit-card APIs: "
    "OpenRouteService (routing + elevation) and Nominatim/OpenStreetMap (geocoding)."
)

ORS_KEY = get_ors_key()
if not ORS_KEY:
    st.error(
        "No ORS_API_KEY found. Get a free key (no card needed) at "
        "https://openrouteservice.org/dev/#/signup -- then locally put it in a .env file, "
        "or on Streamlit Community Cloud add it under Settings > Secrets as:\n"
        'ORS_API_KEY = "your_real_key_here"'
    )
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs([
    "🌱 Greenest Route",
    "👻 Ghost Jam Predictor",
    "🕰️ AR Local History (Web Demo)",
    "📡 Offline Navigator (Demo)",
])

# ============================================================
# TAB 1 -- Greenest Route Optimizer
# ============================================================
with tab1:
    st.subheader("Greenest Route Optimizer")
    st.caption(
        "Scores alternative routes by estimated CO2: distance, elevation gain, and stop-like turns. "
        "Note: the free routing API used here doesn't expose live traffic congestion, so that factor is omitted."
    )

    c1, c2 = st.columns(2)
    with c1:
        origin1 = st.text_input("Origin", value="Bhubaneswar, India", key="t1_origin")
    with c2:
        destination1 = st.text_input("Destination", value="Puri, India", key="t1_dest")

    with st.expander("Emission model weights (adjustable assumptions, not official factors)"):
        base_g_per_km = st.slider("Base g CO2 / km", 80, 250, 120, key="t1_base")
        elevation_g_per_m = st.slider("Extra g CO2 / meter climbed", 0.0, 5.0, 1.5, key="t1_elev")
        stop_g_per_stop = st.slider("Extra g CO2 / stop-like turn", 0, 50, 15, key="t1_stop")

    if st.button("Find greenest route", type="primary", key="t1_run"):
        try:
            with st.spinner("Fetching routes and elevation..."):
                routes = fetch_routes(origin1, destination1, ORS_KEY)

            for r in routes:
                distance_km = r.distance_m / 1000.0
                base = distance_km * base_g_per_km
                elev = r.elevation_gain_m * elevation_g_per_m
                stops = r.stop_count * stop_g_per_stop
                r.co2_grams = base + elev + stops

            routes_sorted = sorted(routes, key=lambda r: r.co2_grams)
            greenest = routes_sorted[0]
            st.success(f"Greenest route: **{greenest.summary}** (~{greenest.co2_grams/1000:.2f} kg CO2 estimated)")

            st.dataframe([{
                "Route": r.summary,
                "Distance (km)": round(r.distance_m / 1000, 2),
                "Duration (min)": round(r.duration_s / 60, 1),
                "Elevation gain (m)": round(r.elevation_gain_m, 1),
                "Stop-like turns": r.stop_count,
                "Est. CO2 (kg)": round(r.co2_grams / 1000, 3),
            } for r in routes_sorted], use_container_width=True, hide_index=True)

            layers = []
            colors = [[0, 160, 0, 200], [255, 140, 0, 160], [200, 30, 30, 160], [120, 120, 120, 160]]
            for i, r in enumerate(routes_sorted):
                color = colors[i] if i < len(colors) else [100, 100, 100, 150]
                path = [[lng, lat] for lat, lng in r.polyline_points]
                layers.append(pdk.Layer("PathLayer", data=[{"path": path}], get_path="path",
                                         get_color=color, width_scale=1, width_min_pixels=4))
            mid = greenest.polyline_points[len(greenest.polyline_points) // 2]
            st.pydeck_chart(pdk.Deck(map_style="road",
                                      initial_view_state=pdk.ViewState(latitude=mid[0], longitude=mid[1], zoom=10),
                                      layers=layers))
            st.caption("Green = greenest. Others ranked worst by color order.")
            if greenest.elevation_profile:
                st.line_chart(greenest.elevation_profile)
        except Exception as e:
            st.error(str(e))

# ============================================================
# TAB 2 -- Ghost Jam Predictor
# ============================================================
with tab2:
    st.subheader("Ghost Jam Predictor")
    st.info(
        "⚠️ Demo scope: this uses a **simulated risk model** overlaid on a real route, "
        "not a live historical-traffic dataset. It's built to illustrate the phantom-jam "
        "concept -- slowdowns from human braking behavior, not accidents."
    )

    c1, c2 = st.columns(2)
    with c1:
        origin2 = st.text_input("Origin", value="Bhubaneswar, India", key="t2_origin")
    with c2:
        destination2 = st.text_input("Destination", value="Puri, India", key="t2_dest")

    hour = st.slider("Hour of day (for rush-hour weighting)", 0, 23, 9, key="t2_hour")

    if st.button("Predict ghost jams", type="primary", key="t2_run"):
        try:
            with st.spinner("Fetching real route geometry..."):
                routes = fetch_routes(origin2, destination2, ORS_KEY)
            route = routes[0]
            sampled = sample_points(route.polyline_points, max_samples=60)

            rush_factor = (
                math.exp(-((hour - 8) ** 2) / 8) + math.exp(-((hour - 18) ** 2) / 8)
            )
            rush_factor = 0.3 + rush_factor

            random.seed(42)
            risk_points = []
            for lat, lng in sampled:
                noise = random.uniform(0.2, 1.0)
                risk = noise * rush_factor
                risk_points.append({"lat": lat, "lng": lng, "weight": risk})

            st.success(f"Simulated {len(risk_points)} risk points along the route for hour={hour}:00.")

            layer = pdk.Layer(
                "HeatmapLayer", data=risk_points, get_position=["lng", "lat"],
                get_weight="weight", radiusPixels=40,
            )
            mid = sampled[len(sampled) // 2]
            st.pydeck_chart(pdk.Deck(map_style="road",
                                      initial_view_state=pdk.ViewState(latitude=mid[0], longitude=mid[1], zoom=10),
                                      layers=[layer]))

            st.subheader("Why phantom jams happen (physics demo)")
            st.caption(
                "Classic ring-road simulation: cars following a simple car-following rule "
                "spontaneously form stop-and-go waves with no obstacle at all -- this is the "
                "real, well-documented phenomenon (Sugiyama et al.) the heatmap above is standing in for."
            )
            n_cars = 22
            positions = sorted(random.uniform(0, 100) for _ in range(n_cars))
            speeds = [5.0] * n_cars
            history = []
            for _ in range(120):
                new_positions = []
                for i in range(n_cars):
                    gap = (positions[(i + 1) % n_cars] - positions[i]) % 100
                    target_speed = min(5.0, max(0.0, gap - 2.0))
                    speeds[i] += (target_speed - speeds[i]) * 0.3
                    new_positions.append((positions[i] + speeds[i]) % 100)
                positions = new_positions
                history.append(list(speeds))
            st.line_chart(history)
            st.caption("Each line is one simulated car's speed over time. Waves emerge purely from spacing/braking, no accident needed.")
        except Exception as e:
            st.error(str(e))

# ============================================================
# TAB 3 -- AR Local History (real Wikipedia geosearch, web analogy)
# ============================================================
with tab3:
    st.subheader("AR Local History -- Web Demo")
    st.info(
        "⚠️ True phone-camera AR needs a native app with Google's ARCore Geospatial API. "
        "This is a web analogy: pick a location, see real historical/background info "
        "anchored to those exact coordinates via Wikipedia's geosearch."
    )

    place = st.text_input("Place name or address", value="Konark Sun Temple, India", key="t3_place")
    radius_m = st.slider("Search radius (meters)", 100, 3000, 800, key="t3_radius")

    if st.button("Time travel here", type="primary", key="t3_run"):
        try:
            with st.spinner("Geocoding location..."):
                lat, lng = geocode(place)

            with st.spinner("Searching nearby historical entries..."):
                geo_resp = requests.get(WIKI_API, params={
                    "action": "query", "list": "geosearch",
                    "gscoord": f"{lat}|{lng}", "gsradius": radius_m,
                    "gslimit": 6, "format": "json",
                }, timeout=15).json()
                pages = geo_resp.get("query", {}).get("geosearch", [])

            if not pages:
                st.warning("No nearby Wikipedia entries found -- try a larger radius or a different place.")
            else:
                titles = "|".join(p["title"] for p in pages)
                detail_resp = requests.get(WIKI_API, params={
                    "action": "query", "prop": "extracts|pageimages",
                    "exintro": True, "explaintext": True,
                    "piprop": "thumbnail", "pithumbsize": 400,
                    "titles": titles, "format": "json",
                }, timeout=15).json()
                detail_pages = detail_resp.get("query", {}).get("pages", {})

                st.pydeck_chart(pdk.Deck(
                    map_style="road",
                    initial_view_state=pdk.ViewState(latitude=lat, longitude=lng, zoom=14),
                    layers=[pdk.Layer(
                        "ScatterplotLayer",
                        data=[{"lat": p["lat"], "lng": p["lon"], "name": p["title"]} for p in pages],
                        get_position=["lng", "lat"], get_radius=30,
                        get_fill_color=[200, 30, 30, 200],
                    )],
                ))

                for p in pages:
                    match = next((v for v in detail_pages.values() if v.get("title") == p["title"]), None)
                    if not match:
                        continue
                    cols = st.columns([1, 3])
                    with cols[0]:
                        thumb = match.get("thumbnail", {}).get("source")
                        if thumb:
                            st.image(thumb, width=150)
                    with cols[1]:
                        st.markdown(f"**{match.get('title')}**")
                        extract = match.get("extract", "")
                        st.write(extract[:400] + ("..." if len(extract) > 400 else ""))
                    st.divider()
        except Exception as e:
            st.error(str(e))

# ============================================================
# TAB 4 -- Offline Emergency Navigator (real compression demo)
# ============================================================
with tab4:
    st.subheader("Offline Emergency Navigator -- Compression Demo")
    st.info(
        "⚠️ This demonstrates the *compression concept only* -- shrinking a route down to a "
        "tiny text string. It does not send data over Bluetooth/SMS/mesh; a browser can't "
        "access that hardware. The point is showing how little data a route actually needs."
    )

    c1, c2 = st.columns(2)
    with c1:
        origin4 = st.text_input("Origin", value="Bhubaneswar, India", key="t4_origin")
    with c2:
        destination4 = st.text_input("Destination", value="Puri, India", key="t4_dest")

    if st.button("Compress route", type="primary", key="t4_run"):
        try:
            with st.spinner("Fetching real route..."):
                routes = fetch_routes(origin4, destination4, ORS_KEY)
            route = routes[0]

            raw_json = json.dumps({"points": route.polyline_points})
            raw_size = len(raw_json.encode("utf-8"))

            full_encoded = route.encoded_polyline
            full_size = len(full_encoded.encode("utf-8"))

            reduced_points = sample_points(route.polyline_points, max_samples=25)
            reduced_encoded = polyline.encode([(lat, lng) for lat, lng in reduced_points])
            reduced_size = len(reduced_encoded.encode("utf-8"))

            st.subheader("Payload size comparison")
            st.dataframe([
                {"Format": "Raw JSON (full points)", "Size (bytes)": raw_size},
                {"Format": "Full-resolution encoded polyline", "Size (bytes)": full_size},
                {"Format": "Reduced + re-encoded polyline (25 pts)", "Size (bytes)": reduced_size},
            ], use_container_width=True, hide_index=True)

            sms_segments = math.ceil(reduced_size / 140)
            st.success(
                f"Compressed route fits in **{reduced_size} bytes** -- "
                f"roughly {sms_segments} SMS segment(s), well within Bluetooth low-energy packet limits."
            )

            st.code(reduced_encoded, language="text")

            st.subheader("Offline decode test (no internet used here)")
            decoded_back = polyline.decode(reduced_encoded)
            st.write(f"Decoded {len(decoded_back)} waypoints locally from the string above.")
            path = [[lng, lat] for lat, lng in decoded_back]
            mid = decoded_back[len(decoded_back) // 2]
            st.pydeck_chart(pdk.Deck(
                map_style="road",
                initial_view_state=pdk.ViewState(latitude=mid[0], longitude=mid[1], zoom=10),
                layers=[pdk.Layer("PathLayer", data=[{"path": path}], get_path="path",
                                   get_color=[0, 100, 200, 200], width_min_pixels=4)],
            ))
            st.caption("This reconstructed path came purely from decoding the short string above -- no API call needed for this step.")
        except Exception as e:
            st.error(str(e))

# 🗺️ MapQuest Suite

A five-in-one route-intelligence app, built entirely on free, no-credit-card APIs. Each tab explores a different underserved mapping problem — environmental cost, phantom traffic jams, hyperlocal history, offline resilience, and sensory/safety-aware routing — using real routing/geocoding data wherever possible, and clearly-labeled simulated models where real data isn't freely available.

---

## Overview

| Tab | What it does | Data source |
|---|---|---|
| 🌱 **Greenest Route** | Multi-route comparison scored by an estimated CO2 model, with hazard/community-note avoidance, weather advisories, and a multi-modal cost comparison | OpenRouteService (ORS) |
| 👻 **Ghost Jam Predictor** | Simulated phantom-traffic-jam risk overlay on a real route, plus a car-following simulation showing how braking waves emerge from spacing alone | ORS (real route) + local simulation |
| 🕰️ **AR Local History** | "Web AR" — real Wikipedia entries anchored to real coordinates near a place | Nominatim/Geoapify + Wikipedia API |
| 📡 **Offline Navigator** | Demonstrates compressing a route into an SMS-sized encoded polyline, decodable with no network call | ORS + `polyline` encoding |
| 🧘 **Sensory & Safety Router** | Simulated sensory-load and night-safety heatmap overlays with 0–100 scores | ORS (real route) + local simulation |

> **Honesty by design:** any tab whose scoring is simulated (Ghost Jam, Sensory & Safety) says so explicitly in the UI. Only Greenest Route, AR Local History, and Offline Navigator use live, real data end-to-end.

---

## Feature details

### 🌱 Greenest Route
- **Travel modes:** Driving, Cycling, Walking
- **One-tap context presets** — "In a rush," "Tired / conserve energy," "Exploring" — auto-fill mode + avoid options + CO2 weights in a single click (removes decision fatigue from manually tuning every slider)
- **CO2 model** — editable grams/km, grams/m elevation climbed, grams/stop-like turn; not official emission factors, just a transparent estimate
- **Community Notes** (see below) can carve out avoid-zones for the router
- **🌦️ Weather-aware advisory** — pulls current temperature/wind/precipitation at the route midpoint (Open-Meteo, free & keyless) and flags exposed-route risk (heat, cold, wind, rain)
- **💰 Multi-modal cost comparison** — fetches driving/cycling/walking routes for the same trip and compares time + an editable cost-per-km estimate side by side (not live fares — no free API exposes those — but transparent and adjustable)

### 👻 Ghost Jam Predictor
- Fetches a real route, then overlays a simulated risk heatmap weighted by a rush-hour curve (peaks ~8am/6pm)
- A small car-following simulation (22 cars, simple follow-the-leader physics) shows how stop-and-go "phantom" waves emerge purely from spacing and braking — no accident or bottleneck required

### 🕰️ AR Local History
- Geocodes a place, then queries Wikipedia's geosearch API for nearby articles within a chosen radius
- Displays thumbnails + intro extracts, plotted on a real map — the "AR" is conceptual (anchoring info to coordinates), not phone-camera AR

### 📡 Offline Navigator
- Fetches a real route, then shows three size comparisons: raw JSON points, full-resolution encoded polyline, and a reduced 25-point re-encoded polyline
- Estimates how many 140-byte SMS segments the compressed route would need, and decodes it back locally to prove no network call is needed to reconstruct it

### 🧘 Sensory & Safety Router
- **Sensory-load score (0–100):** a deterministic, seeded pseudo-random weighting per route-sample-point standing in for real ambient-noise/crowd-density data (no free API exposes that at this granularity)
- **Night-safety score (0–100):** driven by a time-of-day "darkness factor" (risk peaks in the small hours, lowest at midday) — a genuinely simulated heuristic, not real lighting/crime data
- Toggle between the two heatmap overlays on the same map

### 📌 Community Notes
A crowdsourced local-knowledge layer across four categories:
- 🚧 **Hazard/Closure** — the only category that actually reroutes traffic around it (feeds into the same avoid-polygon mechanism as before)
- 💡 **Broken lighting**
- ♿ **Accessibility issue**
- 🎒 **Local tip**

Informational categories show as color-coded map pins but don't affect routing. **Session-only** in this build — not persisted between restarts or shared across users (would need a real backend/database to go further).

---

## Architecture

```
Streamlit (UI) 
   │
   ├── OpenRouteService (ORS) ── driving / cycling / walking / wheelchair routing, elevation, instructions
   ├── Geocoding chain:
   │      1. Geoapify (if GEOAPIFY_API_KEY set) — primary, keyed, 3000 free req/day
   │      2. Nominatim — self-throttled to ≥1.1s between calls
   │      3. Photon (Komoot) — free, keyless fallback mirror
   ├── Wikipedia API ── geosearch + page extracts/thumbnails
   ├── Open-Meteo ── free, keyless current-weather lookup
   └── pydeck ── all map/heatmap rendering
```

**Resilience features:**
- `st.cache_data` caching on geocoding, Wikipedia lookups, and weather (1hr / 1hr / 10min TTLs) — avoids redundant calls to rate-limited free APIs
- Retry-with-backoff session for transient 5xx errors on ORS/Wikipedia
- Nominatim-specific self-throttling + automatic fallback chain (Geoapify → Nominatim → Photon) so a 429 from one provider never surfaces as a raw crash
- Each ORS-dependent tab independently checks for a valid `ORS_API_KEY` — a missing key no longer blocks the whole app (AR Local History never needed it)

---

## Setup

### Required
1. **OpenRouteService key** (free, no card) — https://openrouteservice.org/dev/#/signup
2. Add it as `ORS_API_KEY` in:
   - **Streamlit Cloud:** app → ⋮ menu → Settings → Secrets
   - **Local:** a `.env` file in the project root

### Recommended (for reliable geocoding)
3. **Geoapify key** (free, no card, 3,000 req/day) — https://www.geoapify.com/get-started-with-maps-api
4. Add it as `GEOAPIFY_API_KEY` the same way as above

### Run locally
```bash
pip install streamlit requests polyline pydeck python-dotenv
streamlit run app.py
```

### Deploy on Streamlit Community Cloud
1. Push `app.py` to a GitHub repo
2. Connect the repo at share.streamlit.io
3. Add secrets (`ORS_API_KEY`, optionally `GEOAPIFY_API_KEY`) in app Settings
4. Reboot the app after any code or secrets change

---

## Known limitations

- **Community Notes are session-only** — no shared backend, so they vanish on app restart and aren't visible across different users' sessions
- **Cost estimates are assumptions, not live fares** — no free API exposes real-time rideshare/transit pricing
- **Sensory-load and night-safety scores are simulated heuristics**, not real noise-sensor or crowdsourced-safety data — clearly labeled as such in the UI
- **Nominatim's free endpoint can still rate-limit** shared cloud IPs even with throttling; the Geoapify key removes this dependency almost entirely

---

## Changelog (this build)

- Added one-tap contextual routing presets
- Added weather-aware route advisory (Open-Meteo)
- Added multi-modal cost comparison table
- Expanded hazard zones into a 4-category Community Notes layer
- Added new Sensory & Safety Router tab with dual heatmap overlays
- Added Geoapify as primary geocoder with Nominatim/Photon fallback chain
- Added self-throttling for Nominatim + broad exception handling to eliminate raw connection-error crashes
- Added `st.cache_data` caching across geocoding, Wikipedia, and weather calls
- Decoupled ORS-key requirement so AR Local History works without it

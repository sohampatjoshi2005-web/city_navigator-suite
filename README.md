---
title: MapQuest Suite
emoji: 🗺️
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.32.0"
app_file: app.py
pinned: false
---

# MapQuest Suite

Four Google Maps hackathon concepts in one Streamlit app:

1. **Greenest Route Optimizer** -- real Directions + Elevation API based CO2 scoring
2. **Ghost Jam Predictor** -- real route geometry + simulated phantom-traffic risk model
3. **AR Local History (Web Demo)** -- real Wikipedia geosearch anchored to real coordinates
4. **Offline Emergency Navigator (Demo)** -- real route compression size comparison

## Setup

Add `GOOGLE_MAPS_API_KEY` as a Space secret (Settings > Repository secrets) with
Directions, Elevation, and Geocoding APIs enabled on that key.

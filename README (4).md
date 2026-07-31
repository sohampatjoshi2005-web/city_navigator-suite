# 🗺️ MapQuest Suite

A Streamlit app with eight tabs, each targeting one specific gap in mainstream mapping apps rather than trying to be another general-purpose map.

## Tabs

| Tab | Gap addressed |
|---|---|
| 🌱 Greenest Route | Reroutes around live weather hazards and community-reported closures, and states the exact km/min cost of that choice instead of a black-box "recommended" route. Includes a hands-free voice assistant. |
| 👻 Ghost Jam Predictor | Models *why* phantom traffic jams emerge from following/braking behavior — predictive, not reactive to historical data. |
| 🕰️ AR Local History | Surfaces place-anchored historical/cultural context that keyword search misses, without needing a phone-camera AR view. Voice assistant included. |
| 📡 Offline Navigator | Compresses a route small enough to transmit over SMS/Bluetooth for low-connectivity or emergency scenarios. |
| 🧘 Sensory & Safety Router | Scores routes for sensory load and night-safety instead of a one-size-fits-all ETA. Includes live GPS road-crossing alerts (multilingual) and an optional Google Maps–powered local-errands search (grocery, stationery, pharmacy) for short local walks. |
| 🚨 ADAS Collision Watch (Video + VLM) | Samples frames from an uploaded driving photo/video, runs local CV object detection, and can send frames to Claude vision for a hazard read. Informational only — it does not control a vehicle or watch a live feed. |
| ♿ Accessibility Explorer | Crowdsources a structured accessibility profile per place (ramp steepness, restroom layout, elevators, door width, tactile/auditory accommodations) aggregated across multiple reports, instead of a single step-free-entrance toggle. |
| 🧾 Listing Trust Audit | Cross-checks a business's own website (schema.org structured data) against an independent OpenStreetMap record, scores each field, and can draft a polite verification message. |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. API keys

All keys are optional except **OpenRouteService**, which the core routing features need. Set keys via a local `.env` file, `.streamlit/secrets.toml`, or your host's secrets manager (e.g. Streamlit Community Cloud → Settings → Secrets).

| Key | Required? | Used for | Get one at |
|---|---|---|---|
| `ORS_API_KEY` | **Yes**, for routing | Turn-by-turn directions, route calculation | https://openrouteservice.org/dev/#/signup |
| `ANTHROPIC_API_KEY` | Optional | AI navigation narration, translation, VLM hazard reads, outreach drafting | https://console.anthropic.com/settings/keys |
| `GEOAPIFY_API_KEY` | Optional | Extra geocoding fallback | https://www.geoapify.com/ |
| `GROQ_API_KEY` | Optional | Voice assistant (speech-to-text) | https://console.groq.com/keys |
| `GOOGLE_MAPS_API_KEY` | Optional | Local-errand search & fallback walking directions in the Sensory & Safety Router tab | https://console.cloud.google.com/google/maps-apis |

`.env` example:

```
ORS_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GEOAPIFY_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
GOOGLE_MAPS_API_KEY=your_key_here
```

> **Note on Google Maps:** unlike every other key above (all free tiers, no card required), Google Maps Platform requires a Google Cloud Billing account on file even to use its monthly free credit. It's entirely optional — the app works without it.

### 3. Run it

**Locally:**
```bash
streamlit run APP.py
```

**Google Colab:** Colab can't serve Streamlit directly, so it needs to be tunneled (e.g. via `localtunnel` or `ngrok`) from a launcher notebook.

**Streamlit Community Cloud:** point the deploy at `APP.py`, add your keys under Settings → Secrets, and it deploys on push.

## Notes on scope

A few features are deliberately conservative about what they claim to do:

- The road-crossing alert (Sensory & Safety Router tab) uses phone GPS against OpenStreetMap-tagged crossing points. It's a reminder to look both ways — it does not detect actual vehicles and is not a certified safety device.
- The ADAS tab analyzes uploaded photos/video only. It does not control a vehicle, read a live camera feed, or perform lane-change/speed-control actions.

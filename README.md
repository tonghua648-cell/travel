# AMap AI Travel Stay Assistant

MVP for recommending where to stay when a Wuhan trip has multiple destinations. This version uses AMap Web Service APIs instead of local Wuhan road and POI data.

## Run

```powershell
cd D:\CodexWorkspace\travel-assistant
$env:AMAP_KEY="your_amap_web_service_key"
python backend\server.py
```

Open `http://127.0.0.1:8000`.

You can also put the key in `backend\amap_key.txt` and then run `python backend\server.py`.

Agent mode works without an OpenAI key by falling back to a local rule parser. To enable model-based parsing, set `OPENAI_API_KEY` or put the key in `backend\openai_key.txt`.

Xiaomi MiMo is supported through its OpenAI-compatible Chat Completions API. Set `MIMO_API_KEY` or put the key in `backend\mimo_key.txt`. The default model is `mimo-v2-pro`; override it with `MIMO_MODEL` or `backend\mimo_model.txt` if needed.

Doubao is also supported through Volcengine Ark's OpenAI-compatible chat API. Set `ARK_API_KEY` or put the key in `backend\doubao_key.txt`. The default model is `doubao-seed-1-6-250615`; override it with `ARK_MODEL`, `DOUBAO_MODEL`, or `backend\doubao_model.txt` if your Ark account uses a specific endpoint/model id.

Hotel rating and reference price are read from AMap POI extended fields when available. You can also provide your own hotel market data by creating `backend\hotel_data.json`, or by setting `HOTEL_DATA_FILE` to another JSON file. See `backend\hotel_data.example.json`.

Recommended plans can be saved from the Results panel. The server writes saved snapshots to `backend\saved_plans.json` and returns a short `?plan=<id>` share link that restores destinations, settings, recommendations, and any generated itinerary.

## Features

- Search destinations through AMap POI text search.
- Search nearby hotel candidates through AMap POI around search.
- Batch score hotels by driving or transit travel time to all destinations.
- Rank by average travel time, worst travel time, and a lightweight hotel quality estimate.
- Use real hotel rating/reference price when AMap or local hotel data provides it, with heuristic quality as fallback.
- Compare up to three recommended hotels side by side, including travel time, rating, reference price, and value score.
- Save and restore shareable recommendation snapshots.
- Agent-style natural language planning that parses trip needs, recommends a hotel, and generates an itinerary.

## Notes

- No Python packages are required.
- `AMAP_KEY` or `backend\amap_key.txt` must contain a Web Service API key with POI search and direction planning access.
- `OPENAI_API_KEY` or `backend\openai_key.txt` is optional; without it, Agent mode uses local rule parsing.
- Price is intentionally not included in v1 scoring.

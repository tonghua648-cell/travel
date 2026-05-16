from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
import json
import math
import os
import secrets
import re
import time
import urllib.error
import urllib.request


BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

AMAP_BASE = "https://restapi.amap.com"
DEFAULT_CITY = os.environ.get("AMAP_CITY", "武汉")
DEFAULT_HOTEL_LIMIT = int(os.environ.get("HOTEL_LIMIT", "15"))
DEFAULT_ROUTE_MODE = os.environ.get("ROUTE_MODE", "driving")
KEY_FILE = Path(__file__).resolve().parent / "amap_key.txt"
OPENAI_KEY_FILE = Path(__file__).resolve().parent / "openai_key.txt"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
DOUBAO_KEY_FILE = Path(__file__).resolve().parent / "doubao_key.txt"
DOUBAO_MODEL_FILE = Path(__file__).resolve().parent / "doubao_model.txt"
DOUBAO_BASE_URL = os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
MIMO_KEY_FILE = Path(__file__).resolve().parent / "mimo_key.txt"
MIMO_MODEL_FILE = Path(__file__).resolve().parent / "mimo_model.txt"
MIMO_BASE_URL = os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
HOTEL_DATA_FILE = Path(os.environ.get("HOTEL_DATA_FILE", Path(__file__).resolve().parent / "hotel_data.json"))
SAVED_PLANS_FILE = Path(os.environ.get("SAVED_PLANS_FILE", Path(__file__).resolve().parent / "saved_plans.json"))
FEEDBACK_FILE = Path(os.environ.get("FEEDBACK_FILE", Path(__file__).resolve().parent / "feedback.json"))


def json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def hotel_data_status():
    content = ""
    exists = HOTEL_DATA_FILE.exists()
    count = 0
    if exists:
        try:
            content = HOTEL_DATA_FILE.read_text(encoding="utf-8")
            parsed = json.loads(content) if content.strip() else {}
            records = parsed.get("hotels") if isinstance(parsed, dict) else parsed
            count = len(records) if isinstance(records, list) else 0
        except (OSError, json.JSONDecodeError):
            count = 0
    return {
        "exists": exists,
        "path": str(HOTEL_DATA_FILE),
        "count": count,
        "content": content,
        "example": {
            "hotels": [
                {
                    "name": "悦然居酒店(武汉昙华林店)",
                    "rating": 4.6,
                    "price": 428,
                    "priceUnit": "元",
                    "source": "自有酒店数据",
                }
            ]
        },
    }


def save_hotel_data(payload):
    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, str):
        raise ValueError("Missing hotel data JSON content.")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("酒店数据不是合法 JSON：%s" % exc.msg)
    records = parsed.get("hotels") if isinstance(parsed, dict) else parsed
    if not isinstance(records, list):
        raise ValueError("酒店数据需要是数组，或包含 hotels 数组。")
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError("第 %d 条酒店数据必须是对象。" % index)
        if not record.get("id") and not record.get("name"):
            raise ValueError("第 %d 条酒店数据至少需要 id 或 name。" % index)
        if parse_float(record.get("rating") or record.get("score")) is None and parse_float(record.get("price") or record.get("cost")) is None:
            raise ValueError("第 %d 条酒店数据至少需要 rating/score 或 price/cost。" % index)
    HOTEL_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
    HOTEL_DATA_FILE.write_text(formatted + "\n", encoding="utf-8")
    return hotel_data_status()


def read_saved_plans():
    if not SAVED_PLANS_FILE.exists():
        return {"plans": {}}
    try:
        data = json.loads(SAVED_PLANS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"plans": {}}
    if not isinstance(data, dict):
        return {"plans": {}}
    plans = data.get("plans")
    if not isinstance(plans, dict):
        data["plans"] = {}
    return data


def save_plan(payload):
    if not isinstance(payload, dict):
        raise ValueError("Missing plan payload.")
    data = read_saved_plans()
    plans = data["plans"]
    for _ in range(5):
        plan_id = secrets.token_urlsafe(6)
        if plan_id not in plans:
            break
    else:
        plan_id = secrets.token_urlsafe(9)
    saved_at = int(time.time())
    plan = {
        "id": plan_id,
        "savedAt": saved_at,
        "title": payload.get("title") or "旅行方案",
        "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else payload,
    }
    plans[plan_id] = plan
    SAVED_PLANS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAVED_PLANS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"id": plan_id, "url": "/?plan=%s" % plan_id, "savedAt": saved_at}


def get_saved_plan(plan_id):
    if not plan_id:
        raise ValueError("Missing plan id.")
    plan = read_saved_plans()["plans"].get(plan_id)
    if not plan:
        return None
    return plan


def read_feedback():
    if not FEEDBACK_FILE.exists():
        return {"items": []}
    try:
        data = json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": []}
    if not isinstance(data, dict):
        return {"items": []}
    items = data.get("items")
    if not isinstance(items, list):
        data["items"] = []
    return data


def save_feedback(payload):
    if not isinstance(payload, dict):
        raise ValueError("Missing feedback payload.")
    try:
        rating = int(payload.get("rating"))
    except (TypeError, ValueError):
        raise ValueError("请选择 1-5 分满意度。")
    if rating < 1 or rating > 5:
        raise ValueError("满意度评分必须在 1-5 之间。")
    comment = str(payload.get("comment") or "").strip()
    if not comment:
        raise ValueError("请填写反馈内容。")
    if len(comment) > 2000:
        raise ValueError("反馈内容不能超过 2000 字。")
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    data = read_feedback()
    feedback_id = secrets.token_urlsafe(6)
    saved_at = int(time.time())
    item = {
        "id": feedback_id,
        "savedAt": saved_at,
        "rating": rating,
        "comment": comment,
        "context": context,
    }
    data["items"].append(item)
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "id": feedback_id, "savedAt": saved_at}


def get_amap_key():
    env_key = os.environ.get("AMAP_KEY") or os.environ.get("GAODE_KEY")
    if env_key:
        return env_key.strip().lstrip("\ufeff")
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    return ""


def get_openai_key():
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key.strip().lstrip("\ufeff")
    if OPENAI_KEY_FILE.exists():
        return OPENAI_KEY_FILE.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    return ""


def get_doubao_key():
    env_key = os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY")
    if env_key:
        return env_key.strip().lstrip("\ufeff")
    if DOUBAO_KEY_FILE.exists():
        return DOUBAO_KEY_FILE.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    return ""


def get_doubao_model():
    env_model = os.environ.get("ARK_MODEL") or os.environ.get("DOUBAO_MODEL")
    if env_model:
        return env_model.strip().lstrip("\ufeff")
    if DOUBAO_MODEL_FILE.exists():
        return DOUBAO_MODEL_FILE.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    return os.environ.get("DOUBAO_DEFAULT_MODEL", "doubao-seed-1-6-250615")


def get_mimo_key():
    env_key = os.environ.get("MIMO_API_KEY") or os.environ.get("XIAOMI_MIMO_API_KEY")
    if env_key:
        return env_key.strip().lstrip("\ufeff")
    if MIMO_KEY_FILE.exists():
        return MIMO_KEY_FILE.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    return ""


def get_mimo_model():
    env_model = os.environ.get("MIMO_MODEL") or os.environ.get("XIAOMI_MIMO_MODEL")
    if env_model:
        return env_model.strip().lstrip("\ufeff")
    if MIMO_MODEL_FILE.exists():
        return MIMO_MODEL_FILE.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    return os.environ.get("MIMO_DEFAULT_MODEL", "mimo-v2-pro")


def require_key():
    key = get_amap_key()
    if not key:
        raise ValueError("缺少高德 Web 服务 Key。请先设置环境变量 AMAP_KEY，或把 Key 写入 backend/amap_key.txt，然后重启服务。")
    return key


def amap_get(path, params):
    key = require_key()
    query = dict(params)
    query["key"] = key
    query["output"] = "json"
    url = "%s%s?%s" % (AMAP_BASE, path, urlencode(query))
    req = urllib.request.Request(url, headers={"User-Agent": "travel-assistant/0.1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError("高德 API HTTP 错误：%s" % exc.code)
        except urllib.error.URLError as exc:
            raise RuntimeError("无法连接高德 API：%s" % exc.reason)
        if str(data.get("status")) == "1":
            return data
        message = data.get("info") or data.get("infocode") or "未知错误"
        if message == "CUQPS_HAS_EXCEEDED_THE_LIMIT" and attempt < 2:
            time.sleep(0.8 * (attempt + 1))
            continue
        break
    if message == "USERKEY_PLAT_NOMATCH":
        message = "当前 Key 的平台类型不匹配。请使用高德开放平台的 Web服务 API Key，不是 JS API、Android 或 iOS Key。"
    elif message == "INVALID_USER_KEY":
        message = "当前 Key 无效。请确认 Key 是否复制完整，且已在高德开放平台启用。"
    elif message == "CUQPS_HAS_EXCEEDED_THE_LIMIT":
        message = "当前 Key 调用过快，触发高德 QPS 限制。请稍后再试，或降低候选酒店数。"
    raise RuntimeError("高德 API 返回错误：%s" % message)


def parse_location(value):
    if not value or "," not in value:
        return None
    lon, lat = value.split(",", 1)
    return float(lon), float(lat)


def parse_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"[]", "{}", "None", "null", "暂无"}:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def location_string(lon, lat):
    return "%.6f,%.6f" % (float(lon), float(lat))


def haversine_km(a, b):
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(h))


def parse_clock(value, default="09:00"):
    text = str(value or default).strip()
    try:
        hour, minute = text.split(":", 1)
        hour = int(hour)
        minute = int(minute)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour * 60 + minute
    except (TypeError, ValueError):
        pass
    hour, minute = default.split(":", 1)
    return int(hour) * 60 + int(minute)


def format_clock(total_minutes):
    total = int(round(total_minutes)) % (24 * 60)
    return "%02d:%02d" % (total // 60, total % 60)


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def centroid(points):
    return (
        sum(point["lon"] for point in points) / len(points),
        sum(point["lat"] for point in points) / len(points),
    )


class AmapClient:
    def status(self):
        return {
            "provider": "amap",
            "city": DEFAULT_CITY,
            "hasKey": bool(get_amap_key()),
            "hasMimoKey": bool(get_mimo_key()),
            "mimoModel": get_mimo_model(),
            "hasAgentKey": bool(get_openai_key()),
            "hasDoubaoKey": bool(get_doubao_key()),
            "doubaoModel": get_doubao_model(),
            "hotelLimit": DEFAULT_HOTEL_LIMIT,
            "routeMode": DEFAULT_ROUTE_MODE,
        }

    def agent(self, payload):
        message = (payload.get("message") or "").strip()
        if not message:
            raise ValueError("请输入你的旅行需求。")
        parsed = self._parse_agent_request(message)
        city = parsed.get("city") or payload.get("city") or ""
        destination_keywords = parsed.get("destinationKeywords") or []
        destinations = []
        for keyword in destination_keywords[:6]:
            results = self.search_pois(keyword, city=city, limit=5)
            if results:
                poi = results[0]
                destinations.append(
                    {
                        "name": poi["name"],
                        "lon": poi["lon"],
                        "lat": poi["lat"],
                        "weight": 1,
                        "sourceKeyword": keyword,
                    }
                )
                time.sleep(0.15)
        if not destinations:
            return {
                "needsConfirmation": True,
                "message": "我还没有识别出明确目的地。请补充想去的景点或区域，例如“黄鹤楼、武汉大学、江汉路”。",
                "parsed": parsed,
            }
        stay_minutes = float(parsed.get("stayMinutes") or 60)
        trip_hours = parsed.get("tripHours")
        if trip_hours and destinations:
            available = max(30.0, float(trip_hours) * 60 - 90)
            stay_minutes = max(30.0, min(120.0, available / len(destinations)))
        recommend_payload = {
            "city": city,
            "destinations": destinations,
            "routeMode": self._normalize_route_mode(parsed.get("routeMode")),
            "preference": parsed.get("preference") or "balanced",
            "weights": parsed.get("weights") or {"avgTime": 55, "maxTime": 30, "comfort": 15},
            "travelPreferences": parsed.get("travelPreferences") or {},
            "hotelLimit": int(parsed.get("hotelLimit") or 8),
        }
        recommendation = self.recommend(recommend_payload)
        hotels = recommendation.get("poiRecommendations") or []
        if not hotels:
            return {
                "needsConfirmation": True,
                "message": "已识别目的地，但没有找到可达酒店。建议减少目的地或降低候选限制后再试。",
                "parsed": parsed,
                "destinations": destinations,
            }
        best_hotel = hotels[0]
        itinerary_payload = {
            "city": city,
            "origin": {"name": best_hotel["name"], "lon": best_hotel["lon"], "lat": best_hotel["lat"]},
            "destinations": destinations,
            "routeMode": "transit" if parsed.get("routeMode") == "transit" else "driving",
            "travelPreferences": parsed.get("travelPreferences") or {},
            "startTime": parsed.get("startTime") or "09:00",
            "stayMinutes": stay_minutes,
            "returnToHotel": bool(parsed.get("returnToHotel", True)),
        }
        itinerary = self.itinerary(itinerary_payload)
        return {
            "needsConfirmation": False,
            "message": self._agent_summary(parsed, best_hotel, itinerary),
            "parsed": parsed,
            "destinations": destinations,
            "recommendation": recommendation,
            "itinerary": itinerary,
        }

    def _parse_agent_request(self, message):
        parsed = self._mimo_parse_agent_request(message)
        if parsed:
            return self._normalize_agent_parse(parsed, message, parser="mimo")
        parsed = self._doubao_parse_agent_request(message)
        if parsed:
            return self._normalize_agent_parse(parsed, message, parser="doubao")
        parsed = self._openai_parse_agent_request(message)
        if parsed:
            return self._normalize_agent_parse(parsed, message, parser="openai")
        return self._rule_parse_agent_request(message)

    def _agent_parse_schema(self):
        return {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "destinationKeywords": {"type": "array", "items": {"type": "string"}},
                "tripHours": {"type": ["number", "null"]},
                "travelers": {"type": "array", "items": {"type": "string"}},
                "routeMode": {"type": "string", "enum": ["driving", "transit"]},
                "preference": {"type": "string", "enum": ["balanced", "time", "comfort"]},
                "weights": {
                    "type": "object",
                    "properties": {
                        "avgTime": {"type": "number"},
                        "maxTime": {"type": "number"},
                        "comfort": {"type": "number"},
                    },
                    "required": ["avgTime", "maxTime", "comfort"],
                    "additionalProperties": False,
                },
                "travelPreferences": {
                    "type": "object",
                    "properties": {
                        "lessWalking": {"type": "boolean"},
                        "lessTransfers": {"type": "boolean"},
                        "familyFriendly": {"type": "boolean"},
                        "elderFriendly": {"type": "boolean"},
                    },
                    "required": ["lessWalking", "lessTransfers", "familyFriendly", "elderFriendly"],
                    "additionalProperties": False,
                },
                "stayMinutes": {"type": ["number", "null"]},
                "startTime": {"type": "string"},
                "returnToHotel": {"type": "boolean"},
                "hotelLimit": {"type": "number"},
            },
            "required": ["city", "destinationKeywords", "tripHours", "travelers", "routeMode", "preference", "weights", "travelPreferences", "stayMinutes", "startTime", "returnToHotel", "hotelLimit"],
            "additionalProperties": False,
        }

    def _agent_parse_prompt(self, message):
        return (
            "你是城市旅行助手。把用户中文旅行需求解析为 JSON。"
            "目的地只输出适合高德 POI 搜索的短关键词。"
            "如果有老人小孩或希望快速便利，优先 routeMode=driving，并提高 avgTime/maxTime 权重。"
            "如果明确说地铁公交，routeMode=transit。"
            "识别少走路、少换乘、亲子友好、老人友好到 travelPreferences。"
            "只能输出 JSON，不要输出 Markdown。"
            "用户需求：%s" % message
        )

    def _mimo_parse_agent_request(self, message):
        key = get_mimo_key()
        model = get_mimo_model()
        if not key or not model:
            return None
        schema = self._agent_parse_schema()
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你只输出符合要求的 JSON。"},
                {"role": "user", "content": self._agent_parse_prompt(message)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "travel_request",
                    "schema": schema,
                    "strict": True,
                },
            },
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            self._chat_completions_url(MIMO_BASE_URL),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "api-key": key,
                "Content-Type": "application/json",
                "User-Agent": "travel-assistant/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        message_data = choices[0].get("message") or {}
        text = message_data.get("content")
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except ValueError:
                return None

    def _chat_completions_url(self, base_url):
        normalized = str(base_url or "").rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return normalized + "/chat/completions"

    def _doubao_parse_agent_request(self, message):
        key = get_doubao_key()
        model = get_doubao_model()
        if not key or not model:
            return None
        schema = self._agent_parse_schema()
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你只输出符合要求的 JSON。"},
                {"role": "user", "content": self._agent_parse_prompt(message)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "travel_request",
                    "schema": schema,
                    "strict": True,
                },
            },
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            DOUBAO_BASE_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer %s" % key,
                "Content-Type": "application/json",
                "User-Agent": "travel-assistant/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        message_data = choices[0].get("message") or {}
        text = message_data.get("content")
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except ValueError:
                return None

    def _openai_parse_agent_request(self, message):
        key = get_openai_key()
        if not key:
            return None
        schema = self._agent_parse_schema()
        body = {
            "model": OPENAI_MODEL,
            "input": self._agent_parse_prompt(message),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "travel_request",
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer %s" % key,
                "Content-Type": "application/json",
                "User-Agent": "travel-assistant/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None
        text = data.get("output_text")
        if not text:
            for item in data.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"} and content.get("text"):
                        text = content["text"]
                        break
                if text:
                    break
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            return None

    def _rule_parse_agent_request(self, message):
        city = DEFAULT_CITY
        for candidate in ["武汉", "长沙", "南京", "成都", "重庆", "上海", "北京", "广州", "深圳", "杭州", "西安"]:
            if candidate in message:
                city = candidate
                break
        known_places = [
            "黄鹤楼", "武汉大学", "江汉路", "东湖", "湖北省博物馆", "武汉站", "汉口站", "武昌站",
            "光谷", "昙华林", "粮道街", "户部巷", "古德寺", "归元寺", "晴川阁", "楚河汉街",
            "华中农业大学", "华中科技大学", "武汉理工大学", "中南财经政法大学", "湖北大学",
            "武汉天地", "江滩", "汉口江滩", "汉阳造", "古琴台", "武汉动物园", "武汉植物园",
        ]
        destinations = [place for place in known_places if place in message]
        for place in self._extract_destination_keywords(message):
            if place not in destinations:
                destinations.append(place)
        trip_hours = None
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:个)?小时", message)
        day_match = re.search(r"(\d+(?:\.\d+)?)\s*天", message)
        if hour_match:
            trip_hours = float(hour_match.group(1))
        elif day_match:
            trip_hours = float(day_match.group(1)) * 8
        start_time = "09:00"
        time_match = re.search(r"(\d{1,2})[:：](\d{2})", message)
        if time_match:
            start_time = "%02d:%02d" % (int(time_match.group(1)), int(time_match.group(2)))
        has_elder = any(word in message for word in ["老人", "父母", "长辈", "老年"])
        has_child = any(word in message for word in ["小孩", "孩子", "儿童", "带娃", "亲子"])
        has_elder_or_child = has_elder or has_child
        wants_less_walking = any(word in message for word in ["少走路", "少步行", "不想走", "步行少"])
        wants_less_transfers = any(word in message for word in ["少换乘", "少倒车", "换乘少", "不换乘"])
        wants_fast = any(word in message for word in ["快", "便利", "方便", "省时间", "交通便利"]) or wants_less_walking
        wants_transit = any(word in message for word in ["公交", "地铁", "公共交通"])
        wants_comfort = any(word in message for word in ["舒服", "舒适", "高端", "品质", "安静"])
        if wants_transit:
            route_mode = "transit"
        elif has_elder_or_child or wants_fast:
            route_mode = "driving"
        else:
            route_mode = "driving"
        weights = {"avgTime": 55, "maxTime": 30, "comfort": 15}
        preference = "time" if wants_fast or has_elder_or_child else "balanced"
        if wants_comfort:
            weights = {"avgTime": 40, "maxTime": 20, "comfort": 40}
            preference = "comfort"
        if has_elder_or_child:
            weights = {"avgTime": 50, "maxTime": 40, "comfort": 10}
        return {
            "city": city,
            "destinationKeywords": destinations[:6],
            "tripHours": trip_hours,
            "travelers": ["老人小孩"] if has_elder_or_child else [],
            "routeMode": route_mode,
            "preference": preference,
            "weights": weights,
            "travelPreferences": {
                "lessWalking": wants_less_walking or has_elder_or_child,
                "lessTransfers": wants_less_transfers or has_elder_or_child,
                "familyFriendly": has_child,
                "elderFriendly": has_elder,
            },
            "stayMinutes": None,
            "startTime": start_time,
            "returnToHotel": True,
            "hotelLimit": 8,
            "parser": "rule",
        }

    def _extract_destination_keywords(self, message):
        cleaned = re.sub(r"\d+(?:\.\d+)?\s*(?:个)?(?:小时|天|分钟)", " ", message)
        cleaned = re.sub(r"\d{1,2}[:：]\d{2}", " ", cleaned)
        stop_words = [
            "帮我", "推荐", "酒店", "住宿", "路线", "行程", "方案", "规划", "安排", "生成",
            "带老人", "带小孩", "带孩子", "老人", "小孩", "孩子", "父母", "亲子",
            "希望", "要求", "需要", "最好", "交通", "便利", "快速", "少走路", "少步行",
            "少换乘", "公交", "地铁", "驾车", "开车", "出发", "返回",
        ]
        spans = []
        patterns = [
            r"(?:想去|要去|准备去|打算去|去|到|玩|游览|逛|打卡|看|做|走|安排|规划)([^。；;，,]+?)(?:的?路线|路线|行程|方案|附近|周边|，|,|。|；|;|$)",
            r"([^。；;，,]+?)(?:的?路线|路线|行程)",
        ]
        for pattern in patterns:
            spans.extend(re.findall(pattern, cleaned))

        candidates = []
        for span in spans:
            for part in re.split(r"(?:、|，|,|和|与|及|以及|再|然后|\s+)", span):
                candidate = self._clean_destination_candidate(part, stop_words)
                if candidate:
                    candidates.append(candidate)

        suffix_pattern = r"[\u4e00-\u9fa5A-Za-z0-9]{2,24}(?:大学|学院|中学|小学|站|机场|码头|路|街|大道|广场|中心|公园|动物园|植物园|博物馆|美术馆|科技馆|体育馆|剧院|楼|寺|湖|谷|巷|阁|桥)"
        try:
            suffix_matches = re.findall(suffix_pattern, cleaned)
        except re.error:
            suffix_matches = []
        for match in suffix_matches:
            candidate = self._clean_destination_candidate(match, stop_words)
            if candidate:
                candidates.append(candidate)

        unique = []
        for candidate in candidates:
            if any(candidate != item and item in candidate for item in unique):
                continue
            unique = [item for item in unique if not (item != candidate and candidate in item)]
            if candidate not in unique:
                unique.append(candidate)
        return unique[:8]

    def _clean_destination_candidate(self, text, stop_words):
        candidate = re.sub(r"[“”\"'‘’（）()]", "", str(text or "")).strip()
        candidate = re.sub(r"^(?:我|我们|想|要|准备|打算|从|在|到|去|玩|游览|逛|打卡|看|做|走|安排|规划)+", "", candidate).strip()
        candidate = re.sub(r"(?:的?路线|的路|路线|行程|方案|附近|周边)$", "", candidate).strip()
        for word in stop_words:
            candidate = candidate.replace(word, " ")
        candidate = re.sub(r"\s+", "", candidate)
        if not (2 <= len(candidate) <= 24):
            return ""
        if candidate in {"武汉", "城市", "目的地", "景点", "地方", "时间"}:
            return ""
        return candidate

    def _normalize_agent_parse(self, parsed, message, parser="openai"):
        fallback = self._rule_parse_agent_request(message)
        result = dict(fallback)
        for key, value in parsed.items():
            if value not in (None, "", []):
                result[key] = value
        parsed_destinations = [str(item).strip() for item in parsed.get("destinationKeywords", []) if str(item).strip()] if isinstance(parsed.get("destinationKeywords"), list) else []
        fallback_destinations = [str(item).strip() for item in fallback.get("destinationKeywords", []) if str(item).strip()]
        result["destinationKeywords"] = parsed_destinations or fallback_destinations
        result["routeMode"] = self._normalize_route_mode(result.get("routeMode") or fallback["routeMode"])
        if any(word in message for word in ["公交", "地铁", "公共交通", "只算公交"]):
            result["routeMode"] = "transit"
        elif any(word in message for word in ["驾车", "开车", "打车", "只算驾车"]):
            result["routeMode"] = "driving"
        result["preference"] = result.get("preference") if result.get("preference") in {"balanced", "time", "comfort"} else fallback["preference"]
        parsed_preferences = self._normalize_travel_preferences(result.get("travelPreferences"))
        fallback_preferences = self._normalize_travel_preferences(fallback.get("travelPreferences"))
        result["travelPreferences"] = {
            key: bool(parsed_preferences.get(key) or fallback_preferences.get(key))
            for key in ["lessWalking", "lessTransfers", "familyFriendly", "elderFriendly"]
        }
        result["parser"] = parser
        return result

    def _agent_summary(self, parsed, hotel, itinerary):
        traveler_note = "，已考虑老人小孩同行" if parsed.get("travelers") else ""
        return (
            "已根据你的需求生成方案%s：推荐住在「%s」，平均通勤约 %.1f 分钟。"
            "游览从 %s 开始，预计 %s 结束，总通勤约 %.1f 分钟。"
        ) % (
            traveler_note,
            hotel["name"],
            hotel["avgMinutes"],
            itinerary["startTime"],
            itinerary["endTime"],
            itinerary["totalTravelMinutes"],
        )

    def search_pois(self, keyword, city=None, limit=20):
        if not keyword.strip():
            return []
        query = {
            "keywords": keyword.strip(),
            "offset": min(limit, 25),
            "page": 1,
            "extensions": "base",
        }
        if city:
            query["city"] = city
            query["citylimit"] = "true"
        data = amap_get(
            "/v3/place/text",
            query,
        )
        return [self._normalize_poi(poi) for poi in data.get("pois", []) if poi.get("location")]

    def reverse_geocode_city(self, lon, lat):
        data = amap_get(
            "/v3/geocode/regeo",
            {
                "location": location_string(lon, lat),
                "radius": 1000,
                "extensions": "base",
            },
        )
        component = data.get("regeocode", {}).get("addressComponent", {})
        city = component.get("city")
        if isinstance(city, list):
            city = ""
        return city or component.get("province") or ""

    def infer_city_from_points(self, points, fallback=DEFAULT_CITY):
        for point in points or []:
            try:
                city = self.reverse_geocode_city(float(point["lon"]), float(point["lat"]))
            except (KeyError, TypeError, ValueError, RuntimeError):
                city = ""
            if city:
                return city
        return fallback

    def search_hotels(self, destinations, city=None, limit=DEFAULT_HOTEL_LIMIT):
        center = centroid(destinations)
        max_km = max(haversine_km(center, (dest["lon"], dest["lat"])) for dest in destinations)
        radius = int(min(50000, max(5000, max_km * 1000 + 5000)))
        query = {
            "keywords": "酒店",
            "types": "100000",
            "location": location_string(center[0], center[1]),
            "radius": radius,
            "sortrule": "weight",
            "offset": min(max(limit * 2, 20), 25),
            "page": 1,
            "extensions": "all",
        }
        if city:
            query["city"] = city
        data = amap_get(
            "/v3/place/around",
            query,
        )
        hotels = [self._normalize_poi(poi) for poi in data.get("pois", []) if poi.get("location")]
        if not hotels:
            query = {
                "keywords": "酒店",
                "types": "100000",
                "offset": min(max(limit * 2, 20), 25),
                "page": 1,
                "extensions": "all",
            }
            if city:
                query["city"] = city
                query["citylimit"] = "true"
            data = amap_get(
                "/v3/place/text",
                query,
            )
            hotels = [self._normalize_poi(poi) for poi in data.get("pois", []) if poi.get("location")]
        self._merge_hotel_market_data(hotels)
        unique = []
        seen = set()
        for hotel in hotels:
            key = hotel["id"] or (hotel["name"], round(hotel["lon"], 6), round(hotel["lat"], 6))
            if key in seen:
                continue
            seen.add(key)
            unique.append(hotel)
            if len(unique) >= limit:
                break
        return unique

    def driving_route(self, origin, destination):
        data = amap_get(
            "/v3/direction/driving",
            {
                "origin": location_string(origin["lon"], origin["lat"]),
                "destination": location_string(destination["lon"], destination["lat"]),
                "strategy": "10",
                "extensions": "base",
            },
        )
        paths = data.get("route", {}).get("paths") or []
        if not paths:
            return None
        path = paths[0]
        return {
            "mode": "driving",
            "minutes": round(float(path.get("duration", 0)) / 60, 1),
            "kilometers": round(float(path.get("distance", 0)) / 1000, 2),
        }

    def driving_route_detail(self, origin, destination):
        data = amap_get(
            "/v3/direction/driving",
            {
                "origin": location_string(origin["lon"], origin["lat"]),
                "destination": location_string(destination["lon"], destination["lat"]),
                "strategy": "10",
                "extensions": "base",
            },
        )
        paths = data.get("route", {}).get("paths") or []
        if not paths:
            return None
        path = paths[0]
        polyline = []
        for step in path.get("steps", []) or []:
            self._append_polyline_points(polyline, step.get("polyline"))
        if not polyline:
            polyline = [
                {"lon": float(origin["lon"]), "lat": float(origin["lat"])},
                {"lon": float(destination["lon"]), "lat": float(destination["lat"])},
            ]
        return {
            "mode": "driving",
            "minutes": round(float(path.get("duration", 0)) / 60, 1),
            "kilometers": round(float(path.get("distance", 0)) / 1000, 2),
            "polyline": polyline,
        }

    def transit_route(self, origin, destination, city=DEFAULT_CITY, strategy="0"):
        data = amap_get(
            "/v3/direction/transit/integrated",
            {
                "origin": location_string(origin["lon"], origin["lat"]),
                "destination": location_string(destination["lon"], destination["lat"]),
                "city": city,
                "cityd": city,
                "strategy": strategy,
                "extensions": "base",
            },
        )
        transits = data.get("route", {}).get("transits") or []
        usable = [item for item in transits if str(item.get("duration", "")).strip()]
        if not usable:
            return None
        item = min(usable, key=lambda x: float(x.get("duration", 9999999)))
        segments = item.get("segments") if isinstance(item.get("segments"), list) else []
        bus_segments = 0
        polyline = []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            walking = segment.get("walking") if isinstance(segment.get("walking"), dict) else None
            for step in (walking or {}).get("steps", []) or []:
                self._append_polyline_points(polyline, step.get("polyline"))
            bus = segment.get("bus") if isinstance(segment, dict) else None
            buslines = bus.get("buslines") if isinstance(bus, dict) else None
            if buslines:
                bus_segments += 1
                for busline in buslines:
                    self._append_polyline_points(polyline, busline.get("polyline"))
            railway = segment.get("railway") if isinstance(segment.get("railway"), dict) else None
            self._append_polyline_points(polyline, (railway or {}).get("polyline"))
        if not polyline:
            polyline = [
                {"lon": float(origin["lon"]), "lat": float(origin["lat"])},
                {"lon": float(destination["lon"]), "lat": float(destination["lat"])},
            ]
        transfers = max(0, bus_segments - 1)
        return {
            "mode": "transit",
            "minutes": round(float(item.get("duration", 0)) / 60, 1),
            "kilometers": round(float(item.get("distance", 0)) / 1000, 2),
            "walkingKilometers": round(float(item.get("walking_distance", 0)) / 1000, 2),
            "transfers": transfers,
            "polyline": polyline,
        }

    def _append_polyline_points(self, polyline, encoded):
        for pair in str(encoded or "").split(";"):
            point = parse_location(pair)
            if point:
                polyline.append({"lon": point[0], "lat": point[1]})

    def distance_batch(self, origins, destination, route_type):
        if not origins:
            return []
        route_type_value = "1" if route_type == "driving" else "2"
        data = amap_get(
            "/v3/distance",
            {
                "origins": "|".join(location_string(origin["lon"], origin["lat"]) for origin in origins),
                "destination": location_string(destination["lon"], destination["lat"]),
                "type": route_type_value,
            },
        )
        results = [None] * len(origins)
        for item in data.get("results", []):
            try:
                index = int(item.get("origin_id", "1")) - 1
                if 0 <= index < len(results):
                    results[index] = {
                        "mode": route_type,
                        "minutes": round(float(item.get("duration", 0)) / 60, 1),
                        "kilometers": round(float(item.get("distance", 0)) / 1000, 2),
                    }
            except (TypeError, ValueError):
                continue
        return results

    def recommend(self, payload):
        city = payload.get("city") or ""
        destinations = payload.get("destinations") or []
        if not destinations:
            raise ValueError("请至少添加一个目的地。")
        normalized_destinations = []
        for index, dest in enumerate(destinations):
            normalized_destinations.append(
                {
                    "name": dest.get("name") or "目的地 %d" % (index + 1),
                    "lon": float(dest["lon"]),
                    "lat": float(dest["lat"]),
                    "weight": max(0.1, float(dest.get("weight") or 1)),
                }
            )
        if not city:
            city = self.infer_city_from_points(normalized_destinations, fallback=DEFAULT_CITY)
        limit = int(payload.get("hotelLimit") or DEFAULT_HOTEL_LIMIT)
        route_mode = self._normalize_route_mode(payload.get("routeMode") or payload.get("mode") or DEFAULT_ROUTE_MODE)
        preference = payload.get("preference") or "balanced"
        weights = self._score_weights(payload.get("weights"), preference)
        travel_preferences = self._normalize_travel_preferences(payload.get("travelPreferences"))
        transit_strategy = self._transit_strategy(travel_preferences)
        detailed_transit = route_mode == "transit" and any(travel_preferences.values())
        hotels = payload.get("hotels") or self.search_hotels(normalized_destinations, city=city, limit=limit)
        route_cache = {"driving": [], "transit": []}
        if route_mode == "driving":
            for destination in normalized_destinations:
                route_cache["driving"].append(self.distance_batch(hotels[:limit], destination, "driving"))
                time.sleep(0.25)
        if route_mode == "transit":
            for destination in normalized_destinations:
                if detailed_transit:
                    routes = []
                    for hotel in hotels[:limit]:
                        try:
                            routes.append(self.transit_route(hotel, destination, city=city, strategy=transit_strategy))
                        except RuntimeError:
                            routes.append(None)
                        time.sleep(0.12)
                    route_cache["transit"].append(routes)
                else:
                    try:
                        route_cache["transit"].append(self.distance_batch(hotels[:limit], destination, "transit"))
                    except RuntimeError:
                        route_cache["transit"].append([None] * min(len(hotels), limit))
                    time.sleep(0.35)

        price_values = [parse_float(hotel.get("price")) for hotel in hotels[:limit]]
        price_values = [value for value in price_values if value is not None and value > 0]
        min_price = min(price_values) if price_values else None
        max_price = max(price_values) if price_values else None
        scored = []
        for hotel_index, hotel in enumerate(hotels[:limit]):
            route_details = []
            driving_values = []
            transit_values = []
            walking_values = []
            transfer_values = []
            weighted_minutes = 0.0
            total_weight = 0.0
            max_minutes = 0.0
            avg_km_values = []
            reachable = True
            for destination in normalized_destinations:
                detail = {
                    "destinationName": destination["name"],
                    "destinationLon": destination["lon"],
                    "destinationLat": destination["lat"],
                }
                options = []
                if route_mode == "driving":
                    driving = route_cache["driving"][len(route_details)][hotel_index] if route_cache["driving"] else None
                    if driving:
                        detail["driving"] = driving
                        options.append(driving)
                        driving_values.append(driving["minutes"])
                        avg_km_values.append(driving["kilometers"])
                if route_mode == "transit":
                    transit = route_cache["transit"][len(route_details)][hotel_index] if route_cache["transit"] else None
                    if transit is None and route_mode == "transit":
                        transit = self.transit_route(hotel, destination, city=city)
                    if transit:
                        detail["transit"] = transit
                        options.append(transit)
                        transit_values.append(transit["minutes"])
                        avg_km_values.append(transit["kilometers"])
                if not options:
                    reachable = False
                    break
                chosen = min(options, key=lambda item: item["minutes"])
                detail["bestMode"] = chosen["mode"]
                detail["bestMinutes"] = chosen["minutes"]
                detail["bestKilometers"] = chosen["kilometers"]
                if chosen.get("walkingKilometers") is not None:
                    detail["bestWalkingKilometers"] = chosen["walkingKilometers"]
                    walking_values.append(chosen["walkingKilometers"])
                if chosen.get("transfers") is not None:
                    detail["bestTransfers"] = chosen["transfers"]
                    transfer_values.append(chosen["transfers"])
                weighted_minutes += chosen["minutes"] * destination["weight"]
                total_weight += destination["weight"]
                max_minutes = max(max_minutes, chosen["minutes"])
                route_details.append(detail)
            if not reachable:
                continue
            avg_minutes = weighted_minutes / max(total_weight, 0.001)
            avg_km = sum(avg_km_values) / max(len(avg_km_values), 1)
            hotel_quality = self._hotel_quality_score(hotel)
            value_score, price_level = self._value_score(hotel, min_price, max_price)
            preference_fit = self._preference_fit_score(
                travel_preferences,
                route_details,
                walking_values,
                transfer_values,
                route_mode,
            )
            score, score_breakdown = self._score(
                avg_minutes,
                max_minutes,
                hotel_quality,
                preference,
                weights,
                value_score=value_score,
                has_price=parse_float(hotel.get("price")) is not None,
                preference_fit=preference_fit,
                has_travel_preferences=any(travel_preferences.values()),
            )
            insights = self._insights(hotel, avg_minutes, max_minutes, hotel_quality, route_mode, route_details, weights, value_score, travel_preferences, preference_fit)
            scored.append(
                {
                    "id": hotel["id"],
                    "kind": "poi",
                    "name": hotel["name"],
                    "score": score,
                    "avgMinutes": round(avg_minutes, 1),
                    "maxMinutes": round(max_minutes, 1),
                    "avgKilometers": round(avg_km, 2),
                    "comfortScore": hotel_quality,
                    "rating": hotel.get("rating"),
                    "price": hotel.get("price"),
                    "priceUnit": hotel.get("priceUnit") or "元",
                    "marketDataSource": hotel.get("marketDataSource") or "估算",
                    "valueScore": value_score,
                    "priceLevel": price_level,
                    "scoreBreakdown": score_breakdown,
                    "drivingAvgMinutes": round(sum(driving_values) / len(driving_values), 1) if driving_values else None,
                    "transitAvgMinutes": round(sum(transit_values) / len(transit_values), 1) if transit_values else None,
                    "walkingAvgKilometers": round(sum(walking_values) / len(walking_values), 2) if walking_values else None,
                    "transferAvgCount": round(sum(transfer_values) / len(transfer_values), 1) if transfer_values else None,
                    "preferenceFitScore": preference_fit,
                    "travelPreferences": travel_preferences,
                    "details": route_details,
                    "lon": hotel["lon"],
                    "lat": hotel["lat"],
                    "type": hotel.get("type", ""),
                    "address": hotel.get("address", ""),
                    "tel": hotel.get("tel", ""),
                    "explanation": self._explain(avg_minutes, max_minutes, hotel_quality, route_mode, hotel),
                    "insights": insights,
                    "scoreWeights": weights,
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        if scored:
            avg_score_minutes = sum(item["avgMinutes"] for item in scored) / len(scored)
            for item in scored:
                delta = item["avgMinutes"] - avg_score_minutes
                if abs(delta) < 1:
                    item["insights"]["comparison"] = "与本次候选酒店的平均通勤时间基本持平。"
                elif delta < 0:
                    item["insights"]["comparison"] = "比本次候选酒店平均通勤时间少约 %.1f 分钟。" % abs(delta)
                else:
                    item["insights"]["comparison"] = "比本次候选酒店平均通勤时间多约 %.1f 分钟，适合更看重酒店条件时选择。" % delta
        return {
            "poiRecommendations": scored,
            "gridRecommendations": [],
            "meta": {
                "provider": "amap",
                "city": city,
                "routeMode": route_mode,
                "travelPreferences": travel_preferences,
                "hotelCandidates": len(hotels),
                "destinations": len(normalized_destinations),
            },
        }

    def itinerary(self, payload):
        city = payload.get("city") or ""
        origin = payload.get("origin") or {}
        destinations = payload.get("destinations") or []
        if not origin or "lon" not in origin or "lat" not in origin:
            raise ValueError("Missing route origin.")
        if not destinations:
            raise ValueError("Missing destinations.")
        if not city:
            city = self.infer_city_from_points([origin] + destinations, fallback=DEFAULT_CITY)
        route_mode = self._normalize_route_mode(payload.get("routeMode") or "driving")
        travel_preferences = self._normalize_travel_preferences(payload.get("travelPreferences"))
        transit_strategy = self._transit_strategy(travel_preferences)
        stay_minutes = max(0.0, float(payload.get("stayMinutes") or 60))
        return_to_hotel = bool(payload.get("returnToHotel", True))
        clock_minutes = parse_clock(payload.get("startTime"), "09:00")
        remaining = []
        for index, dest in enumerate(destinations):
            remaining.append(
                {
                    "name": dest.get("name") or "Stop %d" % (index + 1),
                    "lon": float(dest["lon"]),
                    "lat": float(dest["lat"]),
                    "weight": max(0.1, float(dest.get("weight") or 1)),
                }
            )
        current = {
            "name": origin.get("name") or "Hotel",
            "lon": float(origin["lon"]),
            "lat": float(origin["lat"]),
        }
        hotel_origin = dict(current)
        ordered = []
        segments = []
        timeline_stops = []
        total_minutes = 0.0
        total_kilometers = 0.0
        total_travel_minutes = 0.0
        while remaining:
            candidates = []
            for destination in remaining:
                if route_mode == "transit":
                    route = self.transit_route(current, destination, city=city, strategy=transit_strategy)
                else:
                    route = self.driving_route(current, destination)
                if route:
                    candidates.append((route["minutes"] / destination["weight"], destination, route))
                    time.sleep(0.15)
            if not candidates:
                raise RuntimeError("No reachable next stop.")
            _, next_stop, route = min(candidates, key=lambda item: item[0])
            detailed_route = route
            if route_mode == "driving":
                detailed_route = self.driving_route_detail(current, next_stop) or route
            segment = {
                "from": {"name": current["name"], "lon": current["lon"], "lat": current["lat"]},
                "to": {"name": next_stop["name"], "lon": next_stop["lon"], "lat": next_stop["lat"]},
                "mode": detailed_route["mode"],
                "minutes": detailed_route["minutes"],
                "kilometers": detailed_route["kilometers"],
                "departAt": format_clock(clock_minutes),
                "arriveAt": format_clock(clock_minutes + detailed_route["minutes"]),
                "polyline": detailed_route.get("polyline")
                or [
                    {"lon": current["lon"], "lat": current["lat"]},
                    {"lon": next_stop["lon"], "lat": next_stop["lat"]},
                ],
            }
            segments.append(segment)
            arrive_at = clock_minutes + segment["minutes"]
            leave_at = arrive_at + stay_minutes
            next_stop["arriveAt"] = format_clock(arrive_at)
            next_stop["leaveAt"] = format_clock(leave_at)
            next_stop["stayMinutes"] = round(stay_minutes, 1)
            timeline_stops.append(dict(next_stop))
            ordered.append(next_stop)
            total_travel_minutes += segment["minutes"]
            total_kilometers += segment["kilometers"]
            remaining = [item for item in remaining if item is not next_stop]
            current = next_stop
            clock_minutes = leave_at
            time.sleep(0.2)
        if return_to_hotel:
            if route_mode == "transit":
                return_route = self.transit_route(current, hotel_origin, city=city, strategy=transit_strategy)
            else:
                return_route = self.driving_route_detail(current, hotel_origin) or self.driving_route(current, hotel_origin)
            if return_route:
                segment = {
                    "from": {"name": current["name"], "lon": current["lon"], "lat": current["lat"]},
                    "to": {"name": hotel_origin["name"], "lon": hotel_origin["lon"], "lat": hotel_origin["lat"]},
                    "mode": return_route["mode"],
                    "minutes": return_route["minutes"],
                    "kilometers": return_route["kilometers"],
                    "departAt": format_clock(clock_minutes),
                    "arriveAt": format_clock(clock_minutes + return_route["minutes"]),
                    "polyline": return_route.get("polyline")
                    or [
                        {"lon": current["lon"], "lat": current["lat"]},
                        {"lon": hotel_origin["lon"], "lat": hotel_origin["lat"]},
                    ],
                    "isReturn": True,
                }
                segments.append(segment)
                total_travel_minutes += segment["minutes"]
                total_kilometers += segment["kilometers"]
                clock_minutes += segment["minutes"]
                time.sleep(0.2)
        total_stay_minutes = stay_minutes * len(ordered)
        total_minutes = total_travel_minutes + total_stay_minutes
        return {
            "origin": origin,
            "routeMode": route_mode,
            "orderedStops": ordered,
            "timelineStops": timeline_stops,
            "segments": segments,
            "totalMinutes": round(total_minutes, 1),
            "totalTravelMinutes": round(total_travel_minutes, 1),
            "totalStayMinutes": round(total_stay_minutes, 1),
            "totalKilometers": round(total_kilometers, 2),
            "startTime": format_clock(parse_clock(payload.get("startTime"), "09:00")),
            "endTime": format_clock(clock_minutes),
            "returnToHotel": return_to_hotel,
            "travelPreferences": travel_preferences,
            "stayMinutes": round(stay_minutes, 1),
            "summary": "从 %s 出发，游览 %d 个目的地，预计 %s 结束。" % (
                origin.get("name") or "hotel",
                len(ordered),
                format_clock(clock_minutes),
            ),
        }

    def _normalize_poi(self, poi):
        lon, lat = parse_location(poi.get("location"))
        biz_ext = poi.get("biz_ext") if isinstance(poi.get("biz_ext"), dict) else {}
        rating = parse_float(biz_ext.get("rating") or poi.get("rating"))
        price = parse_float(
            biz_ext.get("cost")
            or biz_ext.get("price")
            or poi.get("cost")
            or poi.get("price")
        )
        market_data_source = "高德POI扩展信息" if rating is not None or price is not None else ""
        return {
            "id": poi.get("id") or "",
            "name": poi.get("name") or "未命名地点",
            "type": poi.get("type") or "",
            "address": poi.get("address") if isinstance(poi.get("address"), str) else "",
            "tel": poi.get("tel") if isinstance(poi.get("tel"), str) else "",
            "lon": lon,
            "lat": lat,
            "rating": rating,
            "price": price,
            "priceUnit": "元",
            "marketDataSource": market_data_source,
        }

    def _hotel_quality_score(self, hotel):
        rating = parse_float(hotel.get("rating"))
        if rating is not None:
            return round(max(0.0, min(100.0, rating / 5.0 * 100.0)), 1)
        text = "%s %s" % (hotel.get("name", ""), hotel.get("type", ""))
        score = 55.0
        if "五星" in text or "豪华" in text or "国际" in text:
            score += 20
        if "四星" in text or "精品" in text or "公寓" in text:
            score += 12
        if "快捷" in text or "经济" in text or "旅馆" in text or "招待所" in text:
            score -= 8
        if hotel.get("tel"):
            score += 4
        if hotel.get("address"):
            score += 4
        return round(max(0.0, min(100.0, score)), 1)

    def _merge_hotel_market_data(self, hotels):
        if not HOTEL_DATA_FILE.exists():
            return
        try:
            records = json.loads(HOTEL_DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(records, dict):
            records = records.get("hotels") or records.get("items") or []
        if not isinstance(records, list):
            return
        by_id = {}
        by_name = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            if record.get("id"):
                by_id[str(record["id"])] = record
            if record.get("name"):
                by_name[str(record["name"]).strip()] = record
        for hotel in hotels:
            record = by_id.get(str(hotel.get("id", ""))) or by_name.get(str(hotel.get("name", "")).strip())
            if not record:
                continue
            rating = parse_float(record.get("rating") or record.get("score"))
            price = parse_float(record.get("price") or record.get("cost"))
            if rating is not None:
                hotel["rating"] = rating
            if price is not None:
                hotel["price"] = price
            hotel["priceUnit"] = record.get("priceUnit") or hotel.get("priceUnit") or "元"
            hotel["marketDataSource"] = record.get("source") or "本地酒店数据"

    def _score_weights(self, weights, preference):
        presets = {
            "balanced": {"avgTime": 50.0, "maxTime": 30.0, "comfort": 20.0},
            "time": {"avgTime": 65.0, "maxTime": 25.0, "comfort": 10.0},
            "comfort": {"avgTime": 35.0, "maxTime": 20.0, "comfort": 45.0},
        }
        selected = dict(presets.get(preference, presets["balanced"]))
        if isinstance(weights, dict):
            for key in ["avgTime", "maxTime", "comfort"]:
                try:
                    selected[key] = max(0.0, float(weights.get(key, selected[key])))
                except (TypeError, ValueError):
                    pass
        total = sum(selected.values()) or 1.0
        return {key: round(value / total, 4) for key, value in selected.items()}

    def _normalize_travel_preferences(self, preferences):
        preferences = preferences if isinstance(preferences, dict) else {}
        return {
            "lessWalking": bool(preferences.get("lessWalking")),
            "lessTransfers": bool(preferences.get("lessTransfers")),
            "familyFriendly": bool(preferences.get("familyFriendly")),
            "elderFriendly": bool(preferences.get("elderFriendly")),
        }

    def _normalize_route_mode(self, route_mode):
        return "transit" if route_mode == "transit" else "driving"

    def _transit_strategy(self, preferences):
        if preferences.get("lessWalking") or preferences.get("elderFriendly") or preferences.get("familyFriendly"):
            return "3"
        if preferences.get("lessTransfers"):
            return "2"
        return "0"

    def _preference_fit_score(self, preferences, details, walking_values, transfer_values, route_mode):
        if not any(preferences.values()):
            return None
        score = 100.0
        if preferences.get("lessWalking") or preferences.get("elderFriendly") or preferences.get("familyFriendly"):
            if walking_values:
                avg_walking = sum(walking_values) / len(walking_values)
                score -= min(35.0, avg_walking * 18.0)
            elif route_mode == "transit":
                score -= 12.0
        if preferences.get("lessTransfers") or preferences.get("elderFriendly") or preferences.get("familyFriendly"):
            if transfer_values:
                avg_transfers = sum(transfer_values) / len(transfer_values)
                score -= min(28.0, avg_transfers * 10.0)
            elif route_mode == "transit":
                score -= 8.0
        if (preferences.get("elderFriendly") or preferences.get("familyFriendly")) and route_mode == "transit":
            long_transit_count = len([item for item in details if item.get("bestMinutes", 0) > 40])
            score -= min(18.0, long_transit_count * 6.0)
        if route_mode == "driving" and (preferences.get("elderFriendly") or preferences.get("familyFriendly")):
            score += 4.0
        return round(clamp(score), 1)

    def _value_score(self, hotel, min_price, max_price):
        price = parse_float(hotel.get("price"))
        if price is None or price <= 0:
            return None, "价格缺失"
        if min_price is None or max_price is None or max_price <= min_price:
            return 70.0, "参考价"
        normalized = (price - min_price) / (max_price - min_price)
        value_score = clamp(100.0 - normalized * 60.0)
        if normalized <= 0.33:
            price_level = "较低"
        elif normalized <= 0.66:
            price_level = "中等"
        else:
            price_level = "较高"
        return round(value_score, 1), price_level

    def _score(self, avg_minutes, max_minutes, quality, preference, weights=None, value_score=None, has_price=False, preference_fit=None, has_travel_preferences=False):
        weights = weights or self._score_weights(None, preference)
        time_component = clamp(100.0 - avg_minutes * 1.35)
        max_component = clamp(100.0 - max_minutes * 1.05)
        raw = (
            time_component * weights["avgTime"]
            + max_component * weights["maxTime"]
            + quality * weights["comfort"]
        )
        value_component = value_score if value_score is not None else None
        value_weight = 0.0
        if has_price and value_component is not None:
            value_weight = 0.04 if preference == "comfort" else 0.08
            raw = raw * (1.0 - value_weight) + value_component * value_weight
        preference_weight = 0.10 if has_travel_preferences and preference_fit is not None else 0.0
        if preference_weight:
            raw = raw * (1.0 - preference_weight) + preference_fit * preference_weight
        final = round(clamp(raw), 1)
        return final, {
            "avgTime": round(time_component, 1),
            "maxTime": round(max_component, 1),
            "comfort": round(quality, 1),
            "value": round(value_component, 1) if value_component is not None else None,
            "valueWeight": round(value_weight, 2),
            "preferenceFit": round(preference_fit, 1) if preference_fit is not None else None,
            "preferenceWeight": round(preference_weight, 2),
            "final": final,
        }

    def _explain(self, avg_minutes, max_minutes, quality, route_mode, hotel=None):
        mode_text = {"driving": "驾车", "transit": "公交"}.get(route_mode, route_mode)
        hotel = hotel or {}
        if hotel.get("rating") is not None:
            quality_text = "酒店评分 %.1f/5，折算舒适性 %.1f 分" % (hotel["rating"], quality)
        else:
            quality_text = "酒店基础舒适性估计 %.1f 分" % quality
        return "%s平均约 %.1f 分钟，最远目的地约 %.1f 分钟，%s。" % (
            mode_text,
            avg_minutes,
            max_minutes,
            quality_text,
        )

    def _insights(self, hotel, avg_minutes, max_minutes, quality, route_mode, details, weights, value_score=None, travel_preferences=None, preference_fit=None):
        travel_preferences = travel_preferences or {}
        mode_text = {"driving": "驾车", "transit": "公交"}.get(route_mode, route_mode)
        reasons = []
        warnings = []
        if avg_minutes <= 20:
            reasons.append("整体通勤压力较低，多个目的地之间的平均到达时间较短。")
        elif avg_minutes <= 35:
            reasons.append("整体通勤时间处于可接受范围，适合行程较松的城市游。")
        else:
            warnings.append("平均通勤时间偏长，建议减少目的地或提高候选酒店数重新计算。")
        if max_minutes <= 30:
            reasons.append("最远目的地也没有明显拖累，住宿位置比较均衡。")
        else:
            farthest = max(details, key=lambda item: item.get("bestMinutes", 0))
            warnings.append("%s 相对较远，预计约 %.1f 分钟。" % (farthest.get("destinationName", "某个目的地"), farthest.get("bestMinutes", max_minutes)))
        if hotel.get("rating") is not None and quality >= 75:
            reasons.append("酒店公开评分较高，舒适性权重使用真实评分折算。")
        elif quality >= 75:
            reasons.append("酒店名称、类型和基础信息显示其舒适性估计较高。")
        elif quality < 55:
            if hotel.get("rating") is not None:
                warnings.append("酒店公开评分偏低，建议结合评论内容再确认。")
            else:
                warnings.append("酒店舒适性只是基础估计，建议进一步核对真实评分和价格。")
        if hotel.get("price") is not None:
            if value_score is not None and value_score >= 75:
                reasons.append("参考价格在本批候选中更有优势，性价比得分较高。")
            else:
                reasons.append("已读取参考价格，便于在交通成本之外比较预算。")
        elif not hotel.get("marketDataSource"):
            warnings.append("当前没有读取到真实价格，可用 backend/hotel_data.json 补充。")
        reasons.append("当前按%s计算，推荐结果更贴近该出行方式。" % mode_text)
        if any(travel_preferences.values()):
            labels = []
            if travel_preferences.get("lessWalking"):
                labels.append("少步行")
            if travel_preferences.get("lessTransfers"):
                labels.append("少换乘")
            if travel_preferences.get("familyFriendly"):
                labels.append("亲子友好")
            if travel_preferences.get("elderFriendly"):
                labels.append("老人友好")
            if preference_fit is not None:
                reasons.append("已考虑%s偏好，匹配度 %.1f 分。" % ("、".join(labels), preference_fit))
            else:
                reasons.append("已考虑%s偏好。" % "、".join(labels))
            walking_values = [item.get("bestWalkingKilometers") for item in details if item.get("bestWalkingKilometers") is not None]
            transfer_values = [item.get("bestTransfers") for item in details if item.get("bestTransfers") is not None]
            if walking_values and max(walking_values) > 1.2:
                warnings.append("部分公交路线步行距离超过 1.2 km，带老人小孩时建议复核。")
            if transfer_values and max(transfer_values) > 1:
                warnings.append("部分公交路线需要多次换乘，建议预留缓冲时间。")
        weights_text = "当前权重：平均时间 %.0f%%、最远时间 %.0f%%、舒适性 %.0f%%。" % (
            weights["avgTime"] * 100,
            weights["maxTime"] * 100,
            weights["comfort"] * 100,
        )
        return {
            "reasons": reasons[:3],
            "warnings": warnings[:2],
            "comparison": "",
            "weightsSummary": weights_text,
        }


CLIENT = AmapClient()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def guess_type(self, path):
        if path.endswith(".html"):
            return "text/html; charset=utf-8"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        return super().guess_type(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            json_response(self, CLIENT.status())
            return
        if parsed.path == "/api/bounds":
            json_response(self, {"type": "FeatureCollection", "features": []})
            return
        if parsed.path == "/api/hotel-data":
            json_response(self, hotel_data_status())
            return
        if parsed.path == "/api/plans":
            params = parse_qs(parsed.query)
            plan_id = (params.get("id") or [""])[0]
            try:
                plan = get_saved_plan(plan_id)
                if plan is None:
                    json_response(self, {"error": "方案不存在或已被删除。"}, 404)
                else:
                    json_response(self, plan)
            except ValueError as exc:
                json_response(self, {"error": str(exc)}, 400)
            return
        if parsed.path == "/api/pois/search":
            params = parse_qs(parsed.query)
            q = (params.get("q") or [""])[0]
            city = (params.get("city") or [""])[0]
            try:
                json_response(self, {"items": CLIENT.search_pois(q, city=city)})
            except ValueError as exc:
                json_response(self, {"error": str(exc)}, 400)
            except Exception as exc:
                json_response(self, {"error": str(exc)}, 500)
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/recommend", "/api/itinerary", "/api/agent", "/api/hotel-data", "/api/plans", "/api/feedback"}:
            json_response(self, {"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if parsed.path == "/api/hotel-data":
                json_response(self, save_hotel_data(payload))
            elif parsed.path == "/api/plans":
                json_response(self, save_plan(payload))
            elif parsed.path == "/api/feedback":
                json_response(self, save_feedback(payload))
            elif parsed.path == "/api/recommend":
                json_response(self, CLIENT.recommend(payload))
            elif parsed.path == "/api/itinerary":
                json_response(self, CLIENT.itinerary(payload))
            else:
                json_response(self, CLIENT.agent(payload))
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, 400)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, 500)


def main():
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print("Serving AMap Travel Assistant at http://%s:%s" % (host, port))
    print("Set AMAP_KEY before searching or recommending.")
    server.serve_forever()


if __name__ == "__main__":
    main()

import os
import re
import sys
import json
import math
import threading
from datetime import datetime, timezone
from html import escape as html_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tkinter as tk
from tkinter import colorchooser, ttk
from typing import Optional, Dict, Any, List

import myNotebook as nb

plugin_name = "EDMC-StreamHUD"
PLUGIN_VERSION = "2.0.0"
__version__ = PLUGIN_VERSION

output_dir = os.path.join(os.path.expanduser("~"), "Documents", "EDMC-StreamHUD")
settings_file = os.path.join(output_dir, "settings.json")
totals_file = os.path.join(output_dir, "totals_and_state.json")
json_file = os.path.join(output_dir, "HUD.json")
html_file = os.path.join(output_dir, "HUD.html")
txt_dir = os.path.join(output_dir, "txt")

FONT_CHOICES = [
    "Segoe UI", "Arial", "Consolas", "Verdana", "Tahoma",
    "Trebuchet MS", "Roboto", "Orbitron", "Courier New",
]


FIELD_KEYS: List[str] = [
    "cmdr", "time", "system", "body", "station", "ship", "distance", "credits",
    "jumps", "next_jump",
    "unsold_exp", "unsold_bio", "exploration_session", "exobiology_session",
    "scanned", "first_disc", "mapped",
    "trade_profit", "cargo_status",
    "mining_mined",
    "combat_bounties", "combat_kills", "deaths", "merits", "mining_earnings",
]
FIELD_VISIBILITY_KEY = {k: f"show_{k}" for k in FIELD_KEYS}


MODE_DEFAULT_FIELDS = {
    "exploration": ["cmdr", "time", "system", "body", "station", "distance", "ship", "jumps", "next_jump",
                    "unsold_exp", "unsold_bio", "exploration_session", "exobiology_session",
                    "scanned", "first_disc", "mapped", "merits"],
    "trade": ["cmdr", "time", "system", "station", "ship", "jumps", "trade_profit", "cargo_status", "merits"],
    "mining": ["cmdr", "time", "system", "body", "ship", "cargo_status", "mining_mined", "mining_earnings", "merits"],
    "combat": ["cmdr", "time", "system", "ship", "combat_bounties", "combat_kills", "deaths", "merits"],
}

PRIVATE_FIELDS = {"credits"}
MODES = ["exploration", "trade", "mining", "combat", "auto"]

LANGUAGES = ["en", "tr", "de", "fr", "es", "ru"]
_I18N_KEYS = FIELD_KEYS + ["w_species", "w_ships", "w_left", "w_jumps"]


def _pack(*values: str) -> Dict[str, str]:
    return dict(zip(_I18N_KEYS, values))


I18N: Dict[str, Dict[str, str]] = {
    "en": _pack("CMDR", "Time", "System", "Body", "Station", "Ship", "Distance to Sol", "Balance",
                "Jumps", "Next Jump",
                "Unsold Discoveries", "Unsold Bio", "Exploration Earnings", "Exobiology Earnings",
                "Bodies Scanned", "First Discoveries", "Bodies Mapped",
                "Trade Session Profit", "Cargo Space", "Refined Minerals",
                "Bounty / Bond Claim", "Targets Destroyed", "Deaths", "Merits", "Mining Earnings",
                "Species", "Ships", "left", "jumps"),
    "tr": _pack("CMDR", "Süre", "Sistem", "Cisim", "İstasyon", "Gemi", "Sol'e Uzaklık", "Bakiye",
                "Atlayış", "Sonraki Atlayış",
                "Satılmamış Keşifler", "Satılmamış Biyo", "Keşif Kazancı", "Ekzobiyoloji Kazancı",
                "Taranan Cisimler", "İlk Keşifler", "Haritalanan Cisimler",
                "Ticaret Kârı", "Kargo", "Rafine Edilen",
                "Ödül / Bond", "Yok Edilen", "Ölümler", "Merit", "Madencilik Kazancı",
                "Tür", "Gemi", "kaldı", "atlayış"),
    "de": _pack("CMDR", "Zeit", "System", "Himmelskörper", "Station", "Schiff", "Entfernung zu Sol", "Kontostand",
                "Sprünge", "Nächster Sprung",
                "Unverkaufte Entdeckungen", "Unverkaufte Bio", "Erkundungseinnahmen", "Exobiologie-Einnahmen",
                "Gescannte Körper", "Erstentdeckungen", "Kartierte Körper",
                "Handelsgewinn", "Fracht", "Raffiniert",
                "Kopfgelder", "Abschüsse", "Tode", "Verdienste", "Bergbau-Einnahmen",
                "Arten", "Schiffe", "übrig", "Sprünge"),
    "fr": _pack("CMDR", "Temps", "Système", "Corps", "Station", "Vaisseau", "Distance à Sol", "Solde",
                "Sauts", "Prochain saut",
                "Découvertes invendues", "Bio invendue", "Gains d'exploration", "Gains d'exobiologie",
                "Corps scannés", "Premières découvertes", "Corps cartographiés",
                "Profit commercial", "Soute", "Raffiné",
                "Primes", "Destructions", "Morts", "Mérites", "Gains miniers",
                "espèces", "vaisseaux", "restants", "sauts"),
    "es": _pack("CMDR", "Tiempo", "Sistema", "Cuerpo", "Estación", "Nave", "Distancia a Sol", "Saldo",
                "Saltos", "Próximo salto",
                "Descubrimientos sin vender", "Bio sin vender", "Ganancias de exploración", "Ganancias de exobiología",
                "Cuerpos escaneados", "Primeros descubrimientos", "Cuerpos cartografiados",
                "Beneficio comercial", "Carga", "Refinado",
                "Recompensas", "Destrucciones", "Muertes", "Méritos", "Ganancias de minería",
                "especies", "naves", "restantes", "saltos"),
    "ru": _pack("CMDR", "Время", "Система", "Тело", "Станция", "Корабль", "Расстояние до Sol", "Баланс",
                "Прыжки", "Следующий прыжок",
                "Непроданные открытия", "Непроданная био", "Доход от исследований", "Доход от экзобиологии",
                "Просканировано тел", "Первооткрытия", "Картографировано",
                "Прибыль от торговли", "Груз", "Переработано",
                "Награды", "Уничтожено", "Смерти", "Заслуги", "Доход от добычи",
                "видов", "кораблей", "осталось", "прыжков"),
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "active_mode": "exploration",
    **{FIELD_VISIBILITY_KEY[k]: (k in MODE_DEFAULT_FIELDS["exploration"]) for k in FIELD_KEYS},

    "language": "en",
    "show_labels": True,

    "font_family": "Segoe UI",
    "font_size": 22,
    "label_font_size": 16,
    "font_bold": True,
    "label_bold": True,
    "font_color": "#FFFFFF",
    "label_color": "#7FDBFF",
    "text_shadow": True,
    "bg_enabled": True,
    "bg_color": "#000000",
    "bg_opacity": 50,
    "corner_radius": 8,
    "layout": "vertical",
    "flash_on_change": True,

    "http_server": True,
    "http_port": 8765,
    "write_text_files": False,
}

NUMERIC_RANGES = {
    "font_size": (8, 120),
    "label_font_size": (8, 120),
    "bg_opacity": (0, 100),
    "corner_radius": (0, 40),
    "http_port": (1024, 65535),
}
NUMERIC_KEYS = set(NUMERIC_RANGES)
COLOR_KEYS = ("font_color", "label_color", "bg_color")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

PRESETS: Dict[str, Dict[str, Any]] = {
    "Cyber Cyan (default)": {"font_color": "#FFFFFF", "label_color": "#7FDBFF", "bg_enabled": True,
                             "bg_color": "#000000", "bg_opacity": 50, "text_shadow": True},
    "Elite Orange": {"font_color": "#FFFFFF", "label_color": "#FF7100", "bg_enabled": True,
                     "bg_color": "#0B0B0B", "bg_opacity": 70, "text_shadow": True},
    "Terminal Green": {"font_color": "#7CFC00", "label_color": "#2E8B57", "bg_enabled": True,
                       "bg_color": "#000000", "bg_opacity": 75, "font_family": "Consolas", "text_shadow": False},
    "Hologram Blue": {"font_color": "#E6F7FF", "label_color": "#00B3FF", "bg_enabled": True,
                      "bg_color": "#001A33", "bg_opacity": 60, "text_shadow": True},
    "Minimal (no box)": {"font_color": "#FFFFFF", "label_color": "#CCCCCC", "bg_enabled": False,
                         "text_shadow": True},
    "Light Card": {"font_color": "#111111", "label_color": "#005F99", "bg_enabled": True,
                   "bg_color": "#FFFFFF", "bg_opacity": 85, "text_shadow": False},
}

PREVIEW_SAMPLE_VALUES = {
    "cmdr": "CMDR",
    "time": "2h 14m",
    "system": "Shinrarta Dezhra",
    "body": "Selene Jean",
    "station": "Jameson Memorial",
    "distance": "37.4 Ly",
    "ship": "MANDALAY",
    "credits": "1.250.000.000 cr",
    "jumps": "42 (1,234.5 Ly)",
    "next_jump": "Colonia (12 left)",
    "unsold_exp": "ELW: 2 | WW: 1",
    "unsold_bio": "5 Species",
    "exploration_session": "12.450.000 cr",
    "exobiology_session": "3.200.000 cr",
    "scanned": "87",
    "first_disc": "14",
    "mapped": "9",
    "trade_profit": "45.800.000 cr",
    "cargo_status": "720 / 752 t",
    "mining_mined": "128 t (Platinum 90, Painite 38)",
    "combat_bounties": "8.400.000 cr",
    "combat_kills": "14 Ships",
    "deaths": "2",
    "merits": "1.250",
    "mining_earnings": "18.700.000 cr",
}

def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


saved_state: Dict[str, Any] = {
    "cmdr": "",
    "system": "",
    "station": "Deep Space",
    "ship": "",
    "body": "Unknown",
    "distance_sol": 0.0,
    "credits": 0,
    "last_docked_ts": utc_now_str(),
    "last_event_ts": "",
    "last_event_ts_n": 0,

    "exploration_session": 0,
    "exobiology_session": 0,
    "unsold_elw": 0,
    "unsold_ww": 0,
    "unsold_aw": 0,
    "unsold_bio": 0,
    "unsold_bodies": {},
    "unsold_bio_keys": {},
    "scanned_bodies": 0,
    "first_discoveries": 0,
    "mapped_bodies": 0,

    "session_jumps": 0,
    "session_jump_dist": 0.0,
    "next_target": "",
    "next_remaining": 0,

    "trade_session_profit": 0,
    "cargo_count": 0,
    "cargo_capacity": 0,

    "mining_session_tons": 0,
    "mining_by_commodity": {},
    "mining_names": {},
    "mining_session_earnings": 0,
    "last_mined_commodity": "",

    "combat_session_bounties": 0,
    "combat_session_kills": 0,
    "deaths": 0,

    "session_merits": 0,
    "merit_base": 0,
    "last_merit_total": 0,
    "merit_provisional": 0,
    "last_merit_gain": 0,

    "effective_mode": "exploration",
}

PERSIST_KEYS = [
    "unsold_elw", "unsold_ww", "unsold_aw", "unsold_bio", "unsold_bodies", "unsold_bio_keys",
    "last_docked_ts", "last_event_ts", "last_event_ts_n",
    "exploration_session", "exobiology_session", "scanned_bodies", "first_discoveries", "mapped_bodies",
    "session_jumps", "session_jump_dist", "trade_session_profit",
    "mining_session_tons", "mining_by_commodity", "mining_names", "mining_session_earnings", "last_mined_commodity",
    "combat_session_bounties", "combat_session_kills", "deaths",
    "session_merits", "merit_base", "last_merit_total", "merit_provisional", "last_merit_gain",
]
SESSION_RESET_VALUES = {
    "exploration_session": 0, "exobiology_session": 0, "scanned_bodies": 0, "first_discoveries": 0,
    "mapped_bodies": 0, "session_jumps": 0, "session_jump_dist": 0.0, "trade_session_profit": 0,
    "mining_session_tons": 0, "mining_session_earnings": 0, "last_mined_commodity": "", "combat_session_bounties": 0,
    "combat_session_kills": 0, "deaths": 0, "session_merits": 0,
}

current_settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
vars_cfg: Dict[str, Any] = {}

_lock = threading.RLock()
_stop_event = threading.Event()
_ticker_thread: Optional[threading.Thread] = None
_httpd: Optional[ThreadingHTTPServer] = None
_httpd_thread: Optional[threading.Thread] = None
_last_json_text = ""
_last_txt: Dict[str, str] = {}
_seen_bodies: set = set()
_seen_mapped: set = set()

_replay_ts = ""
_replay_n = 0
_ts_seen = 0

MISSION_BURST_SECONDS = 20.0
KILL_MERIT_WINDOW = 3.0
KILL_DEDUPE_WINDOW = 6.0
_burst_until = 0.0
_mission_marks: List[float] = []
_last_burst_gain = 0
_last_target: Optional[Dict[str, Any]] = None
_lock_lost_epoch: Optional[float] = None
_last_reward_kill_epoch: Optional[float] = None
_last_merit_kill_epoch: Optional[float] = None


def log(msg: str):
    print(f"[{plugin_name}] {msg}", file=sys.stderr)


def safe_lower(val: Any) -> str:
    if val is None:
        return ""
    return str(val).lower().strip()


def ensure_dir():
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        log(f"Directory error: {e}")


def atomic_write(path: str, text: str):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    last_err: Optional[Exception] = None
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last_err = e
            _stop_event.wait(0.05)
    if last_err:
        raise last_err


def tr(key: str, lang: Optional[str] = None) -> str:
    lang = lang or current_settings.get("language", "en")
    return I18N.get(lang, I18N["en"]).get(key) or I18N["en"].get(key, key)


def field_rows(lang: Optional[str] = None):
    return [(k, tr(k, lang)) for k in FIELD_KEYS]


def format_credits(value: int) -> str:
    return f"{int(value):,}".replace(",", ".") + " cr"


def hex_to_rgb(hex_color: str):
    hex_color = (hex_color or "#000000").lstrip("#")
    if len(hex_color) != 6:
        hex_color = "000000"
    try:
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)


def calculate_time() -> str:
    try:
        last_dt = datetime.strptime(saved_state["last_docked_ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - last_dt
        total = max(0, int(diff.total_seconds()))
        days, rem = divmod(total, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        if days > 0:
            return f"{days}d {hours}h"
        return f"{hours}h {minutes}m"
    except Exception:
        return "0h 0m"


def sanitize_settings(raw: Any) -> Dict[str, Any]:
    cfg = DEFAULT_SETTINGS.copy()
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in DEFAULT_SETTINGS:
                cfg[k] = v
        mode = cfg.get("active_mode") if cfg.get("active_mode") in MODES else "exploration"
        if raw:
            for fk in FIELD_KEYS:
                if FIELD_VISIBILITY_KEY[fk] not in raw:
                    cfg[FIELD_VISIBILITY_KEY[fk]] = (fk not in PRIVATE_FIELDS) if mode == "auto" else (fk in MODE_DEFAULT_FIELDS[mode])
    for k, default in DEFAULT_SETTINGS.items():
        v = cfg[k]
        if isinstance(default, bool):
            if not isinstance(v, bool):
                cfg[k] = default
        elif k in NUMERIC_RANGES:
            lo, hi = NUMERIC_RANGES[k]
            try:
                cfg[k] = max(lo, min(hi, int(float(str(v).strip()))))
            except (TypeError, ValueError):
                cfg[k] = default
        elif k in COLOR_KEYS:
            cfg[k] = v if isinstance(v, str) and _COLOR_RE.match(v.strip()) else default
            cfg[k] = cfg[k].strip()
        elif k == "active_mode":
            cfg[k] = v if v in MODES else default
        elif k == "layout":
            cfg[k] = v if v in ("vertical", "horizontal") else default
        elif k == "language":
            cfg[k] = v if v in LANGUAGES else default
        elif k == "font_family":
            cleaned = re.sub(r'[\"<>\\;{}]', "", str(v)).strip() if v else ""
            cfg[k] = cleaned or default
    return cfg


def load_settings() -> dict:
    ensure_dir()
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                return sanitize_settings(json.load(f))
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(data: dict):
    ensure_dir()
    try:
        atomic_write(settings_file, json.dumps(data, indent=2))
    except Exception as e:
        log(f"Settings save error: {e}")


def load_totals() -> dict:
    ensure_dir()
    if os.path.exists(totals_file):
        try:
            with open(totals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def save_totals():
    ensure_dir()
    try:
        with _lock:
            payload = {k: saved_state[k] for k in PERSIST_KEYS}
        atomic_write(totals_file, json.dumps(payload, indent=2))
    except Exception as e:
        log(f"Totals save error: {e}")


UNSOLD_CLASS_CODES = {"earthlike body": "elw", "water world": "ww", "ammonia world": "aw"}


def _body_key(entry: Dict[str, Any]) -> Optional[str]:
    sa, bid = entry.get("SystemAddress"), entry.get("BodyID")
    if sa is not None and bid is not None:
        return f"{sa}:{bid}"
    name = entry.get("BodyName")
    return f"n:{name}" if name else None


def recompute_unsold():
    counts = {"elw": 0, "ww": 0, "aw": 0}
    for code in saved_state["unsold_bodies"].values():
        if code in counts:
            counts[code] += 1
    saved_state["unsold_elw"] = counts["elw"]
    saved_state["unsold_ww"] = counts["ww"]
    saved_state["unsold_aw"] = counts["aw"]
    saved_state["unsold_bio"] = len(saved_state["unsold_bio_keys"])


def register_scan_unsold(entry: Dict[str, Any]):
    code = UNSOLD_CLASS_CODES.get(safe_lower(entry.get("PlanetClass")))
    key = _body_key(entry)
    if code and key:
        saved_state["unsold_bodies"][key] = code
        recompute_unsold()


def register_bio_unsold(entry: Dict[str, Any]):
    if safe_lower(entry.get("ScanType")) in ("analyse", "analyze", "analysis"):
        key = f"{entry.get('SystemAddress')}:{entry.get('Body')}:{entry.get('Species')}"
        saved_state["unsold_bio_keys"][key] = 1
        recompute_unsold()


def reset_unsold_exploration():
    saved_state["unsold_bodies"].clear()
    recompute_unsold()


def reset_unsold_bio():
    saved_state["unsold_bio_keys"].clear()
    recompute_unsold()


def reset_unsold_all():
    saved_state["unsold_bodies"].clear()
    saved_state["unsold_bio_keys"].clear()
    recompute_unsold()


def parse_latest_journals_for_unsold():
    saved_games = os.path.join(os.path.expanduser("~"), "Saved Games", "Frontier Developments", "Elite Dangerous")
    if not os.path.exists(saved_games):
        return
    try:
        journals = [os.path.join(saved_games, f) for f in os.listdir(saved_games)
                    if f.startswith("Journal.") and f.endswith(".log")]
        if not journals:
            return
        journals_with_mtime = sorted([(j, os.path.getmtime(j)) for j in journals], key=lambda x: x[1])
        current_session_journal = journals_with_mtime[-1][0]
        older_journals = [(j, m) for j, m in journals_with_mtime if j != current_session_journal]

        reset_unsold_all()

        if not older_journals:
            return

        now = datetime.now().timestamp()
        filtered_journals = [(j, m) for j, m in older_journals if now - m < 5 * 86400]
        if not filtered_journals:
            filtered_journals = sorted(older_journals, key=lambda x: x[1], reverse=True)[:5]
        filtered_journals.sort(key=lambda x: x[1])

        for j_file, _ in filtered_journals:
            with open(j_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        event_type = safe_lower(entry.get("event"))
                        if event_type == "scan":
                            register_scan_unsold(entry)
                        elif event_type == "scanorganic":
                            register_bio_unsold(entry)
                        elif event_type in ("multisellexplorationdata", "sellexplorationdata"):
                            reset_unsold_exploration()
                        elif event_type == "sellorganicdata":
                            reset_unsold_bio()
                        elif event_type == "died":
                            reset_unsold_all()
                    except Exception:
                        continue
    except Exception as e:
        log(f"Journal parse error: {e}")


def format_exploration_risk() -> str:
    parts = []
    if saved_state["unsold_elw"] > 0:
        parts.append(f"ELW: {saved_state['unsold_elw']}")
    if saved_state["unsold_ww"] > 0:
        parts.append(f"WW: {saved_state['unsold_ww']}")
    if saved_state["unsold_aw"] > 0:
        parts.append(f"AW: {saved_state['unsold_aw']}")
    return " | ".join(parts)


MINEABLE_COMMODITIES = {
    "platinum", "painite", "osmium", "palladium", "gold", "silver", "bromellite", "lowtemperaturediamond",
    "rhodplumsite", "serendibite", "grandidierite", "alexandrite", "monazite", "musgravite", "benitoite",
    "opal", "tritium", "bauxite", "bertrandite", "coltan", "cobalt", "gallite", "indite", "lepidolite",
    "praseodymium", "samarium", "uraninite", "methanolmonohydrateclathrate", "methaneclathrate",
}


def norm_commodity(raw: Any) -> str:
    t = safe_lower(raw)
    if t.startswith("$"):
        t = t[1:]
    if t.endswith("_name;"):
        t = t[:-6]
    return t


def format_mining() -> str:
    by = {k: v for k, v in (saved_state.get("mining_by_commodity") or {}).items() if v > 0}
    total = sum(by.values())
    if total <= 0:
        return ""
    names = saved_state.get("mining_names") or {}
    top = sorted(by.items(), key=lambda kv: kv[1], reverse=True)[:2]
    detail = ", ".join(f"{names.get(k, k.title())} {n}" for k, n in top)
    return f"{total} t ({detail})" if detail else f"{total} t"


def _epoch(ts: Any) -> Optional[float]:
    try:
        return datetime.strptime(str(ts), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def refresh_session_merits():
    s = saved_state
    if s["last_merit_total"] > 0:
        s["session_merits"] = max(0, s["last_merit_total"] + s["merit_provisional"] - s["merit_base"])


def reset_merit_session():
    s = saved_state
    if s["last_merit_total"] > 0:
        s["last_merit_total"] += s["merit_provisional"]
        s["merit_base"] = s["last_merit_total"]
    s["merit_provisional"] = 0
    s["session_merits"] = 0


def apply_powerplay_snapshot(entry: Dict[str, Any]):
    s = saved_state
    merits = entry.get("Merits")
    if not isinstance(merits, (int, float)):
        return
    m = int(merits)
    if s["last_merit_total"] > 0:
        expected = s["last_merit_total"] + s["merit_provisional"]
        drop = expected - m
        if not (0 < drop <= s["last_merit_gain"]):
            s["merit_base"] += m - expected
    else:
        s["merit_base"] = m - s["session_merits"]
    s["last_merit_total"] = m
    s["merit_provisional"] = 0
    s["last_merit_gain"] = 0
    refresh_session_merits()


def apply_merit_award(entry: Dict[str, Any], t: Optional[float]) -> bool:
    global _last_burst_gain
    s = saved_state
    gained = int(entry.get("MeritsGained", 0) or 0)
    total = entry.get("TotalMerits")
    total = int(total) if isinstance(total, (int, float)) else None
    in_burst = t is not None and t <= _burst_until
    if not in_burst:
        _mission_marks.clear()

    if s["last_merit_total"] <= 0:
        s["session_merits"] += max(0, gained)
        if total is not None:
            s["last_merit_total"] = total
            s["merit_base"] = total - s["session_merits"]
            s["merit_provisional"] = 0
        if in_burst and _mission_marks:
            _mission_marks.pop(0)
            _last_burst_gain = gained
    elif in_burst:
        if _mission_marks:
            _mission_marks.pop(0)
            s["merit_provisional"] += gained
            _last_burst_gain = gained
        elif gained != _last_burst_gain:
            s["merit_provisional"] += gained
    elif total is not None:
        s["last_merit_total"] = total
        s["merit_provisional"] = 0
    else:
        s["last_merit_total"] += gained
    s["last_merit_gain"] = gained
    refresh_session_merits()
    return in_burst


def build_raw_values() -> Dict[str, str]:
    s = saved_state
    cap, cnt = s["cargo_capacity"], s["cargo_count"]
    if cap > 0:
        cargo_str = f"{cnt} / {cap} t"
    elif cnt > 0:
        cargo_str = f"{cnt} t"
    else:
        cargo_str = ""

    if s["next_target"]:
        nxt = f"{s['next_target']} ({s['next_remaining']} {tr('w_left')})" if s["next_remaining"] > 0 else s["next_target"]
    else:
        nxt = ""

    def credits_or_empty(v):
        return format_credits(v) if v > 0 else ""

    def num_or_empty(v):
        return str(v) if v > 0 else ""

    return {
        "cmdr": s["cmdr"],
        "time": calculate_time(),
        "system": s["system"],
        "body": s["body"] if s["body"] != "Unknown" else "",
        "station": s["station"] if s["station"] != "Deep Space" else "",
        "ship": s["ship"],
        "distance": f"{s['distance_sol']:,.1f} Ly" if s["distance_sol"] > 0 else "",
        "credits": credits_or_empty(s["credits"]),
        "jumps": f"{s['session_jumps']} ({s['session_jump_dist']:,.1f} Ly)" if s["session_jumps"] > 0 else "",
        "next_jump": nxt,
        "unsold_exp": format_exploration_risk(),
        "unsold_bio": f"{s['unsold_bio']} {tr('w_species')}" if s["unsold_bio"] > 0 else "",
        "exploration_session": credits_or_empty(s["exploration_session"]),
        "exobiology_session": credits_or_empty(s["exobiology_session"]),
        "scanned": num_or_empty(s["scanned_bodies"]),
        "first_disc": num_or_empty(s["first_discoveries"]),
        "mapped": num_or_empty(s["mapped_bodies"]),
        "trade_profit": credits_or_empty(s["trade_session_profit"]),
        "cargo_status": cargo_str,
        "mining_mined": format_mining(),
        "mining_earnings": credits_or_empty(s["mining_session_earnings"]),
        "combat_bounties": credits_or_empty(s["combat_session_bounties"]),
        "combat_kills": f"{s['combat_session_kills']} {tr('w_ships')}" if s["combat_session_kills"] > 0 else "",
        "deaths": num_or_empty(s["deaths"]),
        "merits": f"{s['session_merits']:,}".replace(",", ".") if s["session_merits"] > 0 else "",
    }


def build_final_data() -> Dict[str, str]:
    cfg = current_settings
    selected_mode = cfg.get("active_mode", "exploration")
    auto = selected_mode == "auto"
    mode_fields = set(MODE_DEFAULT_FIELDS.get(saved_state["effective_mode"], []))
    raw = build_raw_values()
    final = {}
    for key in FIELD_KEYS:
        enabled = cfg.get(FIELD_VISIBILITY_KEY[key], False)
        if auto and key not in mode_fields and key not in PRIVATE_FIELDS:
            enabled = False
        final[key] = raw[key] if (enabled and raw.get(key)) else "HIDE"
    return final


def update_hud_file(force: bool = False):
    global _last_json_text
    ensure_dir()
    with _lock:
        final_data = build_final_data()
        text = json.dumps(final_data, ensure_ascii=False)
        if force or text != _last_json_text:
            try:
                atomic_write(json_file, text)
                _last_json_text = text
            except Exception as e:
                log(f"HUD.json write error: {e}")
        if current_settings.get("write_text_files", False):
            try:
                os.makedirs(txt_dir, exist_ok=True)
                for key, val in final_data.items():
                    out = "" if val == "HIDE" else val
                    if force or _last_txt.get(key) != out:
                        atomic_write(os.path.join(txt_dir, f"{key}.txt"), out)
                        _last_txt[key] = out
            except Exception as e:
                log(f"Text file write error: {e}")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="%%LANG%%">
<head>
<meta charset="utf-8">
<title>EDMC-StreamHUD</title>
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; font-family: "%%FONT%%", "Segoe UI", sans-serif; }
  .hud { display: none; flex-direction: %%DIRECTION%%; %%WRAP%% gap: %%GAP%%; padding: 12px 16px; %%BG%% border-radius: %%RADIUS%%px; width: fit-content; max-width: 100vw; box-sizing: border-box; }
  .row { display: none; gap: 10px; align-items: baseline; %%ROWEXTRA%% }
  .label { %%LABELDISPLAY%% color: %%LABELCOLOR%%; font-weight: %%LABELWEIGHT%%; font-size: %%LABELSIZE%%px; font-family: "%%FONT%%", "Segoe UI", sans-serif; }
  .value { color: %%VALUECOLOR%%; font-weight: %%VALUEWEIGHT%%; font-size: %%VALUESIZE%%px; font-family: "%%FONT%%", "Segoe UI", sans-serif; %%SHADOW%% }
  @keyframes flash { 0% { filter: brightness(2.4); } 100% { filter: brightness(1); } }
  .value.flash { animation: flash 1s ease-out; }
</style>
</head>
<body>
  <div class="hud" id="hud">
    %%ROWS%%
  </div>
  <script>
    const FLASH = %%FLASH%%;
    const last = {};
    async function refreshHud() {
      try {
        const res = await fetch('HUD.json?t=' + Date.now(), {cache: 'no-store'});
        const data = await res.json();
        let visible = 0;
        for (const key in data) {
          const el = document.getElementById(key);
          const row = document.getElementById('row-' + key);
          if (!el || !row) continue;
          if (data[key] === null || data[key] === 'HIDE') {
            row.style.display = 'none';
            last[key] = null;
          } else {
            if (last[key] !== data[key]) {
              el.textContent = data[key];
              if (FLASH && last[key] !== undefined && last[key] !== null) {
                el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
              }
              last[key] = data[key];
            }
            row.style.display = 'flex';
            visible++;
          }
        }
        document.getElementById('hud').style.display = visible ? 'inline-flex' : 'none';
      } catch (e) {}
    }
    refreshHud();
    setInterval(refreshHud, 1000);
  </script>
</body>
</html>
"""


def generate_html():
    ensure_dir()
    cfg = current_settings
    r, g, b = hex_to_rgb(cfg.get("bg_color", "#000000"))
    opacity = max(0, min(100, int(cfg.get("bg_opacity", 50)))) / 100
    bg_css = f"background: rgba({r}, {g}, {b}, {opacity:.2f});" if cfg.get("bg_enabled", True) else "background: transparent;"
    direction = "column" if cfg.get("layout", "vertical") == "vertical" else "row"
    lang = cfg.get("language", "en")

    rows = "".join(
        f'<div id="row-{k}" class="row"><span class="label">{html_escape(label)}</span>'
        f'<span id="{k}" class="value"></span></div>'
        for k, label in field_rows(lang)
    )
    repl = {
        "%%LANG%%": lang,
        "%%FONT%%": cfg.get("font_family", "Segoe UI"),
        "%%DIRECTION%%": direction,
        "%%BG%%": bg_css,
        "%%RADIUS%%": str(int(cfg.get("corner_radius", 8))),
        "%%WRAP%%": "flex-wrap: wrap;" if direction == "row" else "",
        "%%GAP%%": "6px 24px" if direction == "row" else "4px",
        "%%ROWEXTRA%%": "max-width: 100%;" if direction == "row" else "white-space: nowrap;",
        "%%LABELDISPLAY%%": "" if cfg.get("show_labels", True) else "display: none;",
        "%%LABELCOLOR%%": cfg.get("label_color", "#7FDBFF"),
        "%%LABELWEIGHT%%": "600" if cfg.get("label_bold", True) else "400",
        "%%LABELSIZE%%": str(int(cfg.get("label_font_size", 16))),
        "%%VALUECOLOR%%": cfg.get("font_color", "#FFFFFF"),
        "%%VALUEWEIGHT%%": "700" if cfg.get("font_bold", True) else "400",
        "%%VALUESIZE%%": str(int(cfg.get("font_size", 22))),
        "%%SHADOW%%": "text-shadow: 0 0 5px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9);" if cfg.get("text_shadow", True) else "",
        "%%FLASH%%": "true" if cfg.get("flash_on_change", True) else "false",
        "%%ROWS%%": rows,
    }
    page = HTML_TEMPLATE
    for token, value in repl.items():
        page = page.replace(token, value)
    try:
        atomic_write(html_file, page)
    except Exception as e:
        log(f"HUD.html write error: {e}")


class _HudHandler(BaseHTTPRequestHandler):
    server_version = "StreamHUD"

    def log_message(self, *args):
        pass

    def _send(self, code: int, body: bytes = b"", ctype: str = "text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        routes = {
            "/": (html_file, "text/html; charset=utf-8"),
            "/HUD.html": (html_file, "text/html; charset=utf-8"),
            "/HUD.json": (json_file, "application/json; charset=utf-8"),
        }
        target = routes.get(path)
        if not target:
            self._send(404, b"Not found")
            return
        try:
            with open(target[0], "rb") as f:
                self._send(200, f.read(), target[1])
        except OSError:
            self._send(503, b"HUD not ready yet")

    do_HEAD = do_GET


def stop_server():
    global _httpd, _httpd_thread
    srv, _httpd = _httpd, None
    if srv is not None:
        try:
            srv.shutdown()
            srv.server_close()
        except Exception as e:
            log(f"Server stop error: {e}")
    _httpd_thread = None


def start_server():
    global _httpd, _httpd_thread
    stop_server()
    if not current_settings.get("http_server", True):
        return
    port = int(current_settings.get("http_port", 8765))
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), _HudHandler)
        srv.daemon_threads = True
    except OSError as e:
        log(f"Could not start local server on port {port}: {e}. Use the local HUD.html file in OBS instead.")
        return
    _httpd = srv
    _httpd_thread = threading.Thread(target=srv.serve_forever, name="StreamHUD-http", daemon=True)
    _httpd_thread.start()
    log(f"OBS Browser Source URL: http://127.0.0.1:{port}/")


def _ticker():
    while not _stop_event.wait(5):
        try:
            update_hud_file()
        except Exception as e:
            log(f"Ticker error: {e}")


def plugin_start3(plugin_dir: str) -> str:
    global current_settings, _ticker_thread, _replay_ts, _replay_n, _ts_seen
    global _burst_until, _last_burst_gain, _last_target, _lock_lost_epoch, _last_reward_kill_epoch, _last_merit_kill_epoch
    ensure_dir()
    current_settings = load_settings()

    totals = load_totals()
    for key in PERSIST_KEYS:
        if key in totals:
            saved_state[key] = totals[key]
    _replay_ts = str(saved_state.get("last_event_ts") or "")
    _replay_n = int(saved_state.get("last_event_ts_n") or 0)
    _ts_seen = 0
    _burst_until, _last_burst_gain = 0.0, 0
    _mission_marks.clear()
    _last_target = _lock_lost_epoch = _last_reward_kill_epoch = _last_merit_kill_epoch = None
    if "merit_base" not in totals:
        last = saved_state["last_merit_total"]
        saved_state["merit_base"] = last - saved_state["session_merits"] if last > 0 else 0
        saved_state["merit_provisional"] = 0
    for dict_key in ("mining_by_commodity", "mining_names", "unsold_bodies", "unsold_bio_keys"):
        if not isinstance(saved_state.get(dict_key), dict):
            saved_state[dict_key] = {}
    if "mining_names" not in totals:
        saved_state["mining_by_commodity"] = {}
    migrated: Dict[str, int] = {}
    for k, v in saved_state["mining_by_commodity"].items():
        try:
            migrated[norm_commodity(k)] = migrated.get(norm_commodity(k), 0) + int(v)
        except (TypeError, ValueError):
            continue
    saved_state["mining_by_commodity"] = migrated

    parse_latest_journals_for_unsold()
    generate_html()
    update_hud_file(force=True)
    start_server()

    _stop_event.clear()
    _ticker_thread = threading.Thread(target=_ticker, name="StreamHUD-ticker", daemon=True)
    _ticker_thread.start()
    print(f"[{plugin_name}] v{PLUGIN_VERSION} - Active.")
    return f"{plugin_name} v{PLUGIN_VERSION}"


def plugin_stop() -> None:
    _stop_event.set()
    stop_server()
    save_totals()


def obs_url() -> str:
    try:
        port = int(vars_cfg["http_port"].get()) if "http_port" in vars_cfg else int(current_settings.get("http_port", 8765))
    except (TypeError, ValueError):
        port = int(current_settings.get("http_port", 8765))
    return f"http://127.0.0.1:{port}/"


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]:
    try:
        cfg = load_settings()
        main_frame = nb.Frame(parent)
        main_frame.columnconfigure(0, weight=1)
        vars_cfg.clear()

        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        tab_data = nb.Frame(notebook)
        tab_style = nb.Frame(notebook)
        tab_obs = nb.Frame(notebook)
        notebook.add(tab_data, text="Data & Mode")
        notebook.add(tab_style, text="Appearance & Style")
        notebook.add(tab_obs, text="OBS & Output")

        td_row = 0

        def next_td_row():
            nonlocal td_row
            td_row += 1
            return td_row

        nb.Label(tab_data, text="Streamer Mode Selection", font=("Helvetica", 9, "bold")).grid(
            row=td_row, column=0, columnspan=2, sticky=tk.W, pady=(8, 2), padx=10)

        mode_var = tk.StringVar(value=cfg.get("active_mode", "exploration"))
        vars_cfg["active_mode"] = mode_var
        r = next_td_row()
        nb.Label(tab_data, text="Active Activity Profile:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(tab_data, mode_var, mode_var.get(), *MODES).grid(row=r, column=1, sticky=tk.W)

        nb.Label(tab_data, text="'auto' follows what you are doing (jumping, mining, trading, fighting).").grid(
            row=next_td_row(), column=0, columnspan=2, sticky=tk.W, padx=10)

        ttk.Separator(tab_data, orient="horizontal").grid(
            row=next_td_row(), column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))

        nb.Label(tab_data, text="HUD Fields (picking a profile ticks its recommended fields)",
                 font=("Helvetica", 9, "bold")).grid(
            row=next_td_row(), column=0, columnspan=2, sticky=tk.W, pady=(8, 2), padx=10)

        field_checkbox_defs = [
            ("cmdr", "Commander Name (CMDR)"),
            ("time", "Time since last dock / reset"),
            ("system", "Current System"),
            ("body", "Current Body"),
            ("station", "Station Name"),
            ("ship", "Ship Name / Model"),
            ("distance", "Distance to Sol"),
            ("credits", "Account Balance (private!)"),
            ("jumps", "Session Jumps & Distance"),
            ("next_jump", "Next Route Jump"),
            ("unsold_exp", "Unsold ELW / WW / AW"),
            ("unsold_bio", "Unsold Exobiology Species"),
            ("exploration_session", "Exploration Earnings"),
            ("exobiology_session", "Exobiology Earnings"),
            ("scanned", "Bodies Scanned"),
            ("first_disc", "First Discoveries"),
            ("mapped", "Bodies Mapped (DSS)"),
            ("trade_profit", "Trade Session Profit"),
            ("cargo_status", "Cargo Space"),
            ("mining_mined", "Refined Minerals (unsold)"),
            ("mining_earnings", "Mining Earnings (sold)"),
            ("combat_bounties", "Bounty / Combat Bond Claims"),
            ("combat_kills", "Targets Destroyed"),
            ("deaths", "Death Counter"),
            ("merits", "Powerplay Merits (session)"),
        ]
        checkbox_vars = {}
        base_row = td_row + 1
        for idx, (key, label_text) in enumerate(field_checkbox_defs):
            vkey = FIELD_VISIBILITY_KEY[key]
            vars_cfg[vkey] = tk.BooleanVar(value=cfg.get(vkey, False))
            checkbox_vars[key] = vars_cfg[vkey]
            nb.Checkbutton(tab_data, text=label_text, variable=vars_cfg[vkey]).grid(
                row=base_row + idx // 2, column=idx % 2, sticky=tk.W, pady=1, padx=10)
        td_row = base_row + (len(field_checkbox_defs) + 1) // 2

        def on_mode_changed(*_args):
            selected = mode_var.get()
            if selected == "auto":
                wanted = set(FIELD_KEYS) - PRIVATE_FIELDS
            else:
                wanted = set(MODE_DEFAULT_FIELDS.get(selected, []))
            for f_key, v_obj in checkbox_vars.items():
                v_obj.set(f_key in wanted)

        mode_var.trace_add("write", on_mode_changed)

        ttk.Separator(tab_data, orient="horizontal").grid(
            row=next_td_row(), column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))

        def reset_session_action():
            with _lock:
                saved_state.update(SESSION_RESET_VALUES)
                reset_merit_session()
                saved_state["mining_by_commodity"] = {}
                saved_state["last_docked_ts"] = utc_now_str()
            save_totals()
            update_hud_file()

        nb.Button(tab_data, text="Reset All Session Stats & Timer", command=reset_session_action).grid(
            row=next_td_row(), column=0, columnspan=2, sticky=tk.W, padx=10, pady=4)

        ts_row = 0

        def next_ts_row():
            nonlocal ts_row
            ts_row += 1
            return ts_row

        nb.Label(tab_style, text="Layout & Style Settings", font=("Helvetica", 9, "bold")).grid(
            row=ts_row, column=0, columnspan=3, sticky=tk.W, pady=(8, 4), padx=10)

        preset_var = tk.StringVar(value="Choose a theme...")
        r = next_ts_row()
        nb.Label(tab_style, text="Theme Preset:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(tab_style, preset_var, preset_var.get(), *PRESETS.keys()).grid(row=r, column=1, sticky=tk.W)

        lang_var = tk.StringVar(value=cfg.get("language", "en"))
        vars_cfg["language"] = lang_var
        r = next_ts_row()
        nb.Label(tab_style, text="HUD Language (en/tr/de/fr/es/ru):").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(tab_style, lang_var, lang_var.get(), *LANGUAGES).grid(row=r, column=1, sticky=tk.W)

        layout_var = tk.StringVar(value=cfg.get("layout", "vertical"))
        vars_cfg["layout"] = layout_var
        r = next_ts_row()
        nb.Label(tab_style, text="Layout Direction:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(tab_style, layout_var, layout_var.get(), "vertical", "horizontal").grid(row=r, column=1, sticky=tk.W)

        def add_check(parent_tab, key, text):
            var = tk.BooleanVar(value=cfg.get(key, DEFAULT_SETTINGS[key]))
            vars_cfg[key] = var
            nb.Checkbutton(parent_tab, text=text, variable=var).grid(
                row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10)

        def add_entry(parent_tab, key, text, width=6):
            var = tk.StringVar(value=str(cfg.get(key, DEFAULT_SETTINGS[key])))
            vars_cfg[key] = var
            r_ = next_ts_row()
            nb.Label(parent_tab, text=text).grid(row=r_, column=0, sticky=tk.W, padx=10)
            nb.EntryMenu(parent_tab, textvariable=var, width=width).grid(row=r_, column=1, sticky=tk.W)

        def add_color_row(parent_tab, label_text, key):
            color_var = tk.StringVar(value=cfg.get(key, DEFAULT_SETTINGS[key]))
            vars_cfg[key] = color_var
            r_ = next_ts_row()
            nb.Label(parent_tab, text=label_text).grid(row=r_, column=0, sticky=tk.W, padx=10)
            nb.EntryMenu(parent_tab, textvariable=color_var, width=10).grid(row=r_, column=1, sticky=tk.W)
            nb.Button(
                parent_tab, text="Choose",
                command=lambda v=color_var: v.set(colorchooser.askcolor(color=v.get() or "#FFFFFF", parent=main_frame)[1] or v.get())
            ).grid(row=r_, column=2, sticky=tk.W, padx=(4, 10))

        add_check(tab_style, "show_labels", "Show Field Labels")
        add_check(tab_style, "bg_enabled", "Enable Background Box")
        add_color_row(tab_style, "Background Colour:", "bg_color")
        add_entry(tab_style, "bg_opacity", "Background Opacity (0-100):")
        add_entry(tab_style, "corner_radius", "Corner Radius (0-40):")
        add_check(tab_style, "text_shadow", "Enable Text Shadow")
        add_check(tab_style, "flash_on_change", "Flash value when it changes")

        ttk.Separator(tab_style, orient="horizontal").grid(
            row=next_ts_row(), column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 4))
        nb.Label(tab_style, text="Font & Typography", font=("Helvetica", 9, "bold")).grid(
            row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=(0, 4), padx=10)

        font_var = tk.StringVar(value=cfg.get("font_family", "Segoe UI"))
        vars_cfg["font_family"] = font_var
        r = next_ts_row()
        nb.Label(tab_style, text="Font Family:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(
            tab_style, font_var, font_var.get(),
            *(FONT_CHOICES if font_var.get() in FONT_CHOICES else [font_var.get()] + FONT_CHOICES)
        ).grid(row=r, column=1, sticky=tk.W)

        add_entry(tab_style, "font_size", "Value Font Size:")
        add_entry(tab_style, "label_font_size", "Label Font Size:")
        add_check(tab_style, "font_bold", "Bold Values")
        add_check(tab_style, "label_bold", "Bold Labels")
        add_color_row(tab_style, "Value Colour:", "font_color")
        add_color_row(tab_style, "Label Colour:", "label_color")

        def apply_preset(*_args):
            preset = PRESETS.get(preset_var.get())
            if not preset:
                return
            for k, v in preset.items():
                var = vars_cfg.get(k)
                if var is not None:
                    var.set(v)

        preset_var.trace_add("write", apply_preset)

        to_row = 0

        def next_to_row():
            nonlocal to_row
            to_row += 1
            return to_row

        nb.Label(tab_obs, text="OBS Browser Source", font=("Helvetica", 9, "bold")).grid(
            row=to_row, column=0, columnspan=3, sticky=tk.W, pady=(8, 4), padx=10)

        http_var = tk.BooleanVar(value=cfg.get("http_server", True))
        vars_cfg["http_server"] = http_var
        nb.Checkbutton(tab_obs, text="Run local web server (recommended)", variable=http_var).grid(
            row=next_to_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10)

        port_var = tk.StringVar(value=str(cfg.get("http_port", 8765)))
        vars_cfg["http_port"] = port_var
        r = next_to_row()
        nb.Label(tab_obs, text="Port:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.EntryMenu(tab_obs, textvariable=port_var, width=8).grid(row=r, column=1, sticky=tk.W)

        url_var = tk.StringVar(value=obs_url())
        r = next_to_row()
        nb.Label(tab_obs, text="Browser Source URL:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.EntryMenu(tab_obs, textvariable=url_var, width=34).grid(row=r, column=1, sticky=tk.W)

        def refresh_url(*_a):
            url_var.set(obs_url())

        port_var.trace_add("write", refresh_url)

        def copy_to_clipboard(text: str):
            main_frame.clipboard_clear()
            main_frame.clipboard_append(text)

        r = next_to_row()
        nb.Button(tab_obs, text="Copy URL", command=lambda: copy_to_clipboard(obs_url())).grid(
            row=r, column=0, sticky=tk.W, padx=10, pady=4)
        nb.Button(tab_obs, text="Copy local file path", command=lambda: copy_to_clipboard(html_file)).grid(
            row=r, column=1, sticky=tk.W, pady=4)

        def open_folder():
            try:
                ensure_dir()
                if hasattr(os, "startfile"):
                    os.startfile(output_dir)
            except Exception as e:
                log(f"Open folder error: {e}")

        nb.Button(tab_obs, text="Open output folder", command=open_folder).grid(
            row=r, column=2, sticky=tk.W, padx=10, pady=4)

        for line in (
            "OBS: Sources > + > Browser > paste the URL above (or tick 'Local file' and use the file path).",
            "Set Width/Height to match your layout (e.g. 1920 x 1080). The background stays transparent.",
            "Tip: no need to refresh - the HUD updates every second on its own.",
        ):
            nb.Label(tab_obs, text=line).grid(row=next_to_row(), column=0, columnspan=3, sticky=tk.W, padx=10)

        ttk.Separator(tab_obs, orient="horizontal").grid(
            row=next_to_row(), column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 4))
        nb.Label(tab_obs, text="Text sources (optional)", font=("Helvetica", 9, "bold")).grid(
            row=next_to_row(), column=0, columnspan=3, sticky=tk.W, pady=(0, 4), padx=10)
        txt_var = tk.BooleanVar(value=cfg.get("write_text_files", False))
        vars_cfg["write_text_files"] = txt_var
        nb.Checkbutton(tab_obs, text="Also write one .txt file per field (for OBS 'Text (GDI+)' > Read from file)",
                       variable=txt_var).grid(row=next_to_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10)
        nb.Label(tab_obs, text=f"Folder: {txt_dir}").grid(
            row=next_to_row(), column=0, columnspan=3, sticky=tk.W, padx=10)

        preview_container = nb.Frame(main_frame)
        preview_container.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 5))
        nb.Label(preview_container, text="Live Preview", font=("Helvetica", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 2))

        preview_canvas = tk.Canvas(preview_container, width=520, height=240,
                                   bg="#3a3a3a", highlightthickness=1, highlightbackground="#888888")
        preview_canvas.grid(row=1, column=0, sticky=tk.W)

        def redraw_preview(*_args):
            try:
                preview_canvas.delete("all")

                def gv(key, default):
                    v = vars_cfg.get(key)
                    if v is None:
                        return default
                    try:
                        val = v.get()
                        return val if val != "" else default
                    except Exception:
                        return default

                def gi(key, default, lo, hi):
                    try:
                        return max(lo, min(hi, int(gv(key, default))))
                    except (TypeError, ValueError):
                        return default

                lang_p = gv("language", "en")
                font_family_p = gv("font_family", "Segoe UI")
                font_size_base = gi("font_size", 22, 8, 120)
                label_size_base = gi("label_font_size", 16, 8, 120)
                bold_val_p = bool(gv("font_bold", True))
                bold_lbl_p = bool(gv("label_bold", True))
                font_color_p = gv("font_color", "#FFFFFF") or "#FFFFFF"
                label_color_p = gv("label_color", "#7FDBFF") or "#7FDBFF"
                shadow_p = bool(gv("text_shadow", True))
                labels_p = bool(gv("show_labels", True))
                bg_enabled_p = bool(gv("bg_enabled", True))
                bg_color_p = gv("bg_color", "#000000") or "#000000"
                bg_opacity_p = gi("bg_opacity", 50, 0, 100)
                layout_p = gv("layout", "vertical")

                canvas_w = int(str(preview_canvas["width"]))
                canvas_h = int(str(preview_canvas["height"]))
                backdrop = (58, 58, 58)

                preview_canvas.create_rectangle(0, 0, canvas_w, canvas_h, fill="#3a3a3a", outline="")
                preview_canvas.create_text(8, canvas_h - 8, anchor="sw", text="(live preview canvas)",
                                           fill="#888888", font=("Segoe UI", 8))

                visible_rows = [(k, tr(k, lang_p)) for k in FIELD_KEYS if bool(gv(FIELD_VISIBILITY_KEY[k], False))]
                if not visible_rows:
                    preview_canvas.create_text(canvas_w / 2, canvas_h / 2, text="(no fields selected)",
                                               fill="#aaaaaa", font=("Segoe UI", 10))
                    return

                def text_size(text, font):
                    if not text:
                        return (0, 0)
                    tmp = preview_canvas.create_text(-1000, -1000, text=text, font=font, anchor="nw")
                    bbox = preview_canvas.bbox(tmp)
                    preview_canvas.delete(tmp)
                    return (bbox[2] - bbox[0], bbox[3] - bbox[1]) if bbox else (0, 0)

                def layout(scale):
                    vs = max(6, int(font_size_base * scale))
                    ls = max(6, int(label_size_base * scale))
                    value_font = (font_family_p, vs, "bold" if bold_val_p else "normal")
                    label_font = (font_family_p, ls, "bold" if bold_lbl_p else "normal")
                    pad_x, pad_y, gap = 14, 10, 6
                    sizes = []
                    for dom_id, label_text in visible_rows:
                        sample = PREVIEW_SAMPLE_VALUES.get(dom_id, "-")
                        if dom_id == "cmdr":
                            sample = (cmdr or saved_state.get("cmdr") or "CMDR")
                        shown_label = label_text if labels_p else ""
                        lw, lh = text_size(shown_label, label_font)
                        vw, vh = text_size(sample, value_font)
                        sizes.append((dom_id, shown_label, sample, lw + (10 if labels_p else 0) + vw, max(lh, vh)))
                    placed = []
                    if layout_p == "horizontal":
                        max_inner = canvas_w - 20 - pad_x * 2
                        gx = 24
                        x = y = line_h = widest = 0
                        for item in sizes:
                            w, h = item[3], item[4]
                            if x > 0 and x + w > max_inner:
                                y += line_h + gap
                                x = line_h = 0
                            placed.append((x, y))
                            x += w + gx
                            line_h = max(line_h, h)
                            widest = max(widest, x - gx)
                        bw = widest + pad_x * 2
                        bh = y + line_h + pad_y * 2
                    else:
                        y = 0
                        for item in sizes:
                            placed.append((0, y))
                            y += item[4] + gap
                        bw = max(x[3] for x in sizes) + pad_x * 2
                        bh = y - gap + pad_y * 2
                    return sizes, bw, bh, value_font, label_font, pad_x, pad_y, gap, placed

                scale = 1.0
                result = layout(scale)
                for _ in range(6):
                    _s, bw, bh = result[0], result[1], result[2]
                    if bw <= canvas_w - 20 and bh <= canvas_h - 20:
                        break
                    scale *= max(0.35, min((canvas_w - 20) / bw, (canvas_h - 20) / bh) * 0.97)
                    result = layout(scale)
                row_sizes, box_w, box_h, value_font, label_font, pad_x, pad_y, gap, placed = result

                box_x = max(10, (canvas_w - box_w) / 2)
                box_y = max(10, (canvas_h - box_h) / 2)

                if bg_enabled_p:
                    br, bgc, bb = hex_to_rgb(bg_color_p)
                    alpha = bg_opacity_p / 100
                    blended = tuple(round(c * alpha + b * (1 - alpha)) for c, b in zip((br, bgc, bb), backdrop))
                    preview_canvas.create_rectangle(box_x, box_y, box_x + box_w, box_y + box_h,
                                                    fill="#%02x%02x%02x" % blended, outline="")

                for (dom_id, shown_label, sample, row_w, row_h), (off_x, off_y) in zip(row_sizes, placed):
                    lx, ly = box_x + pad_x + off_x, box_y + pad_y + off_y + row_h / 2
                    vx = lx
                    if shown_label:
                        preview_canvas.create_text(lx, ly, text=shown_label, anchor="w", fill=label_color_p, font=label_font)
                        lw, _lh = text_size(shown_label, label_font)
                        vx = lx + lw + 10
                    if shadow_p:
                        preview_canvas.create_text(vx + 1, ly + 1, text=sample, anchor="w", fill="#000000", font=value_font)
                    preview_canvas.create_text(vx, ly, text=sample, anchor="w", fill=font_color_p, font=value_font)
            except Exception as e:
                log(f"Preview error: {e}")

        for _key, _var in vars_cfg.items():
            _var.trace_add("write", redraw_preview)
        redraw_preview()

        nb.Label(main_frame, text=f"{plugin_name} v{PLUGIN_VERSION}", font=("Helvetica", 7)).grid(
            row=2, column=0, sticky="e", padx=10, pady=(2, 6))
        return main_frame

    except Exception as e:
        log(f"UI Error: {e}")
        return None


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    global current_settings
    try:
        raw = {key: var.get() for key, var in vars_cfg.items()}
        new_cfg = sanitize_settings({**current_settings, **raw})
        old_srv = (current_settings.get("http_server"), current_settings.get("http_port"))
        save_settings(new_cfg)
        with _lock:
            current_settings = new_cfg
        generate_html()
        update_hud_file(force=True)
        if (new_cfg.get("http_server"), new_cfg.get("http_port")) != old_srv or (new_cfg["http_server"] and _httpd is None):
            start_server()
    except Exception as e:
        log(f"prefs_changed error: {e}")


def _count_cargo(state: Dict[str, Any]) -> Optional[int]:
    cargo = state.get("Cargo")
    if cargo is None:
        return None
    try:
        return int(sum(cargo.values()))
    except Exception:
        return None


def journal_entry(cmdr: str, is_beta: bool, system: str, station: str,
                  entry: Dict[str, Any], state: Dict[str, Any]):
    try:
        with _lock:
            _handle_journal_entry(cmdr, system, station, entry, state)
        update_hud_file()
    except Exception as e:
        log(f"journal_entry error: {e}")
    return None


def _handle_journal_entry(cmdr, system, station, entry, state):
    global _ts_seen, _burst_until, _last_target, _lock_lost_epoch, _last_reward_kill_epoch, _last_merit_kill_epoch
    s = saved_state
    if cmdr:
        s["cmdr"] = cmdr
    if system:
        s["system"] = system
    if station:
        s["station"] = station

    body_val = state.get("Body")
    if body_val:
        s["body"] = body_val

    ship_name = state.get("ShipName", "")
    ship_type = state.get("ShipType", "")
    s["ship"] = ship_name if ship_name else str(ship_type or "").upper()

    credits = state.get("Credits")
    if isinstance(credits, (int, float)):
        s["credits"] = int(credits)

    cargo_now = _count_cargo(state)
    if cargo_now is not None:
        s["cargo_count"] = cargo_now

    event_type = safe_lower(entry.get("event"))
    ts = str(entry.get("timestamp") or "")
    t = _epoch(ts)
    is_replay = False
    if ts:
        last = s["last_event_ts"]
        if ts < last:
            is_replay = True
        elif ts == last:
            _ts_seen += 1
            if ts == _replay_ts and _ts_seen <= _replay_n:
                is_replay = True
            else:
                s["last_event_ts_n"] += 1
        else:
            s["last_event_ts"] = ts
            s["last_event_ts_n"] = 1
            _ts_seen = 1
    count_it = not is_replay

    if event_type in ("marketsell", "buycargo", "sellcargo", "marketbuy"):
        s["effective_mode"] = "trade"
    elif event_type in ("miningrefined", "prospectedasteroid", "launchdrone"):
        s["effective_mode"] = "mining"
    elif event_type in ("bounty", "factionkillbond", "capshipbond", "pvpkill", "underattack"):
        s["effective_mode"] = "combat"
    elif event_type in ("scan", "scanorganic", "fsdjump", "saascancomplete", "fssdiscoveryscan"):
        s["effective_mode"] = "exploration"

    if event_type in ("location", "fsdjump"):
        pos = entry.get("StarPos")
        if pos and len(pos) == 3:
            s["distance_sol"] = math.sqrt(pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2)
    if event_type in ("approachbody", "supercruiseexit", "location", "fsdjump") and entry.get("Body"):
        s["body"] = entry["Body"]
    elif event_type in ("leavebody", "supercruiseentry", "startjump"):
        s["body"] = "Unknown"

    if event_type == "loadout":
        s["cargo_capacity"] = int(entry.get("CargoCapacity", 0) or 0)

    if event_type == "docked":
        s["station"] = station or entry.get("StationName", s["station"])
        s["last_docked_ts"] = entry.get("timestamp", utc_now_str())
        save_totals()
    elif event_type == "undocked":
        s["station"] = "Deep Space"

    elif event_type == "fsdjump":
        s["station"] = "Deep Space"
        if count_it:
            s["session_jumps"] += 1
            s["session_jump_dist"] += float(entry.get("JumpDist", 0) or 0)
        if s["next_target"] and safe_lower(entry.get("StarSystem")) == safe_lower(s["next_target"]):
            s["next_target"] = ""
            s["next_remaining"] = 0
        save_totals()

    elif event_type == "fsdtarget":
        s["next_target"] = str(entry.get("Name", "") or "")
        s["next_remaining"] = int(entry.get("RemainingJumpsInRoute", 0) or 0)
    elif event_type == "navrouteclear":
        s["next_target"] = ""
        s["next_remaining"] = 0

    elif event_type == "scan":
        register_scan_unsold(entry)
        key = (entry.get("SystemAddress"), entry.get("BodyID"), entry.get("BodyName"))
        if count_it and key not in _seen_bodies and entry.get("ScanType") != "NavBeaconDetail":
            _seen_bodies.add(key)
            s["scanned_bodies"] += 1
            if entry.get("WasDiscovered") is False:
                s["first_discoveries"] += 1
        save_totals()

    elif event_type == "saascancomplete":
        key = (entry.get("SystemAddress"), entry.get("BodyID"), entry.get("BodyName"))
        if count_it and key not in _seen_mapped:
            _seen_mapped.add(key)
            s["mapped_bodies"] += 1
            save_totals()

    elif event_type == "scanorganic":
        if safe_lower(entry.get("ScanType")) in ("analyse", "analyze", "analysis"):
            register_bio_unsold(entry)
            save_totals()

    elif event_type in ("multisellexplorationdata", "sellexplorationdata"):
        earnings = entry.get("TotalEarnings", (entry.get("BaseValue", 0) or 0) + (entry.get("Bonus", 0) or 0))
        if count_it:
            s["exploration_session"] += int(earnings or 0)
        reset_unsold_exploration()
        save_totals()

    elif event_type == "sellorganicdata":
        earnings = sum((item.get("Value", 0) or 0) + (item.get("Bonus", 0) or 0) for item in entry.get("BioData", []))
        if count_it:
            s["exobiology_session"] += int(earnings)
        reset_unsold_bio()
        save_totals()

    elif event_type == "marketsell":
        count = int(entry.get("Count", 0) or 0)
        total = int(entry.get("TotalSale", 0) or 0)
        avg = entry.get("AvgPricePaid", 0) or 0
        ckey = norm_commodity(entry.get("Type"))
        held = s["mining_by_commodity"].get(ckey, 0)
        mined_part = min(count, held)
        if avg == 0 and ckey in MINEABLE_COMMODITIES:
            mined_part = count
        mining_revenue = int(round(total * mined_part / count)) if count > 0 else 0
        trade_profit = max(0, (total - mining_revenue) - avg * (count - mined_part))
        if count_it:
            if mined_part > 0:
                left = held - mined_part
                if left > 0:
                    s["mining_by_commodity"][ckey] = left
                else:
                    s["mining_by_commodity"].pop(ckey, None)
                s["mining_session_earnings"] += mining_revenue
            s["trade_session_profit"] += int(trade_profit)
            save_totals()
        if mined_part > 0:
            s["effective_mode"] = "mining"

    elif event_type in ("jettisoncargo", "ejectcargo"):
        ckey = norm_commodity(entry.get("Type"))
        if count_it and ckey in s["mining_by_commodity"]:
            left = s["mining_by_commodity"][ckey] - int(entry.get("Count", 0) or 0)
            if left > 0:
                s["mining_by_commodity"][ckey] = left
            else:
                s["mining_by_commodity"].pop(ckey, None)
            save_totals()

    elif event_type == "cargo":
        if entry.get("Count") is not None and cargo_now is None:
            s["cargo_count"] = int(entry.get("Count", 0) or 0)
        inventory = entry.get("Inventory")
        if count_it and isinstance(inventory, list) and entry.get("Vessel", "Ship") == "Ship":
            held_map: Dict[str, int] = {}
            for item in inventory:
                if isinstance(item, dict):
                    held_map[norm_commodity(item.get("Name"))] = int(item.get("Count", 0) or 0)
            for ckey in list(s["mining_by_commodity"]):
                if held_map.get(ckey, 0) < s["mining_by_commodity"][ckey]:
                    if held_map.get(ckey, 0) > 0:
                        s["mining_by_commodity"][ckey] = held_map[ckey]
                    else:
                        s["mining_by_commodity"].pop(ckey, None)

    elif event_type == "miningrefined":
        ckey = norm_commodity(entry.get("Type")) or "ore"
        name = str(entry.get("Type_Localised") or ckey).title()
        if count_it:
            s["mining_session_tons"] += 1
            by = s["mining_by_commodity"]
            by[ckey] = by.get(ckey, 0) + 1
            s["mining_names"][ckey] = name
            s["last_mined_commodity"] = name
            save_totals()

    elif event_type in ("bounty", "factionkillbond", "capshipbond"):
        reward = entry.get("TotalReward", entry.get("Reward", 0)) or 0
        if count_it:
            s["combat_session_bounties"] += int(reward)
            if t is not None and _last_merit_kill_epoch is not None and abs(t - _last_merit_kill_epoch) <= KILL_DEDUPE_WINDOW:
                _last_merit_kill_epoch = None
            else:
                s["combat_session_kills"] += 1
            if t is not None:
                _last_reward_kill_epoch = t
            save_totals()

    elif event_type == "pvpkill":
        if count_it:
            s["combat_session_kills"] += 1
            save_totals()

    elif event_type == "powerplay":
        if count_it:
            apply_powerplay_snapshot(entry)
            save_totals()

    elif event_type == "powerplaymerits":
        if count_it:
            in_burst = apply_merit_award(entry, t)

            if (not in_burst and t is not None and _lock_lost_epoch is not None
                    and 0 <= t - _lock_lost_epoch <= KILL_MERIT_WINDOW):
                lost_at, _lock_lost_epoch = _lock_lost_epoch, None
                if _last_reward_kill_epoch is not None and abs(lost_at - _last_reward_kill_epoch) <= KILL_DEDUPE_WINDOW:
                    _last_reward_kill_epoch = None
                else:
                    s["combat_session_kills"] += 1
                    _last_merit_kill_epoch = t
                    s["effective_mode"] = "combat"
            save_totals()

    elif event_type == "missioncompleted":
        if count_it and t is not None:
            _mission_marks.append(t)
            _burst_until = t + MISSION_BURST_SECONDS

    elif event_type == "shiptargeted":
        if entry.get("TargetLocked") is False:
            if _last_target is not None and t is not None:
                _lock_lost_epoch = t
            _last_target = None
        elif entry.get("TargetLocked") is True:
            _last_target = {"ship": entry.get("Ship"), "stage": entry.get("ScanStage")}
            _lock_lost_epoch = None

    elif event_type == "died":
        reset_unsold_all()
        if count_it:
            s["deaths"] += 1
            s["mining_by_commodity"].clear()
        save_totals()

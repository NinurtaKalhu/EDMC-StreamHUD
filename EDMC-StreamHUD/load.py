import os
import sys
import json
import math
import time
import datetime
import tkinter as tk
from tkinter import colorchooser, ttk
from typing import Optional, Dict, Any

import myNotebook as nb

plugin_name = "EDMC-StreamHUD"

PLUGIN_VERSION = "1.0.0"
__version__ = PLUGIN_VERSION

output_dir = os.path.join(os.path.expanduser("~"), "Documents", "EDMC-StreamHUD")
settings_file = os.path.join(output_dir, "settings.json")
totals_file = os.path.join(output_dir, "totals_and_state.json")
txt_file = os.path.join(output_dir, "HUD.txt")
json_file = os.path.join(output_dir, "HUD.json")
html_file = os.path.join(output_dir, "HUD.html")

FONT_CHOICES = [
    "Segoe UI", "Arial", "Consolas", "Verdana", "Tahoma",
    "Trebuchet MS", "Roboto", "Orbitron", "Courier New",
]

DEFAULT_SETTINGS = {
    "show_cmdr": True,
    "show_time": True,
    "show_system": True,
    "show_body": True,
    "show_station": True,
    "show_distance": True,
    "show_ship": True,
    "show_risk": True,
    "show_exploration": True,
    "show_exobiology": True,

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
    "layout": "vertical",
}

NUMERIC_KEYS = {"font_size", "label_font_size", "bg_opacity"}

FIELD_ROWS = [
    ("cmdr", "CMDR"),
    ("time", "Time"),
    ("system", "System"),
    ("body", "Body"),
    ("station", "Station"),
    ("distance", "Distance to Sol"),
    ("ship", "Ship"),
    ("unsold_exp", "Unsold Discoveries"),
    ("unsold_bio", "Unsold Bio"),
    ("exploration_session", "Exploration Earnings"),
    ("exobiology_session", "Exobiology Earnings"),
]

FIELD_VISIBILITY_KEY = {
    "cmdr": "show_cmdr",
    "time": "show_time",
    "system": "show_system",
    "body": "show_body",
    "station": "show_station",
    "distance": "show_distance",
    "ship": "show_ship",
    "unsold_exp": "show_risk",
    "unsold_bio": "show_risk",
    "exploration_session": "show_exploration",
    "exobiology_session": "show_exobiology",
}

PREVIEW_SAMPLE_VALUES = {
    "cmdr": "Ninurta Kalhu",
    "time": "2h 14m",
    "system": "Shinrarta Dezhra",
    "body": "Selene Jean",
    "station": "Jameson Memorial",
    "distance": "37.4 Ly",
    "ship": "ANACONDA",
    "unsold_exp": "ELW: 2 | WW: 1",
    "unsold_bio": "5 Sp",
    "exploration_session": "12.450.000 cr",
    "exobiology_session": "3.200.000 cr",
}

saved_state = {
    "cmdr": "",
    "system": "",
    "station": "Deep Space",
    "ship": "",
    "body": "Unknown",
    "distance_sol": 0.0,
    "last_docked_ts": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),

    "exploration_session": 0,
    "exploration_total": 0,
    "exobiology_session": 0,
    "exobiology_total": 0,
    "exobiology_species_session": 0,
    "exobiology_species_total": 0,

    "unsold_elw": 0,
    "unsold_ww": 0,
    "unsold_aw": 0,
    "unsold_bio": 0,
}

current_settings = DEFAULT_SETTINGS.copy()
vars_cfg: Dict[str, Any] = {}


def safe_lower(val: Any) -> str:
    if val is None:
        return ""
    return str(val).lower().strip()


def ensure_dir():
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"[{plugin_name}] Directory error: {e}", file=sys.stderr)


def load_settings() -> dict:
    ensure_dir()
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(data: dict):
    ensure_dir()
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[{plugin_name}] Settings save error: {e}", file=sys.stderr)


def load_totals() -> dict:
    ensure_dir()
    if os.path.exists(totals_file):
        try:
            with open(totals_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_totals():
    ensure_dir()
    try:
        with open(totals_file, "w", encoding="utf-8") as f:
            json.dump({
                "exploration_total": saved_state["exploration_total"],
                "exobiology_total": saved_state["exobiology_total"],
                "exobiology_species_total": saved_state["exobiology_species_total"],
                "unsold_elw": saved_state["unsold_elw"],
                "unsold_ww": saved_state["unsold_ww"],
                "unsold_aw": saved_state["unsold_aw"],
                "unsold_bio": saved_state["unsold_bio"],
                "last_docked_ts": saved_state["last_docked_ts"],
            }, f, indent=2)
    except Exception as e:
        print(f"[{plugin_name}] Totals save error: {e}", file=sys.stderr)


def parse_latest_journals_for_unsold():
    saved_games = os.path.join(
        os.path.expanduser("~"),
        "Saved Games",
        "Frontier Developments",
        "Elite Dangerous")
    if not os.path.exists(saved_games):
        return

    try:
        journals = [os.path.join(saved_games, f) for f in os.listdir(saved_games)
                    if f.startswith("Journal.") and f.endswith(".log")]
        if not journals:
            return

        journals_with_mtime = [(j, os.path.getmtime(j)) for j in journals]
        journals_with_mtime.sort(key=lambda x: x[1])

        current_session_journal = journals_with_mtime[-1][0]
        older_journals = [(j, m) for j, m in journals_with_mtime if j != current_session_journal]

        saved_state["unsold_elw"] = 0
        saved_state["unsold_ww"] = 0
        saved_state["unsold_aw"] = 0
        saved_state["unsold_bio"] = 0

        if not older_journals:
            return

        now = time.time()
        filtered_journals = [(j, m) for j, m in older_journals if now - m < 5 * 86400]

        if not filtered_journals:
            older_sorted = sorted(older_journals, key=lambda x: x[1], reverse=True)
            filtered_journals = older_sorted[:5]

        filtered_journals.sort(key=lambda x: x[1])

        for j_file, _ in filtered_journals:
            with open(j_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        event_type = safe_lower(entry.get('event'))

                        if event_type == 'scan':
                            p_class = safe_lower(entry.get('PlanetClass'))
                            if p_class == 'earthlike body':
                                saved_state["unsold_elw"] += 1
                            elif p_class == 'water world':
                                saved_state["unsold_ww"] += 1
                            elif p_class == 'ammonia world':
                                saved_state["unsold_aw"] += 1
                        elif event_type == 'scanorganic' and safe_lower(entry.get('ScanType')) in ('analyse', 'analyze', 'analysis'):
                            saved_state["unsold_bio"] += 1
                        elif event_type in ('multisellexplorationdata', 'sellexplorationdata'):
                            saved_state["unsold_elw"] = 0
                            saved_state["unsold_ww"] = 0
                            saved_state["unsold_aw"] = 0
                        elif event_type == 'sellorganicdata':
                            saved_state["unsold_bio"] = 0
                        elif event_type == 'died':
                            saved_state["unsold_elw"] = 0
                            saved_state["unsold_ww"] = 0
                            saved_state["unsold_aw"] = 0
                            saved_state["unsold_bio"] = 0
                    except Exception:
                        continue
    except Exception as e:
        print(f"[{plugin_name}] Journal parse error: {e}", file=sys.stderr)


def format_credits(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " cr"


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
        last_dt = datetime.datetime.strptime(saved_state["last_docked_ts"], "%Y-%m-%dT%H:%M:%SZ")
        now_dt = datetime.datetime.utcnow()
        diff = now_dt - last_dt
        if diff.days > 0:
            return f"{diff.days}d {diff.seconds // 3600}h"
        else:
            return f"{diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"
    except Exception:
        return "0h 0m"


def format_exploration_risk() -> str:
    parts = []
    if saved_state["unsold_elw"] > 0:
        parts.append(f"ELW: {saved_state['unsold_elw']}")
    if saved_state["unsold_ww"] > 0:
        parts.append(f"WW: {saved_state['unsold_ww']}")
    if saved_state["unsold_aw"] > 0:
        parts.append(f"AW: {saved_state['unsold_aw']}")
    return " | ".join(parts) if parts else ""


def generate_html():
    ensure_dir()
    cfg = current_settings

    r, g, b = hex_to_rgb(cfg.get("bg_color", "#000000"))
    opacity = max(0, min(100, int(cfg.get("bg_opacity", 50)))) / 100
    bg_css = f"background: rgba({r}, {g}, {b}, {opacity:.2f});" if cfg.get(
        "bg_enabled", True) else "background: transparent;"
    shadow_css = "text-shadow: 0 0 5px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9);" if cfg.get(
        "text_shadow", True) else ""

    weight_value = "700" if cfg.get("font_bold", True) else "400"
    weight_label = "600" if cfg.get("label_bold", True) else "400"

    font_family = cfg.get("font_family", "Segoe UI")
    font_size = int(cfg.get("font_size", 22))
    label_font_size = int(cfg.get("label_font_size", 16))

    font_color = cfg.get("font_color", "#FFFFFF")
    label_color = cfg.get("label_color", "#7FDBFF")

    rows_html = []
    for dom_id, label in FIELD_ROWS:
        rows_html.append(
            f'<div id="row-{dom_id}" class="row">'
            f'<span class="label">{label}</span>'
            f'<span id="{dom_id}" class="value"></span></div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; font-family: "{font_family}", sans-serif; }}
  .hud {{ display: inline-flex; flex-direction: column; gap: 4px; padding: 12px 16px; {bg_css} border-radius: 8px; width: fit-content; }}
  .hud.layout-horizontal {{ flex-direction: row; flex-wrap: wrap; width: 100%; max-width: 100vw; column-gap: 16px; row-gap: 6px; }}
  .row {{ display: none; gap: 10px; align-items: baseline; white-space: nowrap; }}
  .label {{ color: {label_color}; font-weight: {weight_label}; font-size: {label_font_size}px; font-family: "{font_family}", sans-serif; }}
  .value {{ color: {font_color}; font-weight: {weight_value}; font-size: {font_size}px; font-family: "{font_family}", sans-serif; {shadow_css} transition: all 0.2s ease-in-out; }}
</style>
</head>
<body>
  <div class="hud">
    {''.join(rows_html)}
  </div>
  <script>
    async function refreshHud() {{
      try {{
        const res = await fetch('HUD.json?t=' + Date.now(), {{cache: 'no-store'}});
        const data = await res.json();

        const hud = document.querySelector('.hud');
        if (hud) {{
          hud.classList.toggle('layout-horizontal', data.layout === 'horizontal');
        }}

        for (const key in data) {{
          if (key === 'layout') continue;
          const el = document.getElementById(key);
          const row = document.getElementById('row-' + key);
          if (el && row) {{
            if (data[key] === null || data[key] === "HIDE") {{
              row.style.display = 'none';
            }} else {{
              el.textContent = data[key];
              row.style.display = 'flex';
            }}
          }}
        }}
      }} catch (e) {{}}
    }}
    refreshHud();
    setInterval(refreshHud, 1000);
  </script>
</body>
</html>
"""
    try:
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        print(f"[{plugin_name}] HUD.html write error: {e}", file=sys.stderr)


def update_hud_file():
    ensure_dir()
    cfg = current_settings

    exp_risk_str = format_exploration_risk()
    show_exp_risk = cfg.get("show_risk") and bool(exp_risk_str)

    bio_count = saved_state['unsold_bio']
    bio_risk_str = f"{bio_count} Species" if bio_count > 0 else ""
    show_bio_risk = cfg.get("show_risk") and bio_count > 0

    expl_sess = saved_state['exploration_session']
    exo_sess = saved_state['exobiology_session']
    dist_sol = saved_state['distance_sol']
    station_val = saved_state['station']
    body_val = saved_state['body']

    data = {
        "layout": cfg.get("layout", "vertical"),
        "cmdr": saved_state["cmdr"] if (cfg.get("show_cmdr") and saved_state["cmdr"]) else "HIDE",
        "time": calculate_time() if cfg.get("show_time") else "HIDE",
        "system": saved_state["system"] if (cfg.get("show_system") and saved_state["system"]) else "HIDE",
        "body": body_val if (cfg.get("show_body") and body_val and body_val != "Unknown") else "HIDE",
        "station": station_val if (cfg.get("show_station") and station_val and station_val != "Deep Space") else "HIDE",
        "distance": f"{dist_sol:,.1f} Ly" if (cfg.get("show_distance") and dist_sol > 0) else "HIDE",
        "ship": saved_state["ship"] if (cfg.get("show_ship") and saved_state["ship"]) else "HIDE",
        "unsold_exp": exp_risk_str if show_exp_risk else "HIDE",
        "unsold_bio": bio_risk_str if show_bio_risk else "HIDE",
        "exploration_session": format_credits(expl_sess) if (cfg.get("show_exploration") and expl_sess > 0) else "HIDE",
        "exobiology_session": format_credits(exo_sess) if (cfg.get("show_exobiology") and exo_sess > 0) else "HIDE",
    }

    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[{plugin_name}] HUD.json write error: {e}", file=sys.stderr)


def plugin_start3(plugin_dir: str) -> str:
    global current_settings
    ensure_dir()
    current_settings = load_settings()

    totals = load_totals()
    saved_state["exploration_total"] = totals.get("exploration_total", 0)
    saved_state["exobiology_total"] = totals.get("exobiology_total", 0)
    saved_state["exobiology_species_total"] = totals.get("exobiology_species_total", 0)

    if totals.get("last_docked_ts"):
        saved_state["last_docked_ts"] = totals.get("last_docked_ts")

    parse_latest_journals_for_unsold()

    generate_html()
    update_hud_file()
    print(f"[{plugin_name}] v{PLUGIN_VERSION} - Compact Streamer Module active.")
    return f"{plugin_name} v{PLUGIN_VERSION}"


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

        notebook.add(tab_data, text="Data and Content")
        notebook.add(tab_style, text="Appearance and Style")

        td_row = 0

        def next_td_row():
            nonlocal td_row
            td_row += 1
            return td_row

        nb.Label(tab_data, text="Identity Information", font=("Helvetica", 9, "bold")).grid(
            row=td_row, column=0, columnspan=2, sticky=tk.W, pady=(8, 2), padx=10
        )

        identity_checkboxes = [
            ("show_cmdr", "Commander Name (CMDR)"),
            ("show_system", "Current System"),
            ("show_body", "Current Body (Planet/Star)"),
            ("show_station", "Station Name"),
            ("show_ship", "Ship Name / Model"),
        ]
        for key, label_text in identity_checkboxes:
            vars_cfg[key] = tk.BooleanVar(value=cfg.get(key, True))
            nb.Checkbutton(tab_data, text=label_text, variable=vars_cfg[key]).grid(
                row=next_td_row(), column=0, columnspan=2, sticky=tk.W, pady=1, padx=10
            )

        nb.Label(tab_data, text="Progress and Risk Information", font=("Helvetica", 9, "bold")).grid(
            row=next_td_row(), column=0, columnspan=2, sticky=tk.W, pady=(10, 2), padx=10
        )

        progress_checkboxes = [
            ("show_time", "Session / Trip Time"),
            ("show_distance", "Distance to Sol"),
            ("show_risk", "Unsold Discoveries & Biology Risks"),
            ("show_exploration", "Exploration Earnings (Session)"),
            ("show_exobiology", "Exobiology Earnings (Session)"),
        ]
        for key, label_text in progress_checkboxes:
            vars_cfg[key] = tk.BooleanVar(value=cfg.get(key, True))
            nb.Checkbutton(tab_data, text=label_text, variable=vars_cfg[key]).grid(
                row=next_td_row(), column=0, columnspan=2, sticky=tk.W, pady=1, padx=10
            )

        ttk.Separator(tab_data, orient="horizontal").grid(
            row=next_td_row(), column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4)
        )

        def reset_session_action():
            saved_state["exploration_session"] = 0
            saved_state["exobiology_session"] = 0
            saved_state["last_docked_ts"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            save_totals()
            update_hud_file()

        nb.Button(tab_data, text="Reset Session Stats & Timer", command=reset_session_action).grid(
            row=next_td_row(), column=0, columnspan=2, sticky=tk.W, padx=10, pady=4
        )

        ts_row = 0

        def next_ts_row():
            nonlocal ts_row
            ts_row += 1
            return ts_row

        nb.Label(tab_style, text="Layout & Style Settings", font=("Helvetica", 9, "bold")).grid(
            row=ts_row, column=0, columnspan=3, sticky=tk.W, pady=(8, 4), padx=10
        )

        layout_var = tk.StringVar(value=cfg.get("layout", "vertical"))
        vars_cfg["layout"] = layout_var
        r = next_ts_row()
        nb.Label(tab_style, text="Layout Direction:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(
            tab_style,
            layout_var,
            layout_var.get(),
            "vertical",
            "horizontal").grid(
            row=r,
            column=1,
            sticky=tk.W)

        bg_enabled_var = tk.BooleanVar(value=cfg.get("bg_enabled", True))
        vars_cfg["bg_enabled"] = bg_enabled_var
        nb.Checkbutton(tab_style, text="Enable Background Box", variable=bg_enabled_var).grid(
            row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10
        )

        def add_color_row(parent_tab, label_text, key):
            color_var = tk.StringVar(value=cfg.get(key, DEFAULT_SETTINGS[key]))
            vars_cfg[key] = color_var
            r = next_ts_row()
            nb.Label(parent_tab, text=label_text).grid(row=r, column=0, sticky=tk.W, padx=10)
            nb.EntryMenu(parent_tab, textvariable=color_var, width=10).grid(row=r, column=1, sticky=tk.W)
            nb.Button(
                parent_tab,
                text="Choose",
                command=lambda v=color_var: v.set(
                    colorchooser.askcolor(
                        color=v.get() or "#FFFFFF",
                        parent=main_frame)[1] or v.get())).grid(
                row=r,
                column=2,
                sticky=tk.W,
                padx=(
                    4,
                    10))

        add_color_row(tab_style, "Background Color:", "bg_color")

        opacity_var = tk.StringVar(value=str(cfg.get("bg_opacity", 50)))
        vars_cfg["bg_opacity"] = opacity_var
        r = next_ts_row()
        nb.Label(tab_style, text="Background Opacity (0-100):").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.EntryMenu(tab_style, textvariable=opacity_var, width=6).grid(row=r, column=1, sticky=tk.W)

        shadow_var = tk.BooleanVar(value=cfg.get("text_shadow", True))
        vars_cfg["text_shadow"] = shadow_var
        nb.Checkbutton(tab_style, text="Enable Text Shadow", variable=shadow_var).grid(
            row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10
        )

        ttk.Separator(tab_style, orient="horizontal").grid(
            row=next_ts_row(), column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 4)
        )

        nb.Label(tab_style, text="Font & Typography", font=("Helvetica", 9, "bold")).grid(
            row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=(0, 4), padx=10
        )

        font_var = tk.StringVar(value=cfg.get("font_family", "Segoe UI"))
        vars_cfg["font_family"] = font_var
        r = next_ts_row()
        nb.Label(tab_style, text="Font Family:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.OptionMenu(tab_style, font_var, font_var.get(), *
                      (FONT_CHOICES if font_var.get() in FONT_CHOICES else [font_var.get()] +
                       FONT_CHOICES)).grid(row=r, column=1, sticky=tk.W)

        size_var = tk.StringVar(value=str(cfg.get("font_size", 22)))
        vars_cfg["font_size"] = size_var
        r = next_ts_row()
        nb.Label(tab_style, text="Value Font Size:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.EntryMenu(tab_style, textvariable=size_var, width=6).grid(row=r, column=1, sticky=tk.W)

        label_size_var = tk.StringVar(value=str(cfg.get("label_font_size", 16)))
        vars_cfg["label_font_size"] = label_size_var
        r = next_ts_row()
        nb.Label(tab_style, text="Label Font Size:").grid(row=r, column=0, sticky=tk.W, padx=10)
        nb.EntryMenu(tab_style, textvariable=label_size_var, width=6).grid(row=r, column=1, sticky=tk.W)

        bold_val_var = tk.BooleanVar(value=cfg.get("font_bold", True))
        vars_cfg["font_bold"] = bold_val_var
        nb.Checkbutton(tab_style, text="Bold Values", variable=bold_val_var).grid(
            row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10
        )

        bold_lbl_var = tk.BooleanVar(value=cfg.get("label_bold", True))
        vars_cfg["label_bold"] = bold_lbl_var
        nb.Checkbutton(tab_style, text="Bold Labels", variable=bold_lbl_var).grid(
            row=next_ts_row(), column=0, columnspan=3, sticky=tk.W, pady=1, padx=10
        )

        add_color_row(tab_style, "Value Color:", "font_color")
        add_color_row(tab_style, "Label Color:", "label_color")

        preview_container = nb.Frame(main_frame)
        preview_container.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 5))

        nb.Label(preview_container, text="Live Preview", font=("Helvetica", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 2)
        )

        preview_canvas = tk.Canvas(
            preview_container,
            width=480,
            height=160,
            bg="#3a3a3a",
            highlightthickness=1,
            highlightbackground="#888888")
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

                font_family_p = gv("font_family", "Segoe UI")
                try:
                    font_size_p = int(gv("font_size", 22))
                except (TypeError, ValueError):
                    font_size_p = 22
                try:
                    label_size_p = int(gv("label_font_size", 16))
                except (TypeError, ValueError):
                    label_size_p = 16

                bold_val_p = bool(gv("font_bold", True))
                bold_lbl_p = bool(gv("label_bold", True))
                font_color_p = gv("font_color", "#FFFFFF") or "#FFFFFF"
                label_color_p = gv("label_color", "#7FDBFF") or "#7FDBFF"
                shadow_p = bool(gv("text_shadow", True))
                bg_enabled_p = bool(gv("bg_enabled", True))
                bg_color_p = gv("bg_color", "#000000") or "#000000"
                try:
                    bg_opacity_p = max(0, min(100, int(gv("bg_opacity", 50))))
                except (TypeError, ValueError):
                    bg_opacity_p = 50
                layout_p = gv("layout", "vertical")

                canvas_w = int(str(preview_canvas["width"]))
                canvas_h = int(str(preview_canvas["height"]))
                backdrop = (58, 58, 58)

                preview_canvas.create_rectangle(0, 0, canvas_w, canvas_h, fill="#3a3a3a", outline="")
                preview_canvas.create_text(
                    8,
                    canvas_h - 8,
                    anchor="sw",
                    text="(sample background)",
                    fill="#888888",
                    font=(
                        "Segoe UI",
                        8))

                visible_rows = []
                for dom_id, label_text in FIELD_ROWS:
                    if gv(FIELD_VISIBILITY_KEY[dom_id], True):
                        visible_rows.append((dom_id, label_text))

                if not visible_rows:
                    preview_canvas.create_text(
                        canvas_w / 2,
                        canvas_h / 2,
                        text="(no fields selected)",
                        fill="#aaaaaa",
                        font=(
                            "Segoe UI",
                            10))
                    return

                pad_x, pad_y, gap = 14, 10, 6
                value_font = (font_family_p, font_size_p, "bold" if bold_val_p else "normal")
                label_font = (font_family_p, label_size_p, "bold" if bold_lbl_p else "normal")

                def text_size(text, font):
                    tmp = preview_canvas.create_text(-1000, -1000, text=text, font=font, anchor="nw")
                    bbox = preview_canvas.bbox(tmp)
                    preview_canvas.delete(tmp)
                    return (bbox[2] - bbox[0], bbox[3] - bbox[1]) if bbox else (0, 0)

                row_sizes = []
                for dom_id, label_text in visible_rows:
                    sample = PREVIEW_SAMPLE_VALUES.get(dom_id, "-")
                    lw, lh = text_size(label_text, label_font)
                    vw, vh = text_size(sample, value_font)
                    row_sizes.append((dom_id, label_text, sample, lw + 10 + vw, max(lh, vh)))

                if layout_p == "horizontal":
                    box_w = sum(r2[3] for r2 in row_sizes) + gap * (len(row_sizes) - 1) + pad_x * 2
                    box_h = max(r2[4] for r2 in row_sizes) + pad_y * 2
                else:
                    box_w = max(r2[3] for r2 in row_sizes) + pad_x * 2
                    box_h = sum(r2[4] for r2 in row_sizes) + gap * (len(row_sizes) - 1) + pad_y * 2

                box_x = max(10, (canvas_w - box_w) / 2)
                box_y = max(10, (canvas_h - box_h) / 2)

                if bg_enabled_p:
                    br, bgc, bb = hex_to_rgb(bg_color_p)
                    alpha = bg_opacity_p / 100
                    blended = tuple(round(c * alpha + b * (1 - alpha))
                                    for c, b in zip((br, bgc, bb), backdrop))
                    preview_canvas.create_rectangle(
                        box_x,
                        box_y,
                        box_x +
                        box_w,
                        box_y +
                        box_h,
                        fill="#%02x%02x%02x" %
                        blended,
                        outline="")

                cursor_x, cursor_y = box_x + pad_x, box_y + pad_y
                for dom_id, label_text, sample, row_w, row_h in row_sizes:
                    lx, ly = cursor_x, cursor_y + row_h / 2
                    preview_canvas.create_text(lx, ly, text=label_text, anchor="w",
                                               fill=label_color_p, font=label_font)
                    lw, _lh = text_size(label_text, label_font)
                    vx = lx + lw + 10

                    if shadow_p:
                        preview_canvas.create_text(
                            vx + 1, ly + 1, text=sample, anchor="w", fill="#000000", font=value_font)
                    preview_canvas.create_text(vx, ly, text=sample, anchor="w",
                                               fill=font_color_p, font=value_font)

                    if layout_p == "horizontal":
                        cursor_x += row_w + gap
                    else:
                        cursor_y += row_h + gap

            except Exception as e:
                print(f"[{plugin_name}] Preview error: {e}", file=sys.stderr)

        for _key, _var in vars_cfg.items():
            _var.trace_add("write", redraw_preview)

        redraw_preview()

        nb.Label(main_frame, text=f"{plugin_name} v{PLUGIN_VERSION}", font=("Helvetica", 7)).grid(
            row=2, column=0, sticky="e", padx=10, pady=(2, 6)
        )

        return main_frame

    except Exception as e:
        print(f"[{plugin_name}] UI Error: {e}", file=sys.stderr)
        return None


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    global current_settings
    try:
        new_cfg = {}
        for key, var in vars_cfg.items():
            val = var.get()
            if key in NUMERIC_KEYS:
                try:
                    val = int(val)
                except ValueError:
                    val = DEFAULT_SETTINGS[key]
            new_cfg[key] = val
        save_settings(new_cfg)
        current_settings = new_cfg
        generate_html()
        update_hud_file()
    except Exception as e:
        print(f"[{plugin_name}] prefs_changed error: {e}", file=sys.stderr)


def journal_entry(cmdr: str, is_beta: bool, system: str, station: str,
                  entry: Dict[str, Any], state: Dict[str, Any]):
    try:
        if cmdr:
            saved_state["cmdr"] = cmdr
        if system:
            saved_state["system"] = system

        if station:
            saved_state["station"] = station

        body_val = state.get('Body')
        if body_val:
            saved_state["body"] = body_val

        ship_name = state.get('ShipName', '')
        ship_type = state.get('ShipType', '')
        saved_state["ship"] = ship_name if ship_name else str(ship_type).upper()

        event_type = safe_lower(entry.get('event'))

        if event_type in ('location', 'fsdjump'):
            pos = entry.get('StarPos')
            if pos and len(pos) == 3:
                dist = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)
                saved_state['distance_sol'] = dist

        if event_type == 'docked':
            saved_state['station'] = station
            saved_state['last_docked_ts'] = entry.get(
                'timestamp', datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
            save_totals()
        elif event_type == 'undocked':
            saved_state['station'] = "Deep Space"
        elif event_type == 'loadgame':
            pass

        elif event_type == 'scan':
            planet_class = safe_lower(entry.get('PlanetClass'))
            if planet_class == 'earthlike body':
                saved_state["unsold_elw"] += 1
            elif planet_class == 'water world':
                saved_state["unsold_ww"] += 1
            elif planet_class == 'ammonia world':
                saved_state["unsold_aw"] += 1
            save_totals()

        elif event_type == 'scanorganic':
            if safe_lower(entry.get('ScanType')) in ('analyse', 'analyze', 'analysis'):
                saved_state["unsold_bio"] += 1
                save_totals()

        elif event_type in ('multisellexplorationdata', 'sellexplorationdata'):
            earnings = entry.get('TotalEarnings', entry.get('BaseValue', 0) + entry.get('Bonus', 0))
            saved_state["exploration_session"] += earnings
            saved_state["exploration_total"] += earnings
            saved_state["unsold_elw"] = 0
            saved_state["unsold_ww"] = 0
            saved_state["unsold_aw"] = 0
            save_totals()

        elif event_type == 'sellorganicdata':
            bio_data = entry.get('BioData', [])
            earnings = sum(item.get('Value', 0) + item.get('Bonus', 0) for item in bio_data)
            saved_state["exobiology_session"] += earnings
            saved_state["exobiology_total"] += earnings
            saved_state["unsold_bio"] = 0
            save_totals()

        elif event_type == 'died':
            saved_state["unsold_elw"] = 0
            saved_state["unsold_ww"] = 0
            saved_state["unsold_aw"] = 0
            saved_state["unsold_bio"] = 0
            save_totals()

        update_hud_file()
    except Exception as e:
        print(f"[{plugin_name}] journal_entry error: {e}", file=sys.stderr)
    return None

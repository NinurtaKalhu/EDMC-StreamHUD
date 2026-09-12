#### EDMC-StreamHUD
A lightweight, real-time EDMC plugin for OBS streamers, designed specifically for explorers and exobiologists to track session stats, earnings, and un-sold discovery risks.

### EDMC-StreamHUD

A lightweight, real-time Elite Dangerous Market Connector (EDMC) plugin and OBS overlay designed specifically for explorers, exobiologists, and content creators. It tracks your live navigation metrics, session earnings, and un-sold discovery risks, feeding them instantly into OBS via a clean, customizable HTML overlay.

---

## Features

* **Live Navigation & Status:** Tracks your current Commander name, system, planetary body, station, ship model, and distance to Sol.
* **Exploration & Exobiology Risk Tracker:** Monitors un-sold Earth-like Worlds (ELW), Water Worlds (WW), Ammonia Worlds (AW), and exobiology species counts to keep your risk visible on stream.
* **Earnings Counter:** Real-time session tracking for exploration data sales and exobiology payouts.
* **Session Timer:** Automatically tracks elapsed time since your last dock or session reset.
* **Fully Customizable UI:** Tweak fonts, sizes, text colors, background boxes, opacity, text shadows, and switch between **Vertical** or **Horizontal** layouts directly from EDMC's settings panel.
* **Non-Blocking OBS Integration:** Writes local JSON and HTML updates to your Documents folder, powering a zero-lag OBS Browser Source.

---

## Installation

1. Download or clone this repository.
2. Place the `EDMC-StreamHUD` folder into your EDMC plugins directory:
* **Windows:** `%LOCALAPPDATA%\EDMarketConnector\plugins\`


3. Restart EDMC.

---

## OBS Studio Setup

1. Open **OBS Studio**.
2. In your Scenes panel, click **+** and add a **Browser Source**.
3. Name it `EDMC StreamHUD` (or whatever you prefer).
4. Configure the source properties:
* Check **Local file**.
* Click **Browse** and select `HUD.html` located in:
`C:\Users\<YourUsername>\Documents\EDMC_OBS_Texts\HUD.html`
* Set **Width**: `400` (adjust based on your layout)
* Set **Height**: `800` (adjust as needed)


5. Click **OK**. The HUD will update in real-time as you play Elite Dangerous.

---

## Configuration

You can customize the appearance and displayed fields directly inside **EDMC -> File -> Settings -> EDMC-StreamHUD**:

* Toggle individual fields on/off (CMDR name, system, ship, risks, earnings, etc.).
* Choose layout orientation (`vertical` or `horizontal`).
* Customize font families, pixel sizes, and bold weights.
* Pick custom hex colors for labels and values, adjust background box opacity, and toggle text drop-shadows.
* Reset session stats and timers with a single click.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

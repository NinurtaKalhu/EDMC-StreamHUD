# EDMC-StreamHUD

>* ### A highly customizable [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector) plugin designed for content creators and streamers. It generates a live, auto-refreshing HTML overlay for OBS Studio, displaying real-time exploration data, exobiology metrics, and journey progress without the need for complex window captures.

## Key Features

* **Live Journey Tracking:** Displays CMDR Name, Current System, Body, Station, Ship, and Distance to Sol.
* **Session Timer:** Automatically tracks trip time since you last docked at a station.
* **Risk & Unsold Data Tracker:** Monitors your unsent exploration data (Earth-Like Worlds, Water Worlds, Ammonia Worlds) and unlogged Exobiology species to highlight the "risk" you are carrying.
* **Earnings Monitor:** Calculates your estimated session earnings for both Exploration and Exobiology.
* **Automatic Recovery:** Parses recent player journals upon startup to recover unsold data counts in case of crashes or restarts.
* **In-App Customization:** Features a tabbed settings interface directly inside EDMC with a **Live Preview** canvas so you can design your HUD without leaving the app.

## Installation

1. Download the latest release from the repository.
2. Open EDMC, go to **File** > **Settings** > **Plugins**.
3. Click the **Open** button to open the `plugins` folder.
4. Extract the downloaded `EDMC-StreamHUD` folder into this directory.
5. Restart EDMC.

## OBS Studio Setup

The plugin automatically generates the required overlay files in your `Documents/EDMC-StreamHUD` folder.

1. Open OBS Studio and add a new **Browser** source to your scene.
2. Check the **Local file** box.
3. Click **Browse** and navigate to your Documents folder: `Documents\EDMC-StreamHUD\HUD.html`.
4. Set the **Width** and **Height** to fit your chosen layout (e.g., `800` width and `400` height).
5. Leave the default custom CSS or clear it (the plugin manages its own styling).
6. Click **OK**. The overlay will now automatically update every second while EDMC is running.

## Configuration & Customization

Open EDMC **Settings** and navigate to the **EDMC-StreamHUD** tab. The interface is divided into two sections:

### Data and Content
* Toggle exactly which statistics you want to display on your stream.
* Use the **Reset Session Stats & Timer** button when you start a new expedition to zero out your session earnings and restart the trip timer.

### Appearance and Style
* **Layout:** Choose between a vertical list or a horizontal ticker.
* **Background:** Enable/disable the background box, pick a custom HEX color, and adjust opacity.
* **Typography:** Select from multiple fonts, adjust label and value font sizes independently, and toggle bold text.
* **Colors & Shadows:** Fully customize text colors and add drop shadows for better readability against bright game backgrounds.
* **Live Preview:** Instantly see how your changes will look before saving.

## File Locations

All generated data and settings are stored locally to prevent cluttering your EDMC installation:
* **Output Path:** `~\Documents\EDMC-StreamHUD\`
* `HUD.html`: The visual overlay for OBS.
* `HUD.json`: The live data feed.
* `settings.json`: Your visual configuration.
* `totals_and_state.json`: Persistent session data to survive restarts.

<img width="648" height="638" alt="EDMC-StreamHUD-001" src="https://github.com/user-attachments/assets/cdb0ec48-9c30-4463-9f0e-a7f03b8d5dac" />
<img width="654" height="639" alt="EDMC-StreamHUD-002" src="https://github.com/user-attachments/assets/94db4daa-ae68-46a4-8c5d-ac6b8aa0405c" />

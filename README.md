<div align="center">

<img src="icon.png" alt="BOM Creator Icon" width="80" />

# BOM Creator — KiCad Plugin

**Search LCSC · Assign Components · Export BOM**

A powerful KiCad PCB plugin that lets you search LCSC for real components, assign MPN / LCSC PN / Manufacturer / Description directly to footprint fields, and export a grouped, professional Bill of Materials — all without leaving KiCad.

[![KiCad](https://img.shields.io/badge/KiCad-9.x-blue?logo=kicad&logoColor=white)](https://www.kicad.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-yellow?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Playwright](https://img.shields.io/badge/Powered%20by-Playwright-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev/)

</div>

---

## ✨ Features

- 🔍 **Live LCSC Search** — Search LCSC component database directly from KiCad using Playwright
- 🖼️ **Component Image Preview** — Hover over a result to see a high-resolution component photo
- 📦 **One-Click Assignment** — Double-click any result to instantly assign MPN, LCSC PN, Manufacturer, and Description to the selected footprint
- 💱 **Multi-Currency Pricing** — View pricing in USD, EUR, GBP, INR, JPY, AUD, or CAD with live exchange rates
- 🎨 **5 Themes** — Light, Dark, KiCad Classic, Solarized, High Contrast
- 📋 **Grouped BOM Export** — Group by MPN, Value, or MPN+Value and export a clean CSV
- ⛔ **DNP Support** — Mark components as "Do Not Place" directly from the plugin, synced to KiCad's DNP flag
- 🔗 **Copy Fields** — Copy MPN/LCSC/Manufacturer fields from one component to another
- 🎯 **PCB Highlight & Zoom** — Clicking a component in the list selects and zooms to it on the PCB canvas
- 🖱️ **Right-click Context Menu** — Right-click any component to search LCSC by Value, Description, or existing MPN
- 🔎 **Smart Filtering** — Filter components by ref, value, or LCSC PN; hide already-assigned components

---

## 🚀 Installation

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **KiCad** | 9.x | Tested on KiCad 9.0 |
| **Python** | 3.8+ | Bundled with KiCad |
| **Playwright** | Latest | For LCSC scraping & image loading |
| **Pillow** *(optional)* | Latest | For better image decoding |

### Step 1 — Install Playwright

Open a terminal and run:

```bash
pip install playwright
playwright install chromium
           or
python -m playwright install chromium
```

> **Windows users:** Use the system terminal where KiCad's Python is on the PATH.

### Step 2 — Install Pillow *(recommended)*

```bash
pip install Pillow
```

Pillow enables better image format support for component photos. The plugin works without it but image loading may fail for some formats.

### Step 3 — Copy the Plugin Files

Find your KiCad plugin folder:

| OS | Path |
|---|---|
| **Windows** | `%APPDATA%\kicad\9.0\scripting\plugins\` |
| **Linux** | `~/.local/share/kicad/9.0/scripting/plugins/` |
| **macOS** | `~/Library/Preferences/kicad/9.0/scripting/plugins/` |

Create a subfolder called `bom_creator` and place all files inside it:

```
plugins/
└── bom_creator/
    ├── bom_creator.py
    ├── icon.png
    ├── requirements.txt
    └── README.md
```

### Step 4 — Load the Plugin

In KiCad PCB Editor, click the **External Plugins** button in the toolbar (the puzzle piece icon 🧩), then click **BOM Creator** from the dropdown list.

> Alternatively, go to **Tools → External Plugins → BOM Creator**

To reload after updating the plugin files:

> **Tools → External Plugins → Refresh Plugins**

---

## 🎮 Usage

### Basic Workflow

```
Open Plugin → Select Component (Left Panel) → Search LCSC → Double-click Result → Done ✅
```

### Detailed Steps

**1. Open the plugin**

Click the 🧩 **External Plugins** button in the KiCad PCB toolbar and select **BOM Creator**.

![image_1](https://github.com/user-attachments/assets/a7cc6ee9-4f74-46d6-8d76-e16880892749)

**2. Select a target component**

Click any row in the left-hand component list. The component will be highlighted and zoomed to on the PCB canvas automatically.

<img width="1917" height="1028" alt="image" src="https://github.com/user-attachments/assets/c4f3df98-40c8-4de8-ac17-4855d3df79d2" />

**3. Search LCSC**

- Type a query in the search box (e.g. `C 10uF 0402 10%`) and press **Enter** or click **Search LCSC**
- Or right-click a component → **Search LCSC for Value** to auto-fill and search in one step
  
<img width="1919" height="1030" alt="image" src="https://github.com/user-attachments/assets/0133a87e-d5e5-4405-8e03-ca000488f82c" />


**4. Pick a result**

- **Single click** a result row to preview it in the summary card below (with image, price, stock)
- **Double click** to instantly assign it to the selected component

**5. Assign fields**

Clicking **Assign Component** (or double-clicking a result) writes these fields to the footprint:

| Field | Source |
|---|---|
| `Description` | Part description from LCSC |
| `MPN` | Manufacturer Part Number |
| `LCSC` | LCSC Part Number |
| `Manufacturer` | Manufacturer name |

Verify in KiCad by pressing `E` on the component → **Fields tab**.

**6. Export BOM**

Click **📋 Export BOM…** at the bottom → choose grouping strategy → **💾 Export CSV**

<img width="1919" height="1031" alt="image" src="https://github.com/user-attachments/assets/efd84c03-f7d4-46e2-ab72-ad236e2a68f5" />


---

## 📊 BOM Export

The BOM exporter groups identical components and produces a clean CSV ready for JLCPCB, PCBWay, or your purchasing team.

### Grouping Options

| Mode | Groups by | Best for |
|---|---|---|
| **MPN** | Manufacturer Part Number | Purchasing / procurement |
| **Value** | Component value | Quick schematic review |
| **MPN + Value** | Both combined | Strict deduplication |

### Colour Coding in BOM Dialog

| Colour | Meaning |
|---|---|
| 🟢 Green | MPN **and** LCSC PN both assigned |
| 🟡 Yellow | Only one of MPN / LCSC PN assigned |
| 🔴 Red | Component marked as DNP |
| White | No data assigned yet |

### CSV Output Columns

```
References | Qty | Value | Description | Footprint | MPN | LCSC PN | Manufacturer
```

> DNP components are flagged with `(DNP)` in the MPN and LCSC PN columns so your assembler knows to skip them.

---

## ⚙️ Configuration

### Themes

Switch between themes using the **Theme** dropdown in the bottom toolbar:

| Theme | Description |
|---|---|
| **Light** | Clean white UI, ideal for bright environments |
| **Dark** | Dark navy UI, easy on the eyes at night |
| **KiCad Classic** | Matches KiCad's default colour scheme |
| **Solarized** | Solarized Dark palette |
| **High Contrast** | Maximum contrast for accessibility |

### Currency

Select your preferred currency from the **Currency** dropdown. Exchange rates are fetched automatically from [open.er-api.com](https://open.er-api.com) on startup.

Supported: `USD · EUR · GBP · INR · AUD · CAD · JPY`

---

## 🛠️ Troubleshooting

### Plugin doesn't appear in the External Plugins menu

Go to **Tools → External Plugins → Refresh Plugins**. If it still doesn't appear, check that your folder structure matches exactly:

```
plugins/
└── bom_creator/
    └── bom_creator.py   ← must be inside a subfolder
```

### Search returns no results

Make sure Playwright and Chromium are installed:

```bash
pip install playwright
playwright install chromium
        or
python -m playwright install chromium
```

### Images not loading

If you're on a corporate or university network, Cloudflare may block image requests. Try:
1. Switch to a **mobile hotspot** — this bypasses Cloudflare WAF
2. Install **Pillow**: `pip install Pillow`

### Fields not updating in KiCad

Press `E` on the component → **Fields tab**. If you don't see the new fields, make sure you clicked **Save & Close** in the plugin after assigning.

### `AttributeError: 'FOOTPRINT' object has no attribute 'GetFieldCount'`

This plugin requires **KiCad 9.x**. KiCad 9 replaced `GetFieldCount()` with `GetNextFieldId()` — which this plugin uses correctly. Upgrade KiCad if you see this error.

### `AttributeError: 'FOOTPRINT' object has no attribute 'GetDescription'`

Same as above — `GetDescription()` was removed in KiCad 9. This plugin reads Description via `GetFields()` which works correctly on KiCad 9.

---

## 📁 File Structure

```
bom_creator/
├── bom_creator.py       # Main plugin — UI, search logic, field writing
├── icon.png             # Toolbar icon (26×26 px)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

### requirements.txt

```
playwright
Pillow
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Roadmap / Ideas

- [ ] Mouser / Digi-Key search support
- [ ] JLCPCB SMT assembly CSV export format
- [ ] Batch search — auto-search all unassigned components at once
- [ ] Automatic BOM diff between two board revisions
- [ ] Eeschema (schematic editor) companion plugin

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [KiCad](https://www.kicad.org/) — The open-source PCB design suite this plugin is built for
- [LCSC](https://www.lcsc.com/) — Component data, pricing, and images
- [Playwright](https://playwright.dev/) — Browser automation for reliable scraping through WAFs
- [open.er-api.com](https://open.er-api.com) — Free live exchange rate API

---

<div align="center">

Made with ❤️ for the open-source hardware community

⭐ If this plugin saved you time, consider starring the repo!

</div>

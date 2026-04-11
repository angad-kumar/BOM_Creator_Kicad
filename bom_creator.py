import os
import traceback
"""
KiCad Plugin: LCSC Component Search & Footprint Updater
Modern, Clean UI Version with Currency, Filtering, Theme Support, HD Image Previews & Auto-DNP Sync
"""

import pcbnew
import wx
import threading
import json
import re
import io
import urllib.parse
import urllib.request
import ssl

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
#  Theme Definitions
# ══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "Light": {
        "name": "Light",
        "BG_MAIN":      wx.Colour(250, 250, 252),
        "BG_CARD":      wx.Colour(255, 255, 255),
        "BG_UPDATED":   wx.Colour(227, 242, 253),
        "BG_DONE":      wx.Colour(232, 245, 233),
        "BG_STOCK_OK":  wx.Colour(241, 248, 233),
        "BG_STATUS":    wx.Colour(255, 255, 255),
        "BG_DNP":       wx.Colour(255, 228, 228),
        "TXT_ACCENT":   wx.Colour(46, 125, 50),
        "TXT_BLUE":     wx.Colour(21, 101, 192),
        "TXT_STATUS":   wx.Colour(80, 80, 80),
        "TXT_DIM":      wx.Colour(100, 100, 100),
        "TXT_ORANGE":   wx.Colour(200, 80, 0),
        "TXT_DNP":      wx.Colour(160, 0, 0),
        "TXT_PRIMARY":  wx.Colour(0, 0, 0),
        "BOM_FULL":     wx.Colour(220, 255, 220),
        "BOM_PARTIAL":  wx.Colour(255, 250, 210),
        "LIST_BG":      wx.Colour(255, 255, 255),
        "LIST_FG":      wx.Colour(0, 0, 0),
    },
    "Dark": {
        "name": "Dark",
        "BG_MAIN":      wx.Colour(30, 30, 36),
        "BG_CARD":      wx.Colour(40, 40, 48),
        "BG_UPDATED":   wx.Colour(21, 60, 100),
        "BG_DONE":      wx.Colour(20, 65, 30),
        "BG_STOCK_OK":  wx.Colour(28, 55, 20),
        "BG_STATUS":    wx.Colour(25, 25, 31),
        "BG_DNP":       wx.Colour(80, 20, 20),
        "TXT_ACCENT":   wx.Colour(100, 210, 110),
        "TXT_BLUE":     wx.Colour(100, 170, 255),
        "TXT_STATUS":   wx.Colour(190, 190, 200),
        "TXT_DIM":      wx.Colour(150, 150, 165),
        "TXT_ORANGE":   wx.Colour(255, 160, 60),
        "TXT_DNP":      wx.Colour(255, 120, 120),
        "TXT_PRIMARY":  wx.Colour(230, 230, 235),
        "BOM_FULL":     wx.Colour(30, 75, 30),
        "BOM_PARTIAL":  wx.Colour(80, 70, 20),
        "LIST_BG":      wx.Colour(38, 38, 46),
        "LIST_FG":      wx.Colour(220, 220, 228),
    },
    "KiCad Classic": {
        "name": "KiCad Classic",
        "BG_MAIN":      wx.Colour(236, 233, 216),
        "BG_CARD":      wx.Colour(245, 242, 228),
        "BG_UPDATED":   wx.Colour(200, 220, 240),
        "BG_DONE":      wx.Colour(195, 230, 195),
        "BG_STOCK_OK":  wx.Colour(215, 235, 200),
        "BG_STATUS":    wx.Colour(228, 224, 205),
        "BG_DNP":       wx.Colour(255, 210, 210),
        "TXT_ACCENT":   wx.Colour(0, 100, 0),
        "TXT_BLUE":     wx.Colour(0, 0, 180),
        "TXT_STATUS":   wx.Colour(50, 50, 50),
        "TXT_DIM":      wx.Colour(90, 80, 60),
        "TXT_ORANGE":   wx.Colour(180, 60, 0),
        "TXT_DNP":      wx.Colour(140, 0, 0),
        "TXT_PRIMARY":  wx.Colour(20, 20, 20),
        "BOM_FULL":     wx.Colour(190, 230, 190),
        "BOM_PARTIAL":  wx.Colour(240, 230, 180),
        "LIST_BG":      wx.Colour(245, 242, 228),
        "LIST_FG":      wx.Colour(20, 20, 20),
    },
    "Solarized": {
        "name": "Solarized",
        "BG_MAIN":      wx.Colour(0, 43, 54),
        "BG_CARD":      wx.Colour(7, 54, 66),
        "BG_UPDATED":   wx.Colour(0, 73, 90),
        "BG_DONE":      wx.Colour(5, 70, 55),
        "BG_STOCK_OK":  wx.Colour(5, 60, 45),
        "BG_STATUS":    wx.Colour(0, 43, 54),
        "BG_DNP":       wx.Colour(80, 25, 10),
        "TXT_ACCENT":   wx.Colour(133, 153, 0),
        "TXT_BLUE":     wx.Colour(38, 139, 210),
        "TXT_STATUS":   wx.Colour(131, 148, 150),
        "TXT_DIM":      wx.Colour(88, 110, 117),
        "TXT_ORANGE":   wx.Colour(203, 75, 22),
        "TXT_DNP":      wx.Colour(220, 80, 50),
        "TXT_PRIMARY":  wx.Colour(147, 161, 161),
        "BOM_FULL":     wx.Colour(5, 80, 60),
        "BOM_PARTIAL":  wx.Colour(80, 65, 0),
        "LIST_BG":      wx.Colour(7, 54, 66),
        "LIST_FG":      wx.Colour(131, 148, 150),
    },
    "High Contrast": {
        "name": "High Contrast",
        "BG_MAIN":      wx.Colour(0, 0, 0),
        "BG_CARD":      wx.Colour(15, 15, 15),
        "BG_UPDATED":   wx.Colour(0, 0, 100),
        "BG_DONE":      wx.Colour(0, 80, 0),
        "BG_STOCK_OK":  wx.Colour(0, 60, 0),
        "BG_STATUS":    wx.Colour(10, 10, 10),
        "BG_DNP":       wx.Colour(100, 0, 0),
        "TXT_ACCENT":   wx.Colour(0, 255, 0),
        "TXT_BLUE":     wx.Colour(80, 180, 255),
        "TXT_STATUS":   wx.Colour(220, 220, 220),
        "TXT_DIM":      wx.Colour(180, 180, 180),
        "TXT_ORANGE":   wx.Colour(255, 165, 0),
        "TXT_DNP":      wx.Colour(255, 80, 80),
        "TXT_PRIMARY":  wx.Colour(255, 255, 255),
        "BOM_FULL":     wx.Colour(0, 100, 0),
        "BOM_PARTIAL":  wx.Colour(100, 90, 0),
        "LIST_BG":      wx.Colour(10, 10, 10),
        "LIST_FG":      wx.Colour(255, 255, 255),
    },
}

_active_theme = THEMES["Light"]

def T(key):
    return _active_theme[key]


# ══════════════════════════════════════════════════════════════════════════════
#  Currency Data & Helpers
# ══════════════════════════════════════════════════════════════════════════════

CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "AUD": "A$", "CAD": "C$", "JPY": "¥"}

def get_exchange_rates():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request("https://open.er-api.com/v6/latest/USD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            return json.loads(r.read().decode())["rates"]
    except Exception:
        return {}

def format_pricing(raw_pricing, rate, symbol):
    if rate is None or rate == 1.0 and symbol == "$": return raw_pricing
    def repl(m):
        val = float(m.group(1)) * rate
        return f"{symbol}{val:.3f}" if val < 10 else f"{symbol}{val:.2f}"
    return re.sub(r"\$\s*([0-9.]+)", repl, raw_pricing)

def search_lcsc(keyword, max_results=15):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright not installed.\nRun: pip install playwright && playwright install chromium")
    url = f"https://www.lcsc.com/search?q={urllib.parse.quote(keyword)}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Block actual image downloading to keep search fast, but allow DOM to load attributes
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["media", "font"] else route.continue_())
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "en-US,en;q=0.9"})
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("tbody tr", timeout=12000)

        # NEW: Act like a human to trigger LCSC's lazy-loaded images
        try:
            page.evaluate("""async () => {
                let rows = document.querySelectorAll('tbody tr');
                for(let i=0; i < Math.min(rows.length, 15); i++) {
                    // Scroll to the row
                    rows[i].scrollIntoView({block: 'center'});
                    // Simulate mouse hover
                    rows[i].dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                    rows[i].dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                    // Wait 50ms for the UI to react and inject the image
                    await new Promise(r => setTimeout(r, 50)); 
                }
            }""")
        except Exception:
            pass

        js_scraper = """() => {
            let results = [];
            let rows = Array.from(document.querySelectorAll('tbody tr')).slice(0, 30);
            for(let row of rows) {
                let cells = Array.from(row.children).filter(c => c.tagName.toLowerCase() === 'td');
                if(cells.length < 8) continue;
                
                let img_url = "";
                
                // Aggressive search: Look everywhere in the row for an image (LCSC moves it around)
                let imgs = row.querySelectorAll('img');
                for (let img of imgs) {
                    let src = img.getAttribute('src') || img.getAttribute('data-src') || img.getAttribute('lazy-src') || "";
                    if (src && src.match(/\.(jpg|png|jpeg|webp)/i) && !src.includes('rohs') && !src.includes('pdf') && !src.includes('hot')) {
                        img_url = src;
                        break;
                    }
                }
                
                // Backup check for CSS background images
                if (!img_url) {
                    let els = row.querySelectorAll('*');
                    for (let el of els) {
                        let style = el.getAttribute('style') || "";
                        let match = style.match(/url\\([^)]+\\)/);
                        if (match) {
                            let extracted = match[0].replace(/url\\(|&quot;|"|'|\\)/g, '');
                            if (extracted.match(/\.(jpg|png|jpeg|webp)/i) && !extracted.includes('pdf')) {
                                img_url = extracted;
                                break;
                            }
                        }
                    }
                }
                
                // Format the extracted URL securely
                if (img_url) {
                    if (img_url.startsWith('//')) img_url = 'https:' + img_url;
                    else if (img_url.startsWith('/')) img_url = 'https://www.lcsc.com' + img_url;
                    if (img_url.includes('?')) img_url = img_url.split('?')[0];
                }
                
                // Extract standard text components
                let raw_mpn = cells[1].innerText.trim().replace(/\\n/g, "|");
                let mfr = cells[2].innerText.trim().replace(/\\n/g, " ");
                let avail = cells[3].innerText.trim().replace(/\\n/g, " ");
                let raw_pricing = cells[4].innerText.trim().replace(/\\n/g, " | ");
                let desc = cells[6].innerText.trim().replace(/\\n/g, " ");
                let pkg = cells[7].innerText.trim();
                
                results.push({ img_url, raw_mpn, mfr, avail, raw_pricing, desc, pkg });
            }
            return results;
        }"""
        
        scraped_data = page.evaluate(js_scraper)
        browser.close()
        
    parsed_parts = []
    for data in scraped_data:
        elems   = [e.strip() for e in data["raw_mpn"].split("|") if e.strip()]
        mpn     = elems[0] if elems else "N/A"
        lcsc_pn = elems[1] if len(elems) > 1 else "N/A"
        
        stock   = 0
        m = re.search(r"([\d,]+)", data["avail"])
        if m: stock = int(m.group(1).replace(",", ""))
        
        clean_price = data["raw_pricing"].replace(" | More v | ", " | ").replace(" | More | ", " | ")
        
        parsed_parts.append(dict(
            mpn=mpn, lcsc_pn=lcsc_pn, mfr=data["mfr"], stock=stock, 
            raw_pricing=clean_price, package=data["pkg"], 
            desc=data["desc"], img_url=data["img_url"]
        ))
        
    parsed_parts.sort(key=lambda x: x["stock"], reverse=True)
    return parsed_parts[:max_results]

# ══════════════════════════════════════════════════════════════════════════════
#  KiCad Footprint Helpers
# ══════════════════════════════════════════════════════════════════════════════

def get_field_text(fp, name):
    try:
        f = fp.GetFieldByName(name)
        if f: return f.GetText()
    except Exception: pass
    try:
        for f in fp.GetFields():
            if f.GetName() == name: return f.GetText()
    except Exception: pass
    return ""

def set_field_text(fp, name, value):
    try:
        f = fp.GetFieldByName(name)
        if f is not None:
            f.SetText(value)
            return
    except Exception: pass
    try:
        for f in fp.GetFields():
            if f.GetName() == name:
                f.SetText(value)
                return
    except Exception: pass

    fid   = fp.GetNextFieldId()
    new_f = pcbnew.PCB_FIELD(fp, fid, name)
    new_f.SetText(value)
    new_f.SetVisible(False)
    fp.AddField(new_f)


def get_font(size, bold=False):
    weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    return wx.Font(size, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, weight)


def apply_theme_to_window(win):
    theme = _active_theme
    bg = theme["BG_MAIN"]
    fg = theme["TXT_PRIMARY"]

    if isinstance(win, (wx.Frame, wx.Dialog, wx.Panel)):
        win.SetBackgroundColour(bg)
        win.SetForegroundColour(fg)

    if isinstance(win, (wx.StaticText, wx.CheckBox)):
        win.SetForegroundColour(fg)

    if isinstance(win, wx.ListCtrl):
        list_bg = theme.get("LIST_BG")
        list_fg = theme.get("LIST_FG")
        if list_bg and list_bg != wx.NullColour: win.SetBackgroundColour(list_bg)
        if list_fg and list_fg != wx.NullColour: win.SetForegroundColour(list_fg)

    for child in win.GetChildren(): apply_theme_to_window(child)
    win.Refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  Popup Class for Hover Enlarge
# ══════════════════════════════════════════════════════════════════════════════

class ImageHoverPopup(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, style=wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_SIMPLE)
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        
        self.bitmap = wx.StaticBitmap(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.bitmap, 1, wx.EXPAND | wx.ALL, 4) 
        self.SetSizer(sizer)
        self.Hide()

    def set_image(self, wx_img):
        if wx_img and wx_img.IsOk():
            w, h = wx_img.GetWidth(), wx_img.GetHeight()
            max_dim = 400
            
            if w > max_dim or h > max_dim:
                if w > h:
                    new_w = max_dim
                    new_h = int(h * (max_dim / w))
                else:
                    new_h = max_dim
                    new_w = int(w * (max_dim / h))
                wx_img = wx_img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
            
            self.bitmap.SetBitmap(wx.Bitmap(wx_img))
            self.Fit()


# ══════════════════════════════════════════════════════════════════════════════
#  Main Application Window (Frame)
# ══════════════════════════════════════════════════════════════════════════════

class LCSCSearchFrame(wx.Frame):

    COL_REF = 0; COL_VAL = 1; COL_DESC = 2; COL_PKG = 3; COL_MPN = 4; COL_LCSC = 5; COL_MFR = 6
    RES_MPN = 0; RES_LCSC = 1; RES_MFR = 2; RES_PKG = 3; RES_STOCK = 4; RES_PRICE = 5; RES_DESC = 6

    def __init__(self, parent, footprints):
        super().__init__(
            parent, title="LCSC Component Explorer",
            style=wx.DEFAULT_FRAME_STYLE,
            size=(1250, 750)
        )
        self.SetMinSize((1000, 550))

        self.footprints      = footprints
        self.results         = []
        self.exchange_rates  = {}
        self.selected_fp     = None
        self.selected_part   = None
        self.updated_refs    = set()
        self.dnp_refs        = set() 
        self._copy_choices   = []
        self.current_img_url = "" 
        
        self.hd_image        = None 

        for ref, fp in self.footprints:
            try:
                if fp.IsDNP():
                    self.dnp_refs.add(ref)
                    continue
            except AttributeError:
                pass
            if get_field_text(fp, "DNP").upper() == "DNP":
                self.dnp_refs.add(ref)

        self.image_popup = ImageHoverPopup(self)

        self._build_ui()
        self._apply_full_theme()          
        self._populate_component_list()

        threading.Thread(target=self._fetch_rates_thread, daemon=True).start()

    def _apply_full_theme(self):
        t = _active_theme
        apply_theme_to_window(self)

        self.SetBackgroundColour(t["BG_MAIN"])

        self.sb_panel.SetBackgroundColour(t["BG_STATUS"])
        self.status_lbl.SetForegroundColour(t["TXT_STATUS"])
        self.sb_panel.Refresh()

        self._legend_updated.SetBackgroundColour(t["BG_UPDATED"]); self._legend_updated.Refresh()
        self._legend_done.SetBackgroundColour(t["BG_DONE"]);       self._legend_done.Refresh()
        self._legend_dnp.SetBackgroundColour(t["BG_DNP"]);         self._legend_dnp.Refresh()

        self._card_pnl.SetBackgroundColour(t["BG_CARD"]);          self._card_pnl.Refresh()
        self.lbl_card_mpn.SetForegroundColour(t["TXT_PRIMARY"])
        self.lbl_card_price.SetForegroundColour(t["TXT_ACCENT"])
        self.lbl_card_stock.SetForegroundColour(t["TXT_BLUE"])
        self.lbl_card_sub.SetForegroundColour(t["TXT_DIM"])
        self.lbl_card_desc.SetForegroundColour(t["TXT_PRIMARY"])
        self.lbl_card_target.SetForegroundColour(t["TXT_ORANGE"])

        for lc in (self.comp_list, self.result_list):
            list_bg = t.get("LIST_BG"); list_fg = t.get("LIST_FG")
            if list_bg and list_bg != wx.NullColour: lc.SetBackgroundColour(list_bg); lc.SetForegroundColour(list_fg)
            else: lc.SetBackgroundColour(wx.NullColour); lc.SetForegroundColour(wx.NullColour)
            lc.Refresh()

        self.rate_lbl.SetForegroundColour(t["TXT_DIM"]); self.rate_lbl.Refresh()
        self.chk_hide_assigned.SetForegroundColour(t["TXT_PRIMARY"])
        self.chk_stock.SetForegroundColour(t["TXT_PRIMARY"])
        
        self.image_popup.SetBackgroundColour(t.get("LIST_BG", wx.Colour(255, 255, 255)))
        
        self._set_empty_image()

        self.Refresh()
        self.Layout()

    def on_theme_changed(self, event):
        global _active_theme
        sel = self.theme_choice.GetSelection()
        theme_name = list(THEMES.keys())[sel]
        _active_theme = THEMES[theme_name]
        self._apply_full_theme()
        self._populate_component_list(self.comp_filter.GetValue())
        self._render_results(self.results)

    def _build_ui(self):
        self.sb_panel = wx.Panel(self)
        sb_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.status_lbl = wx.StaticText(self.sb_panel, label=" ✨ Ready.")
        self.status_lbl.SetFont(get_font(10))
        self._legend_updated = wx.Panel(self.sb_panel, size=(14, 14))
        self._legend_done    = wx.Panel(self.sb_panel, size=(14, 14))
        self._legend_dnp     = wx.Panel(self.sb_panel, size=(14, 14))
        sb_sz.Add(self.status_lbl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 8)
        sb_sz.AddStretchSpacer() 
        sb_sz.Add(self._legend_updated, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sb_sz.Add(wx.StaticText(self.sb_panel, label=" Updated"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sb_sz.Add(self._legend_done, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sb_sz.Add(wx.StaticText(self.sb_panel, label=" Has Data"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sb_sz.Add(self._legend_dnp, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sb_sz.Add(wx.StaticText(self.sb_panel, label=" DNP"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        self.sb_panel.SetSizer(sb_sz)

        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_3DBORDER)
        self.splitter.SetMinimumPaneSize(350)

        # Panel A (Left)
        pa = wx.Panel(self.splitter)
        pa_sz = wx.BoxSizer(wx.VERTICAL)
        flt_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.comp_filter = wx.SearchCtrl(pa, style=wx.TE_PROCESS_ENTER)
        self.comp_filter.SetDescriptiveText("Filter Board Components...")
        self.comp_filter.SetFont(get_font(10))
        flt_sz.Add(self.comp_filter, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        self.chk_hide_assigned = wx.CheckBox(pa, label="Hide Assigned")
        self.chk_hide_assigned.SetFont(get_font(10))
        self.chk_hide_assigned.SetValue(True)
        flt_sz.Add(self.chk_hide_assigned, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        pa_sz.Add(flt_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.comp_list = wx.ListCtrl(pa, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.BORDER_SIMPLE)
        self.comp_list.SetFont(get_font(10))
        self.comp_list.InsertColumn(self.COL_REF,  "Ref",       width=55)
        self.comp_list.InsertColumn(self.COL_VAL,  "Value",     width=90)
        self.comp_list.InsertColumn(self.COL_DESC, "Desc",      width=130)
        self.comp_list.InsertColumn(self.COL_PKG,  "Footprint", width=140)
        self.comp_list.InsertColumn(self.COL_MPN,  "MPN",       width=120) 
        self.comp_list.InsertColumn(self.COL_LCSC, "LCSC",      width=100) 
        self.comp_list.InsertColumn(self.COL_MFR,  "Mfr",       width=95)
        pa_sz.Add(self.comp_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        copy_sz = wx.BoxSizer(wx.HORIZONTAL)
        copy_sz.Add(wx.StaticText(pa, label="Copy data from:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.copy_choice = wx.Choice(pa, choices=[])
        copy_sz.Add(self.copy_choice, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.copy_btn = wx.Button(pa, label="Apply", size=(70, 28))
        self.copy_btn.Enable(False)
        copy_sz.Add(self.copy_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        pa_sz.Add(copy_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        pa.SetSizer(pa_sz)

        # Panel B (Right)
        pb = wx.Panel(self.splitter)
        pb_sz = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        self.search_box = wx.TextCtrl(pb, style=wx.TE_PROCESS_ENTER | wx.BORDER_SIMPLE)
        self.search_box.SetHint(" e.g. C 10uF 0402 10%")
        self.search_box.SetFont(get_font(12))
        self.search_box.SetMinSize((-1, 32))
        search_row.Add(self.search_box, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.autofill_btn = wx.Button(pb, label="↶ Auto-fill", size=(-1, 32))
        search_row.Add(self.autofill_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.search_btn = wx.Button(pb, label="Search LCSC", size=(110, 32))
        self.search_btn.SetFont(get_font(10, bold=True))
        search_row.Add(self.search_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        pb_sz.Add(search_row, 0, wx.EXPAND | wx.ALL, 10)

        res_flt_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.result_filter = wx.SearchCtrl(pb)
        self.result_filter.SetDescriptiveText("Filter results...")
        self.result_filter.SetFont(get_font(10))
        res_flt_sz.Add(self.result_filter, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        self.chk_stock = wx.CheckBox(pb, label="In Stock Only")
        self.chk_stock.SetFont(get_font(10))
        res_flt_sz.Add(self.chk_stock, 0, wx.ALIGN_CENTER_VERTICAL)
        pb_sz.Add(res_flt_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.result_list = wx.ListCtrl(pb, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.BORDER_SIMPLE)
        self.result_list.SetFont(get_font(10))
        self.result_list.InsertColumn(self.RES_MPN,   "MPN",          width=150)
        self.result_list.InsertColumn(self.RES_LCSC,  "LCSC PN",      width=100)
        self.result_list.InsertColumn(self.RES_MFR,   "Mfr",          width=110)
        self.result_list.InsertColumn(self.RES_PKG,   "Package",      width=90)
        self.result_list.InsertColumn(self.RES_STOCK, "Stock",        width=80)
        self.result_list.InsertColumn(self.RES_PRICE, "Price ($)",    width=120)
        self.result_list.InsertColumn(self.RES_DESC,  "Description",  width=280)
        pb_sz.Add(self.result_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # ── Compact Part Summary Card ──
        self._card_pnl = wx.Panel(pb)
        card_sz = wx.BoxSizer(wx.HORIZONTAL)
        
        # Image Container (80x80) with HOVER bindings
        self.img_bitmap = wx.StaticBitmap(self._card_pnl, size=(80, 80))
        self.img_bitmap.SetMinSize((80, 80))
        self.img_bitmap.Bind(wx.EVT_ENTER_WINDOW, self.on_img_enter)
        self.img_bitmap.Bind(wx.EVT_LEAVE_WINDOW, self.on_img_leave)
        card_sz.Add(self.img_bitmap, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
        
        info_sz = wx.BoxSizer(wx.VERTICAL)
        r1_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_card_mpn = wx.StaticText(self._card_pnl, label="No Part Selected", style=wx.ST_ELLIPSIZE_END)
        self.lbl_card_mpn.SetFont(get_font(10, bold=True))
        r1_sz.Add(self.lbl_card_mpn, 1, wx.ALIGN_CENTER_VERTICAL)
        self.lbl_card_price = wx.StaticText(self._card_pnl, label="--")
        self.lbl_card_price.SetFont(get_font(10, bold=True))
        r1_sz.Add(self.lbl_card_price, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.LEFT, 10)
        self.lbl_card_stock = wx.StaticText(self._card_pnl, label="Stock: --")
        self.lbl_card_stock.SetFont(get_font(9, bold=True))
        r1_sz.Add(self.lbl_card_stock, 0, wx.ALIGN_CENTER_VERTICAL)
        info_sz.Add(r1_sz, 0, wx.EXPAND | wx.BOTTOM, 2)

        self.lbl_card_sub = wx.StaticText(self._card_pnl, label="Manufacturer: --  |  LCSC PN: --", style=wx.ST_ELLIPSIZE_END)
        self.lbl_card_sub.SetFont(get_font(8))
        info_sz.Add(self.lbl_card_sub, 0, wx.EXPAND | wx.BOTTOM, 2)
        
        self.lbl_card_desc = wx.StaticText(self._card_pnl, label="Select a component from the list to view details.", style=wx.ST_ELLIPSIZE_END)
        self.lbl_card_desc.SetFont(get_font(8))
        info_sz.Add(self.lbl_card_desc, 0, wx.EXPAND | wx.BOTTOM, 2)
        
        self.lbl_card_target = wx.StaticText(self._card_pnl, label="▶ Target: None", style=wx.ST_ELLIPSIZE_END)
        self.lbl_card_target.SetFont(get_font(9, bold=True))
        info_sz.Add(self.lbl_card_target, 0, wx.EXPAND)

        card_sz.Add(info_sz, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.apply_btn = wx.Button(self._card_pnl, label="Assign\nComponent", size=(85, 45))
        self.apply_btn.SetFont(get_font(9, bold=True))
        self.apply_btn.Enable(False)
        card_sz.Add(self.apply_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)

        self._card_pnl.SetSizer(card_sz)
        pb_sz.Add(self._card_pnl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        pb.SetSizer(pb_sz)
        self.splitter.SplitVertically(pa, pb, sashPosition=480)

        # Bottom Toolbar 
        bottom_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.bom_btn = wx.Button(self, label="📋 Export BOM...", size=(-1, 30))
        self.bom_btn.SetFont(get_font(10))
        bottom_sz.Add(self.bom_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 12)
        bottom_sz.Add(wx.StaticLine(self, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        bottom_sz.Add(wx.StaticText(self, label="Currency: "), 0, wx.ALIGN_CENTER_VERTICAL)
        display_choices = [f"{code} ({symbol})" for code, symbol in CURRENCIES.items()]
        self.currency_choice = wx.Choice(self, choices=display_choices)
        self.currency_choice.SetSelection(0)
        bottom_sz.Add(self.currency_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.rate_lbl = wx.StaticText(self, label="Fetching rates...")
        bottom_sz.Add(self.rate_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 10)

        bottom_sz.Add(wx.StaticLine(self, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        bottom_sz.Add(wx.StaticText(self, label="Theme: "), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        self.theme_choice = wx.Choice(self, choices=list(THEMES.keys()))
        self.theme_choice.SetSelection(0)
        self.theme_choice.SetFont(get_font(10))
        bottom_sz.Add(self.theme_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        bottom_sz.AddStretchSpacer()
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label="Close", size=(80, 30))
        self.ok_btn    = wx.Button(self, wx.ID_OK, label="Save & Close", size=(110, 30))
        self.ok_btn.SetFont(get_font(10, bold=True))
        bottom_sz.Add(self.close_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        bottom_sz.Add(self.ok_btn,   0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self.sb_panel, 0, wx.EXPAND | wx.BOTTOM, 1)
        root.Add(wx.StaticLine(self), 0, wx.EXPAND)
        root.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 6)
        root.Add(wx.StaticLine(self), 0, wx.EXPAND)
        root.Add(bottom_sz, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        self.SetSizer(root)

        # Events 
        self.search_btn.Bind(wx.EVT_BUTTON, self.on_search)
        self.search_box.Bind(wx.EVT_TEXT_ENTER, self.on_search)
        self.autofill_btn.Bind(wx.EVT_BUTTON, self.on_autofill)
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        self.close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.bom_btn.Bind(wx.EVT_BUTTON, self.on_export_bom)
        self.comp_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_comp_selected)
        self.comp_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_comp_right_click)
        self.result_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_result_selected)
        self.result_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_result_double_click)
        self.comp_filter.Bind(wx.EVT_TEXT, lambda e: self._populate_component_list(self.comp_filter.GetValue()))
        self.chk_hide_assigned.Bind(wx.EVT_CHECKBOX, lambda e: self._populate_component_list(self.comp_filter.GetValue()))
        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_fields)
        self.copy_choice.Bind(wx.EVT_CHOICE, self.on_copy_choice_changed)
        self.result_filter.Bind(wx.EVT_TEXT, lambda e: self._render_results(self.results))
        self.chk_stock.Bind(wx.EVT_CHECKBOX, lambda e: self._render_results(self.results))
        self.currency_choice.Bind(wx.EVT_CHOICE, self.on_currency_changed)
        self.theme_choice.Bind(wx.EVT_CHOICE, self.on_theme_changed) 

    # ─────────────────────────────────────────────────────────────────────────
    #  Image Handling: Bypassing Web Application Firewalls (WAF)
    # ─────────────────────────────────────────────────────────────────────────
    def on_img_enter(self, event):
        """Show larger image popup on hover"""
        if self.hd_image and self.hd_image.IsOk():
            self.image_popup.set_image(self.hd_image)
            pt = self.img_bitmap.ClientToScreen((85, -200))
            self.image_popup.SetPosition((pt.x, pt.y))
            self.image_popup.Show()
        event.Skip()

    def on_img_leave(self, event):
        """Hide the popup when mouse leaves the thumbnail"""
        if self.image_popup.IsShown():
            self.image_popup.Hide()
        event.Skip()

    def _set_empty_image(self):
        self.hd_image = None
        if self.image_popup.IsShown():
            self.image_popup.Hide()
            
        img = wx.Image(80, 80)
        t = _active_theme
        bg = t.get("BG_MAIN", wx.Colour(240, 240, 240))
        img.SetRGB(wx.Rect(0, 0, 80, 80), bg.Red(), bg.Green(), bg.Blue())
        self.img_bitmap.SetBitmap(wx.Bitmap(img))
        self._card_pnl.Layout()

    def _download_image_bytes(self, target_url):
        """
        Uses Playwright's background Chromium networking stack to download the image bytes.
        Because this uses a real browser, Cloudflare WAFs on Home Wi-Fi cannot block it.
        """
        if PLAYWRIGHT_AVAILABLE:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        extra_http_headers={'Referer': 'https://www.lcsc.com/'}
                    )
                    # Use the browser context's built-in API request fetcher (fast and unblockable)
                    response = context.request.get(target_url, timeout=8000)
                    if response.ok:
                        data = response.body()
                        browser.close()
                        return data
                    browser.close()
            except Exception:
                pass # If Playwright fails, fall through to urllib

        # Fallback: urllib (This is what Cloudflare blocks on Wi-Fi, but works on Mobile Hotspots)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(target_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/*,*/*;q=0.8',
            'Referer': 'https://www.lcsc.com/'
        })
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            return response.read()

    def _fetch_and_set_image(self, url):
        if not url: 
            wx.CallAfter(self.status_lbl.SetLabel, " ⚠️ No image available for this component.")
            return
            
        wx.CallAfter(self.status_lbl.SetLabel, " 🔄 Fetching image via Browser...")
        
        hd_url = re.sub(r'/[0-9]+x[0-9]+/', '/900x900/', url)
        img_data = None
        
        try:
            img_data = self._download_image_bytes(hd_url)
        except Exception:
            try:
                img_data = self._download_image_bytes(url)
            except Exception as e:
                wx.CallAfter(self.status_lbl.SetLabel, f" ❌ Connection Blocked. Use Hotspot.")
                return
                
        if self.current_img_url == url and img_data:
            wx.CallAfter(self._update_image_ui, img_data, url)

    def _update_image_ui(self, img_data, url):
        if self.current_img_url != url: return
        
        stream = io.BytesIO(img_data)
        img = None
        
        try:
            from PIL import Image as PILImage
            p_img = PILImage.open(stream).convert('RGB')
            w, h = p_img.size
            img = wx.Image(w, h, p_img.tobytes())
        except Exception:
            pass 
            
        if img is None:
            try:
                stream.seek(0)
                img = wx.Image()
                img.LoadFile(stream, wx.BITMAP_TYPE_ANY)
            except Exception:
                pass

        if img and img.IsOk():
            try:
                self.hd_image = img.Copy()
                
                w, h = img.GetWidth(), img.GetHeight()
                max_dim = 80
                if w > max_dim or h > max_dim:
                    if w > h:
                        new_w = max_dim
                        new_h = int(h * (max_dim / w))
                    else:
                        new_h = max_dim
                        new_w = int(w * (max_dim / h))
                    img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
                else:
                    new_w, new_h = w, h
                
                final_img = wx.Image(80, 80)
                bg = _active_theme.get("BG_MAIN", wx.Colour(250, 250, 252))
                final_img.SetRGB(wx.Rect(0, 0, 80, 80), bg.Red(), bg.Green(), bg.Blue())
                final_img.Paste(img, (80 - new_w) // 2, (80 - new_h) // 2)

                self.img_bitmap.SetBitmap(wx.Bitmap(final_img))
                self._card_pnl.Layout()
                self.status_lbl.SetLabel(" ✅ Image Loaded.")
                return
            except Exception as e:
                self.status_lbl.SetLabel(f" ❌ Render Error: {str(e)}")
        else:
            self.status_lbl.SetLabel(" ❌ Decoding Failed (Format unsupported without PIL).")
            
        self._set_empty_image()

    # ─────────────────────────────────────────────────────────────────────────
    #  Currency Handling
    # ─────────────────────────────────────────────────────────────────────────
    def _fetch_rates_thread(self):
        rates = get_exchange_rates()
        wx.CallAfter(self._on_rates_fetched, rates)

    def _on_rates_fetched(self, rates):
        self.exchange_rates = rates
        self._update_rate_label()
        if self.results: self._render_results(self.results)

    def on_currency_changed(self, event):
        self._update_rate_label()
        self._render_results(self.results)
        if self.selected_part: self._update_detail(self.selected_part)

    def _update_rate_label(self):
        idx = self.currency_choice.GetSelection()
        curr_code = list(CURRENCIES.keys())[idx]
        if not self.exchange_rates:
            self.rate_lbl.SetLabel("Fetching rates...")
            return
        rate = self.exchange_rates.get(curr_code, 1.0)
        symbol = CURRENCIES.get(curr_code, "$")
        if curr_code == "USD": self.rate_lbl.SetLabel("Base: USD")
        else: self.rate_lbl.SetLabel(f"1 USD = {symbol}{rate:.3f}")

    def _get_active_currency_info(self):
        idx = self.currency_choice.GetSelection()
        curr_code = list(CURRENCIES.keys())[idx]
        rate = self.exchange_rates.get(curr_code, 1.0) if self.exchange_rates else 1.0
        symbol = CURRENCIES.get(curr_code, "$")
        return rate, symbol

    # ─────────────────────────────────────────────────────────────────────────
    #  Panel A — Component list
    # ─────────────────────────────────────────────────────────────────────────
    def _populate_component_list(self, filter_text=""):
        selected_ref = None
        sel = self.comp_list.GetFirstSelected()
        if sel != -1: selected_ref = self.comp_list.GetItemText(sel, self.COL_REF)

        self.comp_list.DeleteAllItems()
        self._populate_copy_dropdown()
        fl = filter_text.lower()
        hide_assigned = self.chk_hide_assigned.GetValue()

        reselect_idx = -1
        for ref, fp in self.footprints:
            val  = fp.GetValue()
            desc = get_field_text(fp, "Description")
            mpn  = get_field_text(fp, "MPN")
            lcsc = get_field_text(fp, "LCSC")
            mfr  = get_field_text(fp, "Manufacturer")
            
            kicad_footprint = str(fp.GetFPIDAsString()).split(':')[-1]

            if hide_assigned and lcsc.strip():
                continue

            if fl and fl not in ref.lower() and fl not in val.lower() and fl not in mpn.lower() and fl not in lcsc.lower():
                continue

            is_dnp = ref in self.dnp_refs
            dnp_tag = " (DNP)" if is_dnp else ""

            idx = self.comp_list.InsertItem(self.comp_list.GetItemCount(), ref)
            self.comp_list.SetItem(idx, self.COL_VAL,  val)
            self.comp_list.SetItem(idx, self.COL_DESC, desc)
            self.comp_list.SetItem(idx, self.COL_PKG,  kicad_footprint)
            self.comp_list.SetItem(idx, self.COL_MPN,  (mpn + dnp_tag) if mpn else (dnp_tag if is_dnp else ""))
            self.comp_list.SetItem(idx, self.COL_LCSC, (lcsc + dnp_tag) if lcsc else (dnp_tag if is_dnp else ""))
            self.comp_list.SetItem(idx, self.COL_MFR,  mfr)

            t = _active_theme
            if is_dnp:
                self.comp_list.SetItemBackgroundColour(idx, t["BG_DNP"])
                self.comp_list.SetItemTextColour(idx, t["TXT_DNP"])
            elif ref in self.updated_refs:
                self.comp_list.SetItemBackgroundColour(idx, t["BG_UPDATED"])
            elif lcsc:
                self.comp_list.SetItemBackgroundColour(idx, t["BG_DONE"])

            if ref == selected_ref: reselect_idx = idx

        if reselect_idx != -1:
            self.comp_list.Select(reselect_idx)
            self.comp_list.Focus(reselect_idx)
        else:
            self.selected_fp = None
            self._update_target_only()
            self._check_apply()

    def on_comp_selected(self, event):
        idx = event.GetIndex()
        ref = self.comp_list.GetItemText(idx, self.COL_REF)
        self.selected_fp = next((fp for r, fp in self.footprints if r == ref), None)
        self.status_lbl.SetLabel(f" 🎯 Selected: {ref}  |  Search LCSC or click Auto-fill.")
        if self.selected_fp: self._highlight_on_pcb(self.selected_fp)
        if self.selected_part: self._update_detail(self.selected_part)
        else: self._update_target_only()
        self._check_apply()
        self.copy_btn.Enable(bool(self._copy_choices))

    def _highlight_on_pcb(self, fp):
        board = pcbnew.GetBoard()
        for f in board.GetFootprints():
            f.ClearSelected()
            for pad in f.Pads(): pad.ClearSelected()
            for item in f.GraphicalItems(): item.ClearSelected()
        fp.SetSelected()
        for pad in fp.Pads(): pad.SetSelected()
        for item in fp.GraphicalItems(): item.SetSelected()
        self._zoom_to_fp(fp)
        pcbnew.Refresh()

    def _zoom_to_fp(self, fp):
        try:
            pcbnew.FocusOnItem(fp)
            return
        except Exception: pass
        try:
            bbox   = fp.GetBoundingBox()
            center = bbox.GetCenter()
            margin = max(bbox.GetWidth(), bbox.GetHeight())
            if margin == 0: margin = pcbnew.FromMM(5)
            for win in wx.GetTopLevelWindows():
                title = win.GetTitle().lower()
                if "pcb" in title or "kicad" in title:
                    canvas = self._find_canvas(win)
                    if canvas:
                        view = canvas.GetView()
                        view.SetCenter(pcbnew.VECTOR2D(center.x, center.y))
                        scale = min(canvas.GetSize().GetWidth(), canvas.GetSize().GetHeight()) / (margin * 3.0)
                        view.SetScale(scale)
                        canvas.Refresh()
                        return
        except Exception: pass

    def _find_canvas(self, window):
        for child in window.GetChildren():
            name = type(child).__name__
            if "GAL" in name or "Canvas" in name or "DrawPanel" in name: return child
            result = self._find_canvas(child)
            if result: return result
        return None

    def on_autofill(self, event):
        if self.selected_fp is None:
            wx.MessageBox("Select a component first.", "No Component", wx.OK | wx.ICON_WARNING)
            return
        query = (self.selected_fp.GetValue().strip() or get_field_text(self.selected_fp, "Description"))
        self.search_box.SetValue(query)
        self.search_box.SetFocus()

    def on_comp_right_click(self, event):
        idx = event.GetIndex()
        if idx == wx.NOT_FOUND: return
        ref = self.comp_list.GetItemText(idx, self.COL_REF)
        fp  = next((f for r, f in self.footprints if r == ref), None)
        if fp is None: return

        menu = wx.Menu()
        item_val  = menu.Append(wx.ID_ANY, f"Search LCSC for Value: '{fp.GetValue()}'")
        desc = get_field_text(fp, "Description")
        item_desc = menu.Append(wx.ID_ANY, f"Search LCSC for Desc: '{desc[:40]}'" if desc else "Search LCSC for Desc (empty)")
        item_desc.Enable(bool(desc))
        mpn = get_field_text(fp, "MPN")
        item_mpn  = menu.Append(wx.ID_ANY, f"Search LCSC for MPN: '{mpn}'" if mpn else "Search LCSC for MPN (empty)")
        item_mpn.Enable(bool(mpn))
        menu.AppendSeparator()
        item_auto = menu.Append(wx.ID_ANY, "Auto-fill search box from this component")
        menu.AppendSeparator()

        is_dnp = ref in self.dnp_refs
        item_dnp = menu.AppendCheckItem(wx.ID_ANY, "Mark as DNP (Do Not Place)")
        item_dnp.Check(is_dnp)

        def do_search(query):
            if not query: return
            self.comp_list.Select(idx); self.comp_list.Focus(idx)
            self.selected_fp = fp; self._highlight_on_pcb(fp)
            self.search_box.SetValue(query); self.on_search(None)

        def toggle_dnp(event):
            self._toggle_dnp(ref, fp)

        self.comp_list.Bind(wx.EVT_MENU, lambda e: do_search(fp.GetValue()), item_val)
        self.comp_list.Bind(wx.EVT_MENU, lambda e: do_search(desc), item_desc)
        self.comp_list.Bind(wx.EVT_MENU, lambda e: do_search(mpn), item_mpn)
        self.comp_list.Bind(wx.EVT_MENU, lambda e: (self.search_box.SetValue(fp.GetValue() or desc or ref), self.search_box.SetFocus()), item_auto)
        self.comp_list.Bind(wx.EVT_MENU, toggle_dnp, item_dnp)
        self.comp_list.PopupMenu(menu)
        menu.Destroy()

    def _populate_copy_dropdown(self):
        self.copy_choice.Clear()
        self._copy_choices = []
        for ref, fp in self.footprints:
            mpn, lcsc = get_field_text(fp, "MPN"), get_field_text(fp, "LCSC")
            if mpn or lcsc:
                self.copy_choice.Append(f"{ref} — {mpn or '?'} / {lcsc or '?'}")
                self._copy_choices.append((ref, fp))
        if not self._copy_choices:
            self.copy_choice.Append("(no data available)")
            self.copy_btn.Enable(False)
        else:
            self.copy_choice.SetSelection(0)
            self.copy_btn.Enable(self.selected_fp is not None)

    def on_copy_choice_changed(self, event):
        self.copy_btn.Enable(self.selected_fp is not None and bool(self._copy_choices))

    def _toggle_dnp(self, ref, fp):
        if ref in self.dnp_refs:
            self.dnp_refs.discard(ref)
            set_field_text(fp, "DNP", "")
            try: fp.SetDNP(False)
            except Exception: pass
            self.status_lbl.SetLabel(f" ✅ {ref} — DNP cleared.")
        else:
            self.dnp_refs.add(ref)
            set_field_text(fp, "DNP", "DNP")
            try: fp.SetDNP(True)
            except Exception: pass
            self.status_lbl.SetLabel(f" ⛔ {ref} — marked DNP.")

        try:
            commit = pcbnew.BOARD_COMMIT(pcbnew.GetCurrentFrame())
            commit.Modify(fp); commit.Push("Toggle DNP flag")
        except Exception:
            try: pcbnew.GetBoard().SetModified()
            except Exception: pass

        pcbnew.Refresh()
        self._populate_component_list(self.comp_filter.GetValue())

    def on_copy_fields(self, event):
        if self.selected_fp is None: return
        idx = self.copy_choice.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self._copy_choices): return
        _, src_fp = self._copy_choices[idx]
        dst_fp = self.selected_fp
        if src_fp is dst_fp: return

        for field in ["Description", "MPN", "LCSC", "Manufacturer", "Package"]:
            val = get_field_text(src_fp, field)
            if val: set_field_text(dst_fp, field, val)

        ref = dst_fp.GetReference()
        if ref in self.dnp_refs:
            self.dnp_refs.discard(ref)
            set_field_text(dst_fp, "DNP", "")
            try: dst_fp.SetDNP(False)
            except Exception: pass

        try:
            commit = pcbnew.BOARD_COMMIT(pcbnew.GetCurrentFrame())
            commit.Modify(dst_fp); commit.Push("LCSC copy fields")
        except Exception:
            try: pcbnew.GetBoard().SetModified()
            except Exception: pass

        pcbnew.Refresh()
        self.updated_refs.add(ref)
        self._populate_component_list(self.comp_filter.GetValue())
        self.status_lbl.SetLabel(f" ✅ Fields copied to {ref}")

    # ─────────────────────────────────────────────────────────────────────────
    #  Panel B — LCSC search & Apply
    # ─────────────────────────────────────────────────────────────────────────
    def on_search(self, event):
        keyword = self.search_box.GetValue().strip()
        if not keyword: return
        if not PLAYWRIGHT_AVAILABLE:
            wx.MessageBox("Playwright not installed.\npip install playwright\nplaywright install chromium", "Error", wx.OK | wx.ICON_ERROR)
            return

        self.result_list.DeleteAllItems()
        self.results = []
        self.selected_part = None
        self.apply_btn.Enable(False)
        self._clear_detail()
        self.status_lbl.SetLabel(" 🔄 Searching LCSC...")
        self.search_btn.Enable(False)

        def worker():
            try:
                parts = search_lcsc(keyword)
                wx.CallAfter(self._on_results, parts)
            except Exception as exc:
                wx.CallAfter(self._on_search_error, str(exc))
        threading.Thread(target=worker, daemon=True).start()

    def _on_results(self, parts):
        self.results = parts
        self.search_btn.Enable(True)
        self._render_results(parts)
        self.status_lbl.SetLabel(f" 🔍 Found {len(parts)} result(s). Click a row, then Assign.")

    def _on_search_error(self, msg):
        self.search_btn.Enable(True)
        self.status_lbl.SetLabel(" ❌ Search failed.")
        wx.MessageBox(f"Search error:\n{msg}", "Error", wx.OK | wx.ICON_ERROR)

    def _render_results(self, parts):
        self.result_list.DeleteAllItems()
        fl = self.result_filter.GetValue().lower()
        stock_only = self.chk_stock.GetValue()
        rate, symbol = self._get_active_currency_info()
        t = _active_theme

        col_item = self.result_list.GetColumn(self.RES_PRICE)
        col_item.SetText(f"Price ({symbol})")
        self.result_list.SetColumn(self.RES_PRICE, col_item)

        for part in parts:
            if stock_only and part["stock"] == 0: continue
            if fl and fl not in part["mpn"].lower() and fl not in part["package"].lower(): continue

            display_price = format_pricing(part["raw_pricing"], rate, symbol)
            idx = self.result_list.InsertItem(self.result_list.GetItemCount(), part["mpn"])
            self.result_list.SetItem(idx, self.RES_LCSC,  part["lcsc_pn"])
            self.result_list.SetItem(idx, self.RES_MFR,   part["mfr"])
            self.result_list.SetItem(idx, self.RES_PKG,   part["package"])
            self.result_list.SetItem(idx, self.RES_STOCK, f"{part['stock']:,}")
            self.result_list.SetItem(idx, self.RES_PRICE, display_price[:50])
            self.result_list.SetItem(idx, self.RES_DESC,  part["desc"])

            if part["stock"] > 0:
                self.result_list.SetItemBackgroundColour(idx, t["BG_STOCK_OK"])

    def on_result_selected(self, event):
        idx = event.GetIndex()
        mpn = self.result_list.GetItemText(idx, self.RES_MPN)
        part = next((p for p in self.results if p["mpn"] == mpn), None)
        if part:
            self.selected_part = part
            self._update_detail(part)
            self._check_apply()

    def on_result_double_click(self, event):
        self.on_result_selected(event)
        if self.selected_fp is None:
            wx.MessageBox("Select a component on the left first.", "Warning", wx.OK | wx.ICON_WARNING)
            return
        self.on_apply(event)

    def _clear_detail(self):
        self.current_img_url = ""
        self._set_empty_image()
        self.lbl_card_mpn.SetLabel("No Part Selected")
        self.lbl_card_price.SetLabel("--")
        self.lbl_card_stock.SetLabel("Stock: --")
        self.lbl_card_sub.SetLabel("Manufacturer: --  |  LCSC PN: --")
        self.lbl_card_desc.SetLabel("Select a component from the list to view details.")
        self._update_target_only()

    def _update_target_only(self):
        fp = self.selected_fp
        ref_text = f"▶ Will assign to: {fp.GetReference()}" if fp else "▶ Target: None (Select from Left)"
        self.lbl_card_target.SetLabel(ref_text)
        self.lbl_card_target.GetParent().Layout()

    def _update_detail(self, part):
        rate, symbol = self._get_active_currency_info()
        current_price = format_pricing(part["raw_pricing"], rate, symbol).split(" | ")[0]
        
        self.lbl_card_mpn.SetLabel(part['mpn'])
        self.lbl_card_price.SetLabel(current_price)
        self.lbl_card_stock.SetLabel(f"Stock: {part['stock']:,}")
        self.lbl_card_sub.SetLabel(f"Manufacturer: {part['mfr']}  |  LCSC PN: {part['lcsc_pn']}  |  Pkg: {part['package']}")
        
        desc = part['desc']
        if len(desc) > 110: desc = desc[:107] + "..."
        self.lbl_card_desc.SetLabel(desc)
        
        self._update_target_only()
        
        self.current_img_url = part.get("img_url", "")
        self._set_empty_image() 
        if self.current_img_url:
            threading.Thread(target=self._fetch_and_set_image, args=(self.current_img_url,), daemon=True).start()

    def _check_apply(self):
        self.apply_btn.Enable(self.selected_fp is not None and self.selected_part is not None)

    def on_apply(self, event):
        if self.selected_fp is None or self.selected_part is None: return
        fp   = self.selected_fp
        part = self.selected_part

        set_field_text(fp, "Description",  part["desc"])
        set_field_text(fp, "MPN",          part["mpn"])
        set_field_text(fp, "LCSC",         part["lcsc_pn"])
        set_field_text(fp, "Manufacturer", part["mfr"])

        ref = fp.GetReference()
        if ref in self.dnp_refs:
            self.dnp_refs.discard(ref)
            set_field_text(fp, "DNP", "")
            try: fp.SetDNP(False)
            except Exception: pass

        try:
            commit = pcbnew.BOARD_COMMIT(pcbnew.GetCurrentFrame())
            commit.Modify(fp); commit.Push("LCSC field update")
        except Exception:
            try: pcbnew.GetBoard().SetModified()
            except Exception: pass

        pcbnew.Refresh()
        self.updated_refs.add(ref)
        self.status_lbl.SetLabel(f" ✅ {ref} updated — MPN: {part['mpn']}")

        self._populate_component_list(self.comp_filter.GetValue())
        self._update_detail(part)

    def on_ok(self, event):
        try:
            pcbnew.GetBoard().SetModified()
        except: pass
        
        pcbnew.Refresh()
        self.Close()

    def on_export_bom(self, event):
        dlg = BOMExportDialog(self, self.footprints, self.dnp_refs)
        dlg.ShowModal(); dlg.Destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  BOM Export Dialog
# ══════════════════════════════════════════════════════════════════════════════

class BOMExportDialog(wx.Dialog):
    COL_REFS  = 0; COL_QTY = 1; COL_VAL = 2; COL_DESC = 3; COL_PKG = 4; COL_MPN = 5; COL_LCSC = 6; COL_MFR = 7

    def __init__(self, parent, footprints, dnp_refs=None):
        super().__init__(parent, title="BOM Export", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, size=(1060, 560))
        self.SetMinSize((700, 400))
        self.footprints = footprints
        self.dnp_refs   = dnp_refs or set()
        self.groups     = []
        self._build_ui()
        self._apply_theme()
        self._build_groups()
        self._render_table()

    def _apply_theme(self):
        t = _active_theme
        self.SetBackgroundColour(t["BG_MAIN"])
        apply_theme_to_window(self)
        self.Refresh()

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)
        opt_sz = wx.BoxSizer(wx.HORIZONTAL)
        opt_sz.Add(wx.StaticText(self, label="Group by:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        self.grp_choice = wx.Choice(self, choices=["MPN", "Value", "MPN + Value"])
        self.grp_choice.SetSelection(0)
        opt_sz.Add(self.grp_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        opt_sz.Add(wx.StaticLine(self, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.chk_no_mpn = wx.CheckBox(self, label="Include components without MPN")
        self.chk_no_mpn.SetValue(True)
        opt_sz.Add(self.chk_no_mpn, 0, wx.ALIGN_CENTER_VERTICAL)
        opt_sz.AddStretchSpacer()
        self.total_lbl = wx.StaticText(self, label="")
        opt_sz.Add(self.total_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        root.Add(opt_sz, 0, wx.EXPAND | wx.ALL, 6)
        root.Add(wx.StaticLine(self), 0, wx.EXPAND)

        self.bom_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES | wx.BORDER_SUNKEN)
        self.bom_list.InsertColumn(self.COL_REFS, "References",   width=155)
        self.bom_list.InsertColumn(self.COL_QTY,  "Qty",          width=38)
        self.bom_list.InsertColumn(self.COL_VAL,  "Value",        width=85)
        self.bom_list.InsertColumn(self.COL_DESC, "Description",  width=190)
        self.bom_list.InsertColumn(self.COL_PKG,  "Footprint",    width=140)
        self.bom_list.InsertColumn(self.COL_MPN,  "MPN",          width=155) 
        self.bom_list.InsertColumn(self.COL_LCSC, "LCSC PN",      width=100) 
        self.bom_list.InsertColumn(self.COL_MFR,  "Manufacturer", width=125) 
        
        root.Add(self.bom_list, 1, wx.EXPAND | wx.ALL, 6)

        btn_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.refresh_btn = wx.Button(self, label="↻ Refresh")
        self.export_btn  = wx.Button(self, label="💾 Export CSV...")
        self.close_btn   = wx.Button(self, wx.ID_CANCEL, label="Close")
        f = self.export_btn.GetFont(); f.SetWeight(wx.FONTWEIGHT_BOLD); self.export_btn.SetFont(f)
        btn_sz.Add(self.refresh_btn, 0, wx.LEFT, 6)
        btn_sz.AddStretchSpacer()
        btn_sz.Add(self.export_btn,  0, wx.RIGHT, 6)
        btn_sz.Add(self.close_btn,   0, wx.RIGHT, 6)
        root.Add(btn_sz, 0, wx.EXPAND | wx.BOTTOM, 8)
        self.SetSizer(root)

        self.grp_choice.Bind(wx.EVT_CHOICE,   lambda e: (self._build_groups(), self._render_table()))
        self.chk_no_mpn.Bind(wx.EVT_CHECKBOX, lambda e: (self._build_groups(), self._render_table()))
        self.refresh_btn.Bind(wx.EVT_BUTTON,  lambda e: (self._build_groups(), self._render_table()))
        self.export_btn.Bind(wx.EVT_BUTTON,   self.on_export)

    def _group_key(self, fp):
        mode = self.grp_choice.GetSelection()
        mpn  = get_field_text(fp, "MPN").strip()
        val  = fp.GetValue().strip()
        if mode == 0:   return mpn or f"__NO_MPN__{val}"
        elif mode == 1: return val
        else:           return f"{mpn}|{val}"

    def _build_groups(self):
        include_no_mpn = self.chk_no_mpn.GetValue()
        groups_dict = {}
        for ref, fp in self.footprints:
            mpn = get_field_text(fp, "MPN").strip()
            if not include_no_mpn and not mpn: continue
            key = self._group_key(fp)
            if key not in groups_dict:
                kicad_footprint = str(fp.GetFPIDAsString()).split(':')[-1]
                
                groups_dict[key] = {"refs": [], "dnp_refs": [], "value": fp.GetValue(),
                                    "desc": get_field_text(fp, "Description"), "mpn": mpn,
                                    "lcsc": get_field_text(fp, "LCSC"),
                                    "mfr": get_field_text(fp, "Manufacturer"),
                                    "pkg": kicad_footprint}
            groups_dict[key]["refs"].append(ref)
            if ref in self.dnp_refs:
                groups_dict[key]["dnp_refs"].append(ref)

        import re as _re
        def nat_sort(s): return [int(t) if t.isdigit() else t.lower() for t in _re.split(r"(\d+)", s)]
        self.groups = []
        for g in groups_dict.values():
            g["refs"].sort(key=nat_sort)
            g["dnp_refs"].sort(key=nat_sort)
            self.groups.append(g)
        self.groups.sort(key=lambda g: nat_sort(g["refs"][0]))

    def _render_table(self):
        self.bom_list.DeleteAllItems()
        t = _active_theme
        total_parts = 0
        for g in self.groups:
            refs      = ", ".join(g["refs"])
            qty       = len(g["refs"])
            total_parts += qty
            all_dnp   = len(g["dnp_refs"]) == qty        
            some_dnp  = bool(g["dnp_refs"]) and not all_dnp
            
            dnp_label = " (DNP)" if all_dnp else (f" (DNP:{','.join(g['dnp_refs'])})" if some_dnp else "")

            idx = self.bom_list.InsertItem(self.bom_list.GetItemCount(), refs)
            self.bom_list.SetItem(idx, self.COL_QTY,  str(qty))
            self.bom_list.SetItem(idx, self.COL_VAL,  g["value"])
            self.bom_list.SetItem(idx, self.COL_DESC, g["desc"])
            self.bom_list.SetItem(idx, self.COL_PKG,  g["pkg"])
            self.bom_list.SetItem(idx, self.COL_MPN,  (g["mpn"] + dnp_label) if g["mpn"] else dnp_label.strip())
            self.bom_list.SetItem(idx, self.COL_LCSC, (g["lcsc"] + dnp_label) if g["lcsc"] else dnp_label.strip())
            self.bom_list.SetItem(idx, self.COL_MFR,  g["mfr"])

            if all_dnp:
                self.bom_list.SetItemBackgroundColour(idx, t["BG_DNP"])
                self.bom_list.SetItemTextColour(idx, t["TXT_DNP"])
            elif some_dnp:
                self.bom_list.SetItemBackgroundColour(idx, t["BG_DNP"])
            elif g["mpn"] and g["lcsc"]:
                self.bom_list.SetItemBackgroundColour(idx, t["BOM_FULL"])
            elif g["mpn"] or g["lcsc"]:
                self.bom_list.SetItemBackgroundColour(idx, t["BOM_PARTIAL"])
        self.total_lbl.SetLabel(f"{len(self.groups)} line(s)  |  {total_parts} component(s) total")

    def on_export(self, event):
        import csv, os
        board = pcbnew.GetBoard()
        board_path = board.GetFileName()
        default_name = (os.path.splitext(os.path.basename(board_path))[0] + "_BOM.csv" if board_path else "BOM.csv")
        default_dir  = os.path.dirname(board_path) if board_path else ""

        dlg = wx.FileDialog(self, "Save BOM as CSV", defaultDir=default_dir, defaultFile=default_name, wildcard="CSV files (*.csv)|*.csv", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy(); return
        path = dlg.GetPath(); dlg.Destroy()

        headers = ["References", "Qty", "Value", "Description", "Footprint", "MPN", "LCSC PN", "Manufacturer"]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for g in self.groups:
                    all_dnp  = len(g["dnp_refs"]) == len(g["refs"])
                    some_dnp = bool(g["dnp_refs"]) and not all_dnp
                    dnp_val  = " (DNP)" if all_dnp else (f" (Partial DNP: {','.join(g['dnp_refs'])})" if some_dnp else "")
                    
                    writer.writerow([
                        ", ".join(g["refs"]), len(g["refs"]), g["value"], g["desc"],
                        g["pkg"], 
                        g["mpn"] + dnp_val, 
                        g["lcsc"] + dnp_val, 
                        g["mfr"]
                    ])
            wx.MessageBox(f"BOM exported successfully!\n\n  {len(self.groups)} line(s)\n  Path: {path}", "Export Complete", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Export failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)


# ══════════════════════════════════════════════════════════════════════════════
#  Plugin registration
# ══════════════════════════════════════════════════════════════════════════════

class BOMCreatorPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name        = "BOM Creator"
        self.category    = "BOM"
        self.description = "Search LCSC for components, assign MPN / LCSC PN / Manufacturer / Description to footprints, and export grouped BOM."
        self.show_toolbar_button = True
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.isfile(icon_path):
            self.icon_file_name = icon_path

    def Run(self):
        try:
            # Safely initialize wx images here when we know KiCad GUI is ready
            if not wx.Image.FindHandler(wx.BITMAP_TYPE_JPEG):
                wx.InitAllImageHandlers()

            board = pcbnew.GetBoard()
            if board is None:
                wx.MessageBox("No board open.", "Error", wx.OK | wx.ICON_ERROR)
                return

            footprints = sorted(
                [(fp.GetReference(), fp) for fp in board.GetFootprints()],
                key=lambda x: x[0]
            )

            if not footprints:
                wx.MessageBox("No footprints found on this board.", "LCSC Search", wx.OK | wx.ICON_INFORMATION)
                return
            
            # Find the parent window safely instead of relying on GetFrame()
            parent = None
            for win in wx.GetTopLevelWindows():
                if win.GetTitle().lower().startswith('pcb editor'):
                    parent = win
                    break
            
            # Use self._frame to prevent the window from being destroyed instantly
            self._frame = LCSCSearchFrame(parent, footprints)
            self._frame.Show()
            
        except Exception as e:
            err_msg = traceback.format_exc()
            wx.MessageBox(f"Plugin crashed during startup:\n\n{err_msg}", "BOM Creator Error", wx.OK | wx.ICON_ERROR)

BOMCreatorPlugin().register()
import os
"""
KiCad Plugin: LCSC Component Search & Footprint Updater
Modern, Clean UI Version with Currency & Filtering
"""

import pcbnew
import wx
import threading
import json
import re
import urllib.parse
import urllib.request
import pcbnew; pcbnew.LoadPlugins()

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
#  Currency Data & Helpers
# ══════════════════════════════════════════════════════════════════════════════

CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "AUD": "A$", "CAD": "C$", "JPY": "¥"}

def get_exchange_rates():
    try:
        req = urllib.request.Request("https://open.er-api.com/v6/latest/USD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
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
    parts = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "en-US,en;q=0.9"})
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector("tbody tr", timeout=12000)

        for row in page.locator("tbody tr").all()[: max_results * 2]:
            cells = row.locator(":scope > td").all()
            if len(cells) < 8: continue
            raw = cells[1].inner_text().strip().replace("\n", "|")
            if not raw: continue
            elems   = [e.strip() for e in raw.split("|") if e.strip()]
            mpn     = elems[0] if elems else "N/A"
            lcsc_pn = elems[1] if len(elems) > 1 else "N/A"
            mfr     = cells[2].inner_text().strip().replace("\n", " ")
            avail   = cells[3].inner_text().strip().replace("\n", " ")
            raw_pricing = cells[4].inner_text().strip().replace("\n", " | ")
            desc    = cells[6].inner_text().strip().replace("\n", " ")
            package = cells[7].inner_text().strip()
            stock   = 0
            m = re.search(r"([\d,]+)", avail)
            if m: stock = int(m.group(1).replace(",", ""))
            parts.append(dict(mpn=mpn, lcsc_pn=lcsc_pn, mfr=mfr, stock=stock, raw_pricing=raw_pricing, package=package, desc=desc))
        browser.close()
    parts.sort(key=lambda x: x["stock"], reverse=True)
    return parts[:max_results]


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


# ══════════════════════════════════════════════════════════════════════════════
#  UI Theme Colors & Fonts
# ══════════════════════════════════════════════════════════════════════════════

# Modern Pastel Palette
CLR_BG_MAIN    = wx.Colour(250, 250, 252)  # Off-white background
CLR_BG_CARD    = wx.Colour(255, 255, 255)  # Pure white for cards
CLR_UPDATED    = wx.Colour(227, 242, 253)  # Material Blue 100
CLR_DONE       = wx.Colour(232, 245, 233)  # Material Green 100
CLR_STOCK_OK   = wx.Colour(241, 248, 233)  # Material Light Green 50
CLR_ACCENT_TXT = wx.Colour(46, 125, 50)    # Dark Green for prices
CLR_BLUE_TXT   = wx.Colour(21, 101, 192)   # Dark Blue for stock

def get_font(size, bold=False):
    weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    return wx.Font(size, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, weight)


# ══════════════════════════════════════════════════════════════════════════════
#  Main Dialog
# ══════════════════════════════════════════════════════════════════════════════

class LCSCSearchDialog(wx.Dialog):

    COL_REF = 0; COL_VAL = 1; COL_DESC = 2; COL_MPN = 3; COL_LCSC = 4; COL_MFR = 5; COL_PKG = 6
    RES_MPN = 0; RES_LCSC = 1; RES_MFR = 2; RES_PKG = 3; RES_STOCK = 4; RES_PRICE = 5; RES_DESC = 6

    def __init__(self, parent, footprints):
        super().__init__(
            parent, title="LCSC Component Explorer",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX,
            size=(1200, 750)
        )
        self.SetMinSize((950, 550))
        self.SetBackgroundColour(CLR_BG_MAIN)

        self.footprints    = footprints
        self.results       = []
        self.exchange_rates = {}
        self.selected_fp   = None
        self.selected_part = None
        self.updated_refs  = set()
        self._copy_choices = [] 

        self._build_ui()
        self._populate_component_list()
        
        threading.Thread(target=self._fetch_rates_thread, daemon=True).start()

    def _build_ui(self):
        # ── Status Bar Panel (Top) ────────────────────────────────────────────
        self.sb_panel = wx.Panel(self)
        self.sb_panel.SetBackgroundColour(CLR_BG_CARD)
        sb_sz = wx.BoxSizer(wx.HORIZONTAL)
        
        self.status_lbl = wx.StaticText(self.sb_panel, label=" ✨ Ready. Select a component on the left.")
        self.status_lbl.SetFont(get_font(10))
        self.status_lbl.SetForegroundColour(wx.Colour(80, 80, 80))

        legend_updated = wx.Panel(self.sb_panel, size=(14, 14)); legend_updated.SetBackgroundColour(CLR_UPDATED)
        legend_done = wx.Panel(self.sb_panel, size=(14, 14)); legend_done.SetBackgroundColour(CLR_DONE)

        sb_sz.Add(self.status_lbl, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 8)
        sb_sz.Add(legend_updated, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sb_sz.Add(wx.StaticText(self.sb_panel, label=" Updated"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sb_sz.Add(legend_done, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        sb_sz.Add(wx.StaticText(self.sb_panel, label=" Has Data"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        self.sb_panel.SetSizer(sb_sz)

        # ── Main Splitter ─────────────────────────────────────────────────────
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_3DBORDER)
        self.splitter.SetMinimumPaneSize(350)

        # ── Panel A — Component List (Left) ───────────────────────────────────
        pa = wx.Panel(self.splitter)
        pa.SetBackgroundColour(CLR_BG_MAIN)
        pa_sz = wx.BoxSizer(wx.VERTICAL)

        flt_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.comp_filter = wx.SearchCtrl(pa, style=wx.TE_PROCESS_ENTER)
        self.comp_filter.SetDescriptiveText("Filter Board Components...")
        self.comp_filter.SetFont(get_font(10))
        flt_sz.Add(self.comp_filter, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        
        # Checkbox to hide already assigned components
        self.chk_hide_assigned = wx.CheckBox(pa, label="Hide Assigned")
        self.chk_hide_assigned.SetFont(get_font(10))
        self.chk_hide_assigned.SetValue(True) # Checked by default!
        flt_sz.Add(self.chk_hide_assigned, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        
        pa_sz.Add(flt_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.comp_list = wx.ListCtrl(pa, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.BORDER_SIMPLE)
        self.comp_list.SetFont(get_font(10))
        self.comp_list.InsertColumn(self.COL_REF,  "Ref",      width=55)
        self.comp_list.InsertColumn(self.COL_VAL,  "Value",    width=90)
        self.comp_list.InsertColumn(self.COL_DESC, "Desc",     width=140)
        self.comp_list.InsertColumn(self.COL_MPN,  "MPN",      width=120)
        self.comp_list.InsertColumn(self.COL_LCSC, "LCSC",     width=90)
        self.comp_list.InsertColumn(self.COL_MFR,  "Mfr",      width=100)
        self.comp_list.InsertColumn(self.COL_PKG,  "Package",  width=80)
        pa_sz.Add(self.comp_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        copy_sz = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(pa, label="Copy data from:")
        lbl.SetForegroundColour(wx.Colour(100, 100, 100))
        copy_sz.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.copy_choice = wx.Choice(pa, choices=[])
        copy_sz.Add(self.copy_choice, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.copy_btn = wx.Button(pa, label="Apply", size=(70, 28))
        self.copy_btn.Enable(False)
        copy_sz.Add(self.copy_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        pa_sz.Add(copy_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        pa.SetSizer(pa_sz)

        # ── Panel B — Search & Results (Right) ────────────────────────────────
        pb = wx.Panel(self.splitter)
        pb.SetBackgroundColour(CLR_BG_MAIN)
        pb_sz = wx.BoxSizer(wx.VERTICAL)

        # Big Search Bar
        search_row = wx.BoxSizer(wx.HORIZONTAL)
        self.search_box = wx.TextCtrl(pb, style=wx.TE_PROCESS_ENTER | wx.BORDER_SIMPLE)
        self.search_box.SetHint(" e.g. C 10uF 0402 10%")
        self.search_box.SetFont(get_font(12)) # Larger font for search
        self.search_box.SetMinSize((-1, 32))
        search_row.Add(self.search_box, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        
        self.autofill_btn = wx.Button(pb, label="↶ Auto-fill", size=(-1, 32))
        search_row.Add(self.autofill_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        
        self.search_btn = wx.Button(pb, label="Search LCSC", size=(110, 32))
        self.search_btn.SetFont(get_font(10, bold=True))
        search_row.Add(self.search_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        pb_sz.Add(search_row, 0, wx.EXPAND | wx.ALL, 10)

        # Results Filter
        res_flt_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.result_filter = wx.SearchCtrl(pb)
        self.result_filter.SetDescriptiveText("Filter results...")
        self.result_filter.SetFont(get_font(10))
        res_flt_sz.Add(self.result_filter, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        self.chk_stock = wx.CheckBox(pb, label="In Stock Only")
        self.chk_stock.SetFont(get_font(10))
        res_flt_sz.Add(self.chk_stock, 0, wx.ALIGN_CENTER_VERTICAL)
        pb_sz.Add(res_flt_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Results List
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

        # ── Awesome Part Summary Card ─────────────────────────────────────────
        card_pnl = wx.Panel(pb)
        card_pnl.SetBackgroundColour(CLR_BG_CARD)
        card_sz = wx.BoxSizer(wx.HORIZONTAL)
        
        info_sz = wx.BoxSizer(wx.VERTICAL)
        
        # Row 1: MPN and Price
        r1_sz = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_card_mpn = wx.StaticText(card_pnl, label="No Part Selected")
        self.lbl_card_mpn.SetFont(get_font(14, bold=True))
        r1_sz.Add(self.lbl_card_mpn, 1, wx.ALIGN_CENTER_VERTICAL)
        
        self.lbl_card_price = wx.StaticText(card_pnl, label="--")
        self.lbl_card_price.SetFont(get_font(14, bold=True))
        self.lbl_card_price.SetForegroundColour(CLR_ACCENT_TXT)
        r1_sz.Add(self.lbl_card_price, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        
        self.lbl_card_stock = wx.StaticText(card_pnl, label="Stock: --")
        self.lbl_card_stock.SetFont(get_font(12, bold=True))
        self.lbl_card_stock.SetForegroundColour(CLR_BLUE_TXT)
        r1_sz.Add(self.lbl_card_stock, 0, wx.ALIGN_CENTER_VERTICAL)
        info_sz.Add(r1_sz, 0, wx.EXPAND | wx.BOTTOM, 6)

        # Row 2: Subtext (Mfr, LCSC)
        self.lbl_card_sub = wx.StaticText(card_pnl, label="Manufacturer: --  |  LCSC PN: --")
        self.lbl_card_sub.SetFont(get_font(10))
        self.lbl_card_sub.SetForegroundColour(wx.Colour(100, 100, 100))
        info_sz.Add(self.lbl_card_sub, 0, wx.EXPAND | wx.BOTTOM, 6)

        # Row 3: Description & Target
        self.lbl_card_desc = wx.StaticText(card_pnl, label="Select a component from the list to view details.")
        self.lbl_card_desc.SetFont(get_font(10))
        info_sz.Add(self.lbl_card_desc, 0, wx.EXPAND | wx.BOTTOM, 6)

        self.lbl_card_target = wx.StaticText(card_pnl, label="▶ Target: None")
        self.lbl_card_target.SetFont(get_font(10, bold=True))
        self.lbl_card_target.SetForegroundColour(wx.Colour(200, 80, 0)) # Subtle Orange
        info_sz.Add(self.lbl_card_target, 0, wx.EXPAND)

        card_sz.Add(info_sz, 1, wx.ALL | wx.EXPAND, 12)

        # Apply Button (Big & Bold)
        self.apply_btn = wx.Button(card_pnl, label="Assign \nComponent", size=(120, 70))
        self.apply_btn.SetFont(get_font(11, bold=True))
        self.apply_btn.Enable(False)
        card_sz.Add(self.apply_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 12)
        
        card_pnl.SetSizer(card_sz)
        pb_sz.Add(card_pnl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        pb.SetSizer(pb_sz)
        self.splitter.SplitVertically(pa, pb, sashPosition=450)

        # ── Bottom Toolbar ────────────────────────────────────────────────────
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
        self.rate_lbl.SetForegroundColour(wx.Colour(130, 130, 130))
        bottom_sz.Add(self.rate_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        
        bottom_sz.AddStretchSpacer()
        self.close_btn = wx.Button(self, wx.ID_CANCEL, label="Close", size=(80, 30))
        self.ok_btn = wx.Button(self, wx.ID_OK, label="Save & Close", size=(110, 30))
        self.ok_btn.SetFont(get_font(10, bold=True))
        
        bottom_sz.Add(self.close_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        bottom_sz.Add(self.ok_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        # ── Root Layout ───────────────────────────────────────────────────────
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self.sb_panel, 0, wx.EXPAND | wx.BOTTOM, 1) # acts like a top menu bar
        root.Add(wx.StaticLine(self), 0, wx.EXPAND)
        root.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 6)
        root.Add(wx.StaticLine(self), 0, wx.EXPAND)
        root.Add(bottom_sz, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        self.SetSizer(root)

        # ── Events ────────────────────────────────────────────────────────────
        self.search_btn.Bind(wx.EVT_BUTTON, self.on_search)
        self.search_box.Bind(wx.EVT_TEXT_ENTER, self.on_search)
        self.autofill_btn.Bind(wx.EVT_BUTTON, self.on_autofill)
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        self.bom_btn.Bind(wx.EVT_BUTTON, self.on_export_bom)
        self.close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
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
            pkg  = get_field_text(fp, "Package")

            # HIDDEN LOGIC: Skip footprints that already have an LCSC part assigned
            if hide_assigned and lcsc.strip():
                continue

            if fl and fl not in ref.lower() and fl not in val.lower() and fl not in mpn.lower() and fl not in lcsc.lower():
                continue

            idx = self.comp_list.InsertItem(self.comp_list.GetItemCount(), ref)
            self.comp_list.SetItem(idx, self.COL_VAL,  val)
            self.comp_list.SetItem(idx, self.COL_DESC, desc)
            self.comp_list.SetItem(idx, self.COL_MPN,  mpn)
            self.comp_list.SetItem(idx, self.COL_LCSC, lcsc)
            self.comp_list.SetItem(idx, self.COL_MFR,  mfr)
            self.comp_list.SetItem(idx, self.COL_PKG,  pkg)

            if ref in self.updated_refs: self.comp_list.SetItemBackgroundColour(idx, CLR_UPDATED)
            elif lcsc: self.comp_list.SetItemBackgroundColour(idx, CLR_DONE)

            if ref == selected_ref: reselect_idx = idx

        if reselect_idx != -1:
            self.comp_list.Select(reselect_idx)
            self.comp_list.Focus(reselect_idx)
        else:
            # Deselect UI elements if the active item was hidden
            self.selected_fp = None
            self._update_target_only()
            self._check_apply()

    def on_comp_selected(self, event):
        idx = event.GetIndex()
        ref = self.comp_list.GetItemText(idx, self.COL_REF)
        self.selected_fp = next((fp for r, fp in self.footprints if r == ref), None)
        self.status_lbl.SetLabel(f" 🎯 Selected: {ref}  |  Search LCSC or click Auto-fill.")
        if self.selected_fp: self._highlight_on_pcb(self.selected_fp)
        
        # Trigger detail update to change the "Target" text in the UI card
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
            bbox = fp.GetBoundingBox()
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

        def do_search(query):
            if not query: return
            self.comp_list.Select(idx); self.comp_list.Focus(idx)
            self.selected_fp = fp; self._highlight_on_pcb(fp)
            self.search_box.SetValue(query); self.on_search(None)

        self.comp_list.Bind(wx.EVT_MENU, lambda e: do_search(fp.GetValue()), item_val)
        self.comp_list.Bind(wx.EVT_MENU, lambda e: do_search(desc), item_desc)
        self.comp_list.Bind(wx.EVT_MENU, lambda e: do_search(mpn), item_mpn)
        self.comp_list.Bind(wx.EVT_MENU, lambda e: (self.search_box.SetValue(fp.GetValue() or desc or ref), self.search_box.SetFocus()), item_auto)
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

        try:
            commit = pcbnew.BOARD_COMMIT(pcbnew.GetCurrentFrame())
            commit.Modify(dst_fp); commit.Push("LCSC copy fields")
        except Exception:
            try: pcbnew.GetBoard().SetModified()
            except Exception: pass

        pcbnew.Refresh()
        self.updated_refs.add(dst_fp.GetReference())
        self._populate_component_list(self.comp_filter.GetValue())
        self.status_lbl.SetLabel(f" ✅ Fields copied to {dst_fp.GetReference()}")

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

            if part["stock"] > 0: self.result_list.SetItemBackgroundColour(idx, CLR_STOCK_OK)

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
        
        # Truncate description if too long
        desc = part['desc']
        if len(desc) > 110: desc = desc[:107] + "..."
        self.lbl_card_desc.SetLabel(desc)
        
        self._update_target_only()

    def _check_apply(self):
        self.apply_btn.Enable(self.selected_fp is not None and self.selected_part is not None)

    def on_apply(self, event):
        if self.selected_fp is None or self.selected_part is None: return

        fp = self.selected_fp
        part = self.selected_part

        set_field_text(fp, "Description",  part["desc"])
        set_field_text(fp, "MPN",          part["mpn"])
        set_field_text(fp, "LCSC",         part["lcsc_pn"])
        set_field_text(fp, "Manufacturer", part["mfr"])
        set_field_text(fp, "Package",      part["package"])

        try:
            commit = pcbnew.BOARD_COMMIT(pcbnew.GetCurrentFrame())
            commit.Modify(fp); commit.Push("LCSC field update")
        except Exception:
            try: pcbnew.GetBoard().SetModified()
            except Exception: pass

        pcbnew.Refresh()
        ref = fp.GetReference()
        self.updated_refs.add(ref)
        self.status_lbl.SetLabel(f" ✅ {ref} updated — MPN: {part['mpn']}")

        # Re-populate list to instantly hide the assigned component (if checkbox is ticked)
        self._populate_component_list(self.comp_filter.GetValue())
        
        # Keep the card updated just in case the user wants to see what they just did
        self._update_detail(part)

    def on_ok(self, event):
        pcbnew.Refresh(); self.Destroy()

    def on_export_bom(self, event):
        dlg = BOMExportDialog(self, self.footprints)
        dlg.ShowModal(); dlg.Destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  BOM Export Dialog (Untouched)
# ══════════════════════════════════════════════════════════════════════════════

class BOMExportDialog(wx.Dialog):
    COL_REFS  = 0; COL_QTY = 1; COL_VAL = 2; COL_DESC = 3; COL_MPN = 4; COL_LCSC = 5; COL_MFR = 6; COL_PKG = 7

    def __init__(self, parent, footprints):
        super().__init__(parent, title="BOM Export", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, size=(1000, 560))
        self.SetMinSize((700, 400))
        self.footprints = footprints
        self.groups     = [] 
        self._build_ui()
        self._build_groups()
        self._render_table()

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
        self.bom_list.InsertColumn(self.COL_REFS, "References",   width=160)
        self.bom_list.InsertColumn(self.COL_QTY,  "Qty",          width=40)
        self.bom_list.InsertColumn(self.COL_VAL,  "Value",        width=90)
        self.bom_list.InsertColumn(self.COL_DESC, "Description",  width=200)
        self.bom_list.InsertColumn(self.COL_MPN,  "MPN",          width=160)
        self.bom_list.InsertColumn(self.COL_LCSC, "LCSC PN",      width=90)
        self.bom_list.InsertColumn(self.COL_MFR,  "Manufacturer", width=110)
        self.bom_list.InsertColumn(self.COL_PKG,  "Package",      width=90)
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
                groups_dict[key] = {"refs": [], "value": fp.GetValue(), "desc": get_field_text(fp, "Description"), "mpn": mpn, "lcsc": get_field_text(fp, "LCSC"), "mfr": get_field_text(fp, "Manufacturer"), "pkg": get_field_text(fp, "Package")}
            groups_dict[key]["refs"].append(ref)

        import re as _re
        def nat_sort(s): return [int(t) if t.isdigit() else t.lower() for t in _re.split(r"(\d+)", s)]
        self.groups = []
        for g in groups_dict.values():
            g["refs"].sort(key=nat_sort)
            self.groups.append(g)
        self.groups.sort(key=lambda g: nat_sort(g["refs"][0]))

    def _render_table(self):
        self.bom_list.DeleteAllItems()
        total_parts = 0
        for g in self.groups:
            refs = ", ".join(g["refs"]); qty = len(g["refs"]); total_parts += qty
            idx = self.bom_list.InsertItem(self.bom_list.GetItemCount(), refs)
            self.bom_list.SetItem(idx, self.COL_QTY,  str(qty))
            self.bom_list.SetItem(idx, self.COL_VAL,  g["value"])
            self.bom_list.SetItem(idx, self.COL_DESC, g["desc"])
            self.bom_list.SetItem(idx, self.COL_MPN,  g["mpn"])
            self.bom_list.SetItem(idx, self.COL_LCSC, g["lcsc"])
            self.bom_list.SetItem(idx, self.COL_MFR,  g["mfr"])
            self.bom_list.SetItem(idx, self.COL_PKG,  g["pkg"])
            if g["mpn"] and g["lcsc"]: self.bom_list.SetItemBackgroundColour(idx, wx.Colour(220, 255, 220))
            elif g["mpn"] or g["lcsc"]: self.bom_list.SetItemBackgroundColour(idx, wx.Colour(255, 250, 210))
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

        headers = ["References", "Qty", "Value", "Description", "MPN", "LCSC PN", "Manufacturer", "Package"]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for g in self.groups:
                    writer.writerow([", ".join(g["refs"]), len(g["refs"]), g["value"], g["desc"], g["mpn"], g["lcsc"], g["mfr"], g["pkg"]])
            wx.MessageBox(f"BOM exported successfully!\n\n  {len(self.groups)} line(s)\n  Path: {path}", "Export Complete", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Export failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)


# ══════════════════════════════════════════════════════════════════════════════
#  Plugin registration
# ══════════════════════════════════════════════════════════════════════════════

class LCSCFootprintPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name        = "BOM Creator"
        self.category    = "Edit"
        self.description = "Search LCSC for components, assign MPN / LCSC PN / Manufacturer / Description to footprints, and export grouped BOM."
        self.show_toolbar_button = True
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.isfile(icon_path):
            self.icon_file_name = icon_path

    def Run(self):
        board = pcbnew.GetBoard()
        footprints = sorted([(fp.GetReference(), fp) for fp in board.GetFootprints()], key=lambda x: x[0])
        if not footprints:
            wx.MessageBox("No footprints on board.", "LCSC Search", wx.OK | wx.ICON_INFORMATION)
            return
        dlg = LCSCSearchDialog(None, footprints)
        dlg.ShowModal()

LCSCFootprintPlugin().register()
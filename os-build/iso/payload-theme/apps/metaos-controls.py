#!/usr/bin/env python3
"""Meta OS Controls — the native gallery of every control the theme styles.

Why this exists: a theme is only real when the widgets are drawn by it. The
generated gtk.css names a selector for each control (buttons, entries, menus,
tabs, treeview headers, infobars, toasts, dialogs, sliders, level bars,
calendars, segmented controls, window buttons). This app instantiates one of
each so the styling can be judged in the running OS instead of in a screenshot
of a browser page.

It is also the acceptance harness: `metaos-controls.py --selftest` reads
gtk.css and fails if any selector this app relies on has gone missing. That
check runs without a display, so a build can gate on it.

    metaos-controls.py            open the gallery
    metaos-controls.py --page nav jump to a section
    metaos-controls.py --selftest exit 0 only when every selector exists
"""
import os
import sys

CSS_CANDIDATES = [
    os.environ.get("META_GTK_CSS") or "",
    "/usr/share/themes/MetaOS/gtk-3.0/gtk.css",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "gtk", "gtk.css"),
]

# One selector per control this app shows. The selftest is the contract: if a
# rule disappears from the generated CSS, the gallery would silently fall back
# to Adwaita and nobody would notice until a judge pointed at a grey button.
REQUIRED_SELECTORS = [
    "menu", "menubar", "menuitem",
    "menubutton", "combobox", "button.combo",
    "entry", "entry.search", "spinbutton", "textview",
    "switch", "check", "radio", "scale", "scale marks",
    "notebook", "notebook tab",
    "treeview.view header button", "header button",
    "sidebar", "row:selected",
    "infobar", "app-notification", "toast",
    "dialog", "messagedialog",
    "statusbar", "levelbar", "progressbar",
    "calendar", "stackswitcher", "segmented",
    "button.image-button", "titlebutton.close",
    "titlebutton.minimize", "titlebutton.maximize",
    "scrollbar", "tooltip", "popover", "osd",
]


def css_path():
    for p in CSS_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None


def selftest():
    path = css_path()
    if not path:
        print("selftest: no gtk.css found in %s" % (CSS_CANDIDATES,))
        return 1
    with open(path, "r", encoding="utf-8") as fh:
        css = fh.read()
    missing = [s for s in REQUIRED_SELECTORS if s not in css]
    if missing:
        for s in missing:
            print("FAIL missing selector: %s" % s)
        print("selftest: %d/%d selectors missing in %s"
              % (len(missing), len(REQUIRED_SELECTORS), path))
        return 1
    print("selftest: PASS %d selectors present in %s"
          % (len(REQUIRED_SELECTORS), path))
    return 0


def load_css():
    """Install the theme's GTK3 stylesheet on top of the session theme.

    The session already runs the MetaOS theme, so this is belt and braces: it
    makes the gallery look right even when launched from a terminal with a
    different GTK_THEME, which is exactly how someone would test it.
    """
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk
    path = css_path()
    if not path:
        return None
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(path)
    except Exception as exc:  # a broken sheet must not hide the app
        print("controls: gtk.css failed to parse: %s" % exc, file=sys.stderr)
        return None
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return provider


# --------------------------------------------------------------------------
# Window chrome shared by the gallery and its child demo window (R2-T2 A).
# Chrome only: minimise/maximise buttons, Alt+F4/F9/F10 + Ctrl+Q keys, and
# a per-window minimum size. No gallery content or behavior changes here.
# --------------------------------------------------------------------------
def add_window_chrome(win, hb, min_size=None):
    """Pack minimise/maximise beside the WM close button and wire the
    standard keys. Safe to call once per top-level window."""
    from gi.repository import Gtk
    if min_size:
        try:
            win.set_size_request(*min_size)
        except Exception:
            pass
    for icon, tooltip, action in (
            ("window-minimize-symbolic", "Minimise (Alt+F9)", "minimize"),
            ("window-maximize-symbolic", "Maximise (Alt+F10)",
             "toggle-maximize")):
        try:
            btn = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.MENU)
            btn.set_tooltip_text(tooltip)
            btn.set_can_focus(True)
            btn.set_focus_on_click(False)
            btn.connect("clicked", _chrome_button, win, action)
            hb.pack_end(btn)
        except Exception:
            pass
    try:
        ag = Gtk.AccelGroup()
        win.add_accel_group(ag)
        for spec, action in (("<Alt>F4", "close"),
                             ("<Alt>F9", "minimize"),
                             ("<Alt>F10", "toggle-maximize"),
                             ("<Control>q", "close")):
            key, mods = Gtk.accelerator_parse(spec)
            if key == 0:
                continue
            ag.connect(key, mods, Gtk.AccelFlags.VISIBLE,
                       _chrome_accel, win, action)
    except Exception:
        pass


def _chrome_button(_btn, win, action):
    _chrome_action(win, action)


def _chrome_accel(_ag, _obj, _key, _mods, win, action):
    _chrome_action(win, action)
    return True


def _chrome_action(win, action):
    try:
        if action == "minimize":
            win.iconify()
        elif action == "toggle-maximize":
            if win.is_maximized():
                win.unmaximize()
            else:
                win.maximize()
        elif action == "close":
            win.destroy()  # this window only; the session is untouched
    except Exception:
        pass


# --------------------------------------------------------------------------
# small builders, so each page reads as a list of controls, not as geometry
# --------------------------------------------------------------------------
def row(label, widget, note=None):
    from gi.repository import Gtk
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
    lab = Gtk.Label(label=label, xalign=0)
    lab.set_size_request(190, -1)
    lab.get_style_context().add_class("dim-label")
    box.pack_start(lab, False, False, 0)
    box.pack_start(widget, False, False, 0)
    if note:
        hint = Gtk.Label(label=note, xalign=0)
        hint.get_style_context().add_class("dim-label")
        box.pack_start(hint, False, False, 0)
    return box


def heading(text):
    from gi.repository import Gtk
    lab = Gtk.Label(label=text.upper(), xalign=0)
    lab.get_style_context().add_class("heading")
    return lab


def card(child):
    from gi.repository import Gtk
    frame = Gtk.Frame()
    frame.get_style_context().add_class("card")
    frame.add(child)
    return frame


def page(children):
    from gi.repository import Gtk
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_border_width(18)
    box.get_style_context().add_class("preferences-page")
    for i, c in enumerate(children):
        if isinstance(c, str):
            box.pack_start(heading(c), False, False, 0)
        else:
            box.pack_start(c, False, False, 0)
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    sw.add(box)
    return sw


def buttons_page():
    from gi.repository import Gtk
    b_default = Gtk.Button(label="Default")
    b_suggest = Gtk.Button(label="Submit a job")
    b_suggest.get_style_context().add_class("suggested-action")
    b_destroy = Gtk.Button(label="Purge queue")
    b_destroy.get_style_context().add_class("destructive-action")
    b_flat = Gtk.Button(label="Flat")
    b_flat.get_style_context().add_class("flat")
    b_off = Gtk.Button(label="Disabled")
    b_off.set_sensitive(False)

    icon = Gtk.Button()
    icon.get_style_context().add_class("image-button")
    icon.add(Gtk.Image.new_from_icon_name("view-refresh-symbolic",
                                          Gtk.IconSize.BUTTON))
    icon.set_tooltip_text("Open the run receipt")

    seg = Gtk.Box(spacing=0)
    seg.get_style_context().add_class("segmented")
    toggles = []
    for i, name in enumerate(("Runs", "Fleet", "Receipts")):
        b = Gtk.ToggleButton(label=name)
        b.set_active(i == 0)
        b.connect("toggled", lambda w, grp=toggles: [
            g.set_active(g is w) for g in grp if g is not w])
        toggles.append(b)
        seg.pack_start(b, False, False, 0)

    menu_btn = Gtk.MenuButton(label="Actions")
    pop = Gtk.Popover()
    popbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    popbox.set_border_width(6)
    for text in ("Open run receipt", "Copy run id", "Cancel job"):
        mb = Gtk.ModelButton(label=text)
        popbox.pack_start(mb, False, False, 0)
    popbox.show_all()
    pop.add(popbox)
    menu_btn.set_popover(pop)

    return page([
        "Buttons",
        row("default", b_default),
        row("primary", b_suggest, "accent fill, paper text"),
        row("destructive", b_destroy),
        row("flat", b_flat),
        row("disabled", b_off),
        row("icon button", icon, "flat, 8 px radius"),
        row("segmented", seg, "pill tabs"),
        row("menu button", menu_btn, "opens a popover"),
        "Shape and state",
        row("size", Gtk.Label(label="30 px high, 9 px radius"),
            "one height for every button in the OS"),
    ])


def inputs_page():
    from gi.repository import Gtk
    entry = Gtk.Entry()
    entry.set_placeholder_text("Submit a job to the fleet")
    entry.set_width_chars(28)

    search = Gtk.SearchEntry()
    search.set_placeholder_text("Search runs")
    search.set_width_chars(26)

    pw = Gtk.Entry()
    pw.set_visibility(False)
    pw.set_text("hunter2")
    pw.set_width_chars(20)

    spin = Gtk.SpinButton()
    spin.set_adjustment(Gtk.Adjustment(value=4, lower=0, upper=64,
                                      step_increment=1, page_increment=8))
    spin.set_numeric(True)

    combo = Gtk.ComboBoxText()
    for name in ("Auto", "Watchman", "Patrol", "Officina"):
        combo.append_text(name)
    combo.set_active(0)

    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    scale.set_value(62)
    scale.set_draw_value(True)
    for mark in (0, 25, 50, 75, 100):
        scale.add_mark(mark, Gtk.PositionType.BOTTOM, str(mark))
    scale.set_size_request(320, -1)

    sw = Gtk.Switch()
    sw.set_active(True)

    view = Gtk.TextView()
    view.get_buffer().set_text("Job watch-mw17tpki\nstatus: refused — 18940 not answering\n")
    view.set_size_request(320, 70)

    return page([
        "Inputs",
        row("entry", entry),
        row("entry (filled)", pw),
        row("search", search, "pill, 999 px radius"),
        row("spinbutton", spin, "22 px steppers"),
        row("combo box", combo),
        row("slider", scale, "track 4 px, thumb 14 px"),
        row("switch", sw),
        row("text view", card(view)),
    ])


def _radio_pair(a, b):
    from gi.repository import Gtk
    box = Gtk.Box(spacing=14)
    box.pack_start(a, False, False, 0)
    box.pack_start(b, False, False, 0)
    return box


def selection_page():
    from gi.repository import Gtk
    chk = Gtk.CheckButton(label="Run on boot")
    chk.set_active(True)
    radio1 = Gtk.RadioButton(label="Software GL")
    radio2 = Gtk.RadioButton(label="Hardware GL")
    radio2.join_group(radio1)
    radio1.set_active(True)

    listbox = Gtk.ListBox()
    listbox.get_style_context().add_class("sidebar")
    listbox.set_size_request(260, -1)
    for i, name in enumerate(("Overview", "Window controls", "Agents", "Aegis")):
        r = Gtk.ListBoxRow()
        r.add(Gtk.Label(label=name, xalign=0))
        r.set_size_request(-1, 34)
        if i == 1:
            pass
        listbox.add(r)
    listbox.select_row(listbox.get_row_at_index(1))

    tags = Gtk.Box(spacing=8)
    for text in ("LIVE", "QUEUED", "FAILED"):
        lab = Gtk.Label(label=text)
        lab.get_style_context().add_class("badge")
        tags.pack_start(lab, False, False, 0)

    return page([
        "Selection",
        row("check", chk),
        row("radio", _radio_pair(radio1, radio2)),
        row("sidebar", listbox, "selected row is accent"),
        row("badges", tags),
    ])


def navigation_page():
    from gi.repository import Gtk
    nb = Gtk.Notebook()
    nb.set_size_request(420, 130)
    for name in ("Runs", "Fleet", "Receipts"):
        tab = Gtk.Box(spacing=6)
        tab.pack_start(Gtk.Label(label=name), False, False, 0)
        close = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                              Gtk.IconSize.MENU)
        close.set_relief(Gtk.ReliefStyle.NONE)
        tab.pack_start(close, False, False, 0)
        body = Gtk.Label(label="%s tab — close button per tab" % name)
        nb.append_page(body, tab)
    nb.show_all()

    stack = Gtk.Stack()
    stack.add_titled(Gtk.Label(label="Stack page one"), "one", "One")
    stack.add_titled(Gtk.Label(label="Stack page two"), "two", "Two")
    switcher = Gtk.StackSwitcher(stack=stack)

    menubar = Gtk.MenuBar()
    for name in ("File", "Edit", "View", "Agents"):
        item = Gtk.MenuItem(label=name)
        sub = Gtk.Menu()
        sub.append(Gtk.MenuItem(label="%s action" % name))
        item.set_submenu(sub)
        menubar.append(item)
    menubar.show_all()

    return page([
        "Navigation",
        row("menubar", menubar, "inside a window, 28 px"),
        row("notebook", nb),
        row("stack switcher", switcher),
    ])


def pop_page(win, note_text):
    """Slide-in toast, bottom right of whatever window is open."""
    from gi.repository import GLib
    overlay = getattr(win, "_overlay", None)
    if overlay is None:
        return
    note = Gtk.Box(spacing=10)
    note.get_style_context().add_class("app-notification")
    note.pack_start(Gtk.Label(label=note_text), False, False, 0)
    overlay.add_overlay(note)
    overlay.set_overlay_pass_through(note, True)
    note.show_all()
    GLib.timeout_add_seconds(3, lambda: (overlay.remove(note), False)[1])


def feedback_page(win):
    from gi.repository import Gtk
    prog = Gtk.ProgressBar()
    prog.set_fraction(0.42)
    prog.set_show_text(True)
    prog.set_text("42 %")
    prog.set_size_request(320, -1)

    pulse = Gtk.ProgressBar()
    pulse.pulse()
    pulse.set_size_request(320, -1)
    pulse.get_style_context().add_class("indeterminate")

    level = Gtk.LevelBar()
    level.set_value(0.62)
    level.set_size_request(320, -1)

    spinner = Gtk.Spinner()
    spinner.start()
    spinner.set_size_request(24, 24)

    info = Gtk.InfoBar()
    info.set_message_type(Gtk.MessageType.INFO)
    info.get_content_area().add(Gtk.Label(
        label="18940 answers. Jobs are accepted."))
    info.add_button("Open", Gtk.ResponseType.OK)

    bad = Gtk.InfoBar()
    bad.set_message_type(Gtk.MessageType.ERROR)
    bad.get_content_area().add(Gtk.Label(
        label="18940 is not answering — the relay is down."))

    toast_btn = Gtk.Button(label="Show a toast")
    toast_btn.connect(
        "clicked", lambda *_: pop_page(win, "Job accepted — watch-mw17tpki"))

    return page([
        "Feedback",
        row("progress", prog),
        row("indeterminate", pulse),
        row("level bar", level),
        row("spinner", spinner),
        row("infobar", info),
        row("infobar (error)", bad),
        row("toast", toast_btn, "slides in bottom-right"),
    ])


def data_page():
    from gi.repository import Gtk
    store = Gtk.ListStore(str, str, str, str)
    for rec in (("watch-mw17tpki", "watchman", "refused", "0.08 s"),
                ("officina-faber-mw17ztds", "officina", "refused", "0.02 s"),
                ("research-director-mw188jtu", "research", "refused", "0.05 s")):
        store.append(list(rec))
    tree = Gtk.TreeView(model=store)
    for i, title in enumerate(("Run id", "Agent", "Outcome", "Took")):
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn(title, renderer, text=i)
        col.set_resizable(True)
        tree.append_column(col)
    tree.set_size_request(520, 120)

    status = Gtk.Statusbar()
    ctx = status.get_context_id("meta")
    status.push(ctx, "3 runs · 0 receipts · relay 18940")

    cal = Gtk.Calendar()

    return page([
        "Data",
        row("treeview", tree, "column headers per the theme"),
        row("statusbar", status),
        row("calendar", cal),
    ])


def window_page(win):
    from gi.repository import Gtk

    def open_child(*_a):
        child = Gtk.Window(title="Child window — x, -, +")
        child.set_default_size(520, 260)
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "Meta OS child window"
        add_window_chrome(child, hb, min_size=(520, 260))
        child.set_titlebar(hb)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(18)
        box.pack_start(Gtk.Label(
            label="This window is drawn by xfwm4 with the MetaOS theme.\n"
                  "The three buttons at the top right are black (close),\n"
                  "white (minimise) and blue (maximise)."), False, False, 0)
        child.add(box)
        child.show_all()

    def open_dialog(*_a):
        dlg = Gtk.MessageDialog(transient_for=win, modal=True,
                                message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text="Purge the queue?")
        dlg.format_secondary_text("3 queued jobs will be dropped.")
        dlg.run()
        dlg.destroy()

    def show_toast(*_a):
        pop_page(win, "Job accepted — watch-mw17tpki")

    b_child = Gtk.Button(label="Open a decorated window")
    b_child.connect("clicked", open_child)
    b_dialog = Gtk.Button(label="Open a dialog")
    b_dialog.connect("clicked", open_dialog)
    b_toast = Gtk.Button(label="Trigger the toast above")
    b_toast.connect("clicked", show_toast)

    return page([
        "Windows",
        row("window buttons", Gtk.Label(label="close black · minimise white · "
                                             "maximise blue"), "22 px, 6 px apart"),
        row("decorated window", b_child),
        row("dialog", b_dialog),
        row("toast", b_toast),
        "What the buttons do",
        row("close", Gtk.Label(label="closes this window")),
        row("minimise", Gtk.Label(label="hides it; the panel tasklist brings it back")),
        row("maximise", Gtk.Label(label="fills the screen; press again to restore")),
    ])


def main(argv):
    if "--selftest" in argv:
        return selftest()
    load_css()

    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk

    win = Gtk.Window(title="Meta OS Controls")
    win.set_default_size(980, 700)
    hb = Gtk.HeaderBar()
    hb.set_show_close_button(True)
    hb.props.title = "Meta OS Controls"
    hb.props.subtitle = "every control, drawn by the MetaOS theme"
    add_window_chrome(win, hb, min_size=(640, 440))
    win.set_titlebar(hb)

    overlay = Gtk.Overlay()
    win._overlay = overlay
    win.add(overlay)

    pages = [
        ("Buttons", buttons_page()),
        ("Inputs", inputs_page()),
        ("Selection", selection_page()),
        ("Navigation", navigation_page()),
        ("Feedback", feedback_page(win)),
        ("Data", data_page()),
        ("Windows", window_page(win)),
    ]
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    sidebar = Gtk.ListBox()
    sidebar.get_style_context().add_class("sidebar")
    sidebar.set_size_request(196, -1)

    for name, widget in pages:
        stack.add_titled(widget, name.lower(), name)
        r = Gtk.ListBoxRow()
        r.add(Gtk.Label(label=name, xalign=0))
        r.set_size_request(-1, 34)
        sidebar.add(r)

    def on_row(_lb, r):
        stack.set_visible_child_name(pages[r.get_index()][0].lower())

    sidebar.connect("row-selected", on_row)
    sidebar.select_row(sidebar.get_row_at_index(0))

    body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    body.pack_start(sidebar, False, False, 0)
    body.pack_start(stack, True, True, 0)
    overlay.add(body)

    if "--page" in argv:
        want = argv[argv.index("--page") + 1].lower()
        for i, (name, _w) in enumerate(pages):
            if name.lower() == want:
                sidebar.select_row(sidebar.get_row_at_index(i))
                break

    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

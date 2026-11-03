#!/usr/bin/env python3
"""meta-notes — the Meta OS notes program.

A real GTK program with real files: every note is a markdown file in ~/Notes,
named from its first line. No localStorage, no browser, no database. If the
folder is also open in Files, you see the same files, because they are files.
"""
import os
import re
import shutil
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

NOTES_DIR = os.path.join(os.path.expanduser("~"), "Notes")
CSS = b"""
window { background: #070b16; }
textview, textview text { background: #0b1220; color: #edf5ff; font-family: monospace; font-size: 13px; }
list { background: #0b1220; color: #edf5ff; }
row:selected { background: #1877f2; color: #ffffff; }
label { color: #8291ac; }
"""


def slug(text, fallback):
    first = (text.strip().splitlines() or [fallback])[0]
    s = re.sub(r"[^a-zA-Z0-9 _-]+", "", first).strip().replace(" ", "-").lower()
    return (s or fallback)[:60]


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


class Notes(Gtk.Window):
    def __init__(self):
        super().__init__(title="Meta Notes")
        self.set_default_size(760, 520)
        self.current = None

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        header = Gtk.HeaderBar(title="Meta Notes", show_close_button=True)
        self.set_titlebar(header)

        new_btn = Gtk.Button(label="New")
        new_btn.connect("clicked", self.on_new)
        header.pack_start(new_btn)

        trash_btn = Gtk.Button.new_from_icon_name("user-trash", Gtk.IconSize.BUTTON)
        trash_btn.connect("clicked", self.on_trash)
        header.pack_end(trash_btn)

        save_btn = Gtk.Button(label="Save")
        save_btn.connect("clicked", self.on_save)
        header.pack_end(save_btn)

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        split.set_position(240)
        self.add(split)

        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list.connect("row-selected", self.on_select)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.list)
        split.pack1(scroll, resize=False, shrink=False)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.set_border_width(8)
        self.view = Gtk.TextView()
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        vscroll = Gtk.ScrolledWindow()
        vscroll.add(self.view)
        right.pack_start(vscroll, True, True, 0)
        self.status = Gtk.Label(label=NOTES_DIR, xalign=0)
        right.pack_end(self.status, False, False, 0)
        split.pack2(right, resize=True, shrink=False)

        self.reload()

    # -- data ---------------------------------------------------------------
    def notes(self):
        os.makedirs(NOTES_DIR, exist_ok=True)
        out = []
        for name in sorted(os.listdir(NOTES_DIR)):
            if name.endswith(".md") and not name.startswith("."):
                path = os.path.join(NOTES_DIR, name)
                out.append((name, path, os.path.getmtime(path)))
        out.sort(key=lambda r: r[2], reverse=True)
        return out

    def reload(self):
        for row in self.list.get_children():
            self.list.remove(row)
        rows = self.notes()
        for name, path, _ in rows:
            row = Gtk.ListBoxRow()
            title = name[:-3].replace("-", " ")
            label = Gtk.Label(label=title, xalign=0)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_margin_start(8)
            row.add(label)
            row.path = path
            self.list.add(row)
        self.list.show_all()
        if rows and self.current is None:
            self.list.select_row(self.list.get_row_at_index(0))
        elif not rows:
            self.status.set_text(f"{NOTES_DIR} — no notes yet, press New")

    # -- actions ------------------------------------------------------------
    def on_select(self, _list, row):
        if row is None:
            return
        self.autosave()
        self.current = row.path
        buf = self.view.get_buffer()
        buf.set_text(read_text(row.path))
        self.status.set_text(row.path)

    def autosave(self):
        if not self.current:
            return
        buf = self.view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        if text.strip():
            write_text(self.current, text)
            self.status.set_text(f"saved {os.path.basename(self.current)}")

    def on_save(self, _btn):
        if self.current is None:
            self.on_new(None)
            return
        self.autosave()
        self.current = None
        self.reload()

    def on_new(self, _btn):
        self.autosave()
        os.makedirs(NOTES_DIR, exist_ok=True)
        stamp = time.strftime("%H%M%S")
        path = os.path.join(NOTES_DIR, f"untitled-{stamp}.md")
        write_text(path, "")
        self.current = None
        self.reload()
        for i, (name, p, _m) in enumerate(self.notes()):
            if p == path:
                self.list.select_row(self.list.get_row_at_index(i))
                break
        self.view.get_buffer().set_text("")
        self.view.grab_focus()

    def on_trash(self, _btn):
        if not self.current:
            return
        self.autosave()
        data = os.environ.get(
            "XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")
        )
        files = os.path.join(data, "Trash", "files")
        info = os.path.join(data, "Trash", "info")
        os.makedirs(files, exist_ok=True)
        os.makedirs(info, exist_ok=True)
        base = os.path.basename(self.current)
        n = 1
        while os.path.exists(os.path.join(files, base)):
            base = f"{os.path.basename(self.current)}.{n}"
            n += 1
        with open(os.path.join(info, base + ".trashinfo"), "w") as fh:
            fh.write("[Trash Info]\nPath=%s\nDeletionDate=%s\n"
                     % (self.current, time.strftime("%Y-%m-%dT%H:%M:%S")))
        shutil.move(self.current, os.path.join(files, base))
        self.current = None
        self.view.get_buffer().set_text("")
        self.reload()


def main():
    win = Notes()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Copyright (C) 2026 Essora Linux
# Essora Installer - GTK3 (Simple Wizard)
# Keyboard page (layout/model + optional variant/options)
# Simple confirmation with checkbox
# Password root opcional + bloquear root
# Timezones: combo completo + buscador
# Welcome page with image
# Formatting: choose ext4/ext3 (ext4 default) + essora label
# Autor: josejp2424

import os
import re
import sys
import threading
import importlib.util

import subprocess as _subproc

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk

from translations import Translator

APP_TITLE = "Essora Installer"
ICON_PATH = "/usr/local/essora-installer/icons/essora-installer.png"
FINISH_ICON_PATH = "/usr/local/essora-installer/icons/essora-installer-final.png"
CORNER_ICON_PATH = "/usr/local/essora-installer/icons/essora-installer2.png"
BANNERS_DIR = "/usr/local/essora-installer/banners"
LANG_DIR = "/usr/local/essora-installer/lang"
ZONEINFO_DIR = "/usr/share/zoneinfo"
EVDEV_LST = "/usr/share/X11/xkb/rules/evdev.lst"

SUPPORTED_LANGS = {
    "en": "English",
    "es": "Español",
    "ca": "Català",
    "fr": "Français",
    "it": "Italiano",
    "pt": "Português",
    "hu": "Magyar",
    "ru": "Русский",
    "ja": "日本語",
    "zh": "中文",
    "zh_TW": "繁體中文",
    "ar": "العربية",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ABOUT_SCRIPT = os.path.join(BASE_DIR, "essora-about.py")
LOCALE_ESSORA_SCRIPT = "/usr/local/essora-installer/locale-essora"

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def load_backend_module():
    normal = os.path.join(BASE_DIR, "backend.py")
    alt = os.path.join(BASE_DIR, "backend.py.py")
    if os.path.exists(normal):
        spec = importlib.util.spec_from_file_location("backend", normal)
    elif os.path.exists(alt):
        spec = importlib.util.spec_from_file_location("backend", alt)
    else:
        raise ModuleNotFoundError("backend.py not found in /usr/local/essora-installer")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


_backend = load_backend_module()
list_partitions = _backend.list_partitions
list_disks = _backend.list_disks
partition_whole_disk = _backend.partition_whole_disk
is_uefi_firmware = _backend.is_uefi_firmware
parent_disk = _backend.parent_disk
InstallPlan = _backend.InstallPlan
do_install = _backend.do_install


def load_scaled_pixbuf(path: str, max_w: int, max_h: int):
    if not path or not os.path.exists(path):
        return None
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file(path)
        w, h = pb.get_width(), pb.get_height()
        if w <= 0 or h <= 0:
            return pb
        scale = min(max_w / w, max_h / h)
        nw, nh = int(w * scale), int(h * scale)
        if nw <= 0 or nh <= 0:
            return pb
        if nw == w and nh == h:
            return pb
        return pb.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
    except Exception:
        return None


def make_corner_logo_widget(size_px: int = 96):
    pb = load_scaled_pixbuf(CORNER_ICON_PATH, size_px, size_px)
    if not pb:
        return None
    img = Gtk.Image.new_from_pixbuf(pb)
    img.set_halign(Gtk.Align.END)
    img.set_valign(Gtk.Align.END)
    img.set_margin_end(12)
    img.set_margin_bottom(12)
    return img


def wrap_with_corner_logo(content: Gtk.Widget) -> Gtk.Widget:
    overlay = Gtk.Overlay()
    overlay.add(content)
    logo = make_corner_logo_widget(96)
    if logo:
        overlay.add_overlay(logo)
    return overlay



def read_locale_conf_lang() -> str:
    for path in ("/etc/locale.conf", "/etc/default/locale"):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "LANG" and v:
                        return v
        except Exception:
            pass
    return os.environ.get("LANG", "").strip() or "en_US.UTF-8"


def lang_code_from_locale(locale_str: str) -> str:
    s = (locale_str or "").strip()
    if not s:
        return "en"
    s = s.split(".", 1)[0]
    if s.lower().startswith("zh_") and "_" in s:
        return s.split(".", 1)[0]
    return s.split("_", 1)[0].lower()


def read_default_keyboard() -> dict:
    defaults = {"XKBMODEL": "pc105", "XKBLAYOUT": "us", "XKBVARIANT": "", "XKBOPTIONS": ""}
    path = "/etc/default/keyboard"
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in defaults:
                    defaults[k] = v
    except Exception:
        pass
    return defaults
def detect_system_lang_code() -> str:
    env = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    env = env.strip()
    if env:
        code = env.split("_", 1)[0].split(".", 1)[0].lower()
        if code in SUPPORTED_LANGS:
            return code
    return "en"


def detect_system_timezone() -> str:
    try:
        if os.path.exists("/etc/timezone"):
            tz = open("/etc/timezone", "r", encoding="utf-8", errors="ignore").read().strip()
            if tz:
                return tz
    except Exception:
        pass
    return "UTC"


def list_timezones() -> list:
    zones = set()
    tab_candidates = [os.path.join(ZONEINFO_DIR, "zone1970.tab"), os.path.join(ZONEINFO_DIR, "zone.tab")]
    for tab in tab_candidates:
        if os.path.exists(tab):
            try:
                with open(tab, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            tz = parts[2].strip()
                            if tz:
                                zones.add(tz)
                break
            except Exception:
                pass

    if not zones:
        skip = {"posix", "right", "SystemV"}
        for root, dirs, files in os.walk(ZONEINFO_DIR):
            rel_root = os.path.relpath(root, ZONEINFO_DIR)
            top = rel_root.split(os.sep)[0] if rel_root != "." else ""
            if top in skip:
                continue
            for fn in files:
                if fn in ("posixrules", "localtime", "zone.tab", "zone1970.tab", "leapseconds", "tzdata.zi"):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), ZONEINFO_DIR)
                if rel.startswith(".") or rel.count(os.sep) < 1:
                    continue
                zones.add(rel.replace("\\", "/"))
        zones.update(["Etc/UTC", "Etc/GMT", "UTC"])

    out = sorted(zones)
    if "UTC" in out:
        out.remove("UTC"); out.insert(0, "UTC")
    elif "Etc/UTC" in out:
        out.remove("Etc/UTC"); out.insert(0, "Etc/UTC")
    return out


def parse_evdev_section(section: str) -> list:
    res = []
    if not os.path.exists(EVDEV_LST):
        return res
    in_sec = False
    try:
        with open(EVDEV_LST, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if line.startswith("!"):
                    in_sec = (line.strip() == f"! {section}")
                    continue
                if not in_sec or not line.strip() or line.lstrip().startswith("#"):
                    continue
                m = re.match(r"^\s*([^\s]+)\s+(.*)$", line)
                if not m:
                    continue
                res.append((m.group(1).strip(), m.group(2).strip()))
    except Exception:
        return res
    return res


def read_keyboard_defaults() -> dict:
    defaults = {"XKBMODEL": "pc105", "XKBLAYOUT": "us", "XKBVARIANT": "", "XKBOPTIONS": ""}
    path = "/etc/default/keyboard"
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in defaults:
                    defaults[k] = v
    except Exception:
        pass
    return defaults


def parse_size_to_bytes(size_str: str) -> int:
    s = (size_str or "").strip().upper()
    m = re.match(r"^(\d+(\.\d+)?)\s*([KMGTP]?)(I?B)?$", s)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(3)
    mult = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}.get(unit, 1)
    return int(val * mult)


def is_efi_candidate(part: dict) -> bool:
    path = (part.get("path") or "")
    fstype = (part.get("fstype") or "").lower()
    label = (part.get("label") or "").lower()
    mp = (part.get("mountpoint") or "").lower()
    size_b = parse_size_to_bytes(part.get("size") or "")

    if not path.startswith("/dev/"):
        return False
    if fstype not in ("vfat", "fat32", "fat"):
        return False
    if mp.endswith("/boot/efi") or mp.endswith("/efi"):
        return True
    if "efi" in label or "esp" in label or "boot" in label:
        return True
    return 80 * 1024**2 <= size_b <= 2 * 1024**3


def is_root_candidate(part: dict) -> bool:
    path = (part.get("path") or "")
    fstype = (part.get("fstype") or "").lower()
    mp = (part.get("mountpoint") or "")
    if not path.startswith("/dev/"):
        return False
    if mp:
        return False
    return fstype in ("ext4", "ext3")


def part_text(p: dict) -> str:
    return f"{p.get('path','')} ({p.get('size','')}) {p.get('fstype','')} {p.get('label','')} {p.get('mountpoint','')}".strip()


class Installer(Gtk.Assistant):
    def __init__(self):
        super().__init__(title=APP_TITLE)
        self.set_default_size(980, 620)
        self.set_position(Gtk.WindowPosition.CENTER)

        if os.path.exists(ICON_PATH):
            try:
                self.set_icon_from_file(ICON_PATH)
            except Exception:
                pass

        self.tr_mgr = Translator(LANG_DIR, default_lang="en")
        self.tr_mgr.set_language(detect_system_lang_code())

        self.part_rows = []
        self.disk_rows = []
        self.all_timezones = list_timezones()
        self.kb_defaults = read_keyboard_defaults()
        self.kb_layouts = parse_evdev_section("layout") or [("us", "English (US)"), ("latam", "Spanish (Latin American)"), ("es", "Spanish")]
        self.kb_models = parse_evdev_section("model") or [("pc105", "Generic 105-key PC"), ("pc104", "Generic 104-key PC")]

        self.connect("cancel", self._quit)
        self.connect("close", self._quit)
        self.connect("delete-event", self._quit)
        self.connect("apply", self.on_apply)
        self.connect("prepare", self.on_prepare)

        self._setup_gnome_header() 
        self.build_pages()
        self.output_finish.set_buffer(self.output.get_buffer())
        self.reload_region_from_system()
        self.refresh_partitions()
        self.validate_user_page()
        self.validate_confirm_page()
        self.apply_translations()

    def _quit(self, *_):
        try:
            current = self.get_current_page()
            total = self.get_n_pages()
            if current == total - 1:  
                if getattr(self, "chk_reboot", None) and self.chk_reboot.get_active():
                    self._on_reboot_clicked()
                    return
        except Exception:
            pass
        self.destroy()
        Gtk.main_quit()

    def _setup_gnome_header(self):
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.set_title("Essora Installer")
        hbar.props.title = "Essora Installer"


        if os.path.exists(ICON_PATH):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(ICON_PATH, 22, 22)
                hbar.pack_start(Gtk.Image.new_from_pixbuf(pb))
            except Exception:
                pass


        menu_button = Gtk.MenuButton()
        menu_icon = Gtk.Image.new_from_icon_name(
            "open-menu-symbolic", Gtk.IconSize.BUTTON
        )
        menu_button.set_image(menu_icon)
        menu_button.set_tooltip_text(self.tr("Menu"))


        menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label=self.tr("About"))
        about_item.connect("activate", lambda *_: self.open_about())
        menu.append(about_item)
        menu.show_all()
        menu_button.set_popup(menu)

        hbar.pack_end(menu_button)
        hbar.show_all()


        self.set_titlebar(hbar)
        self._hbar = hbar

    def open_about(self, *_):
        lang = getattr(self.tr_mgr, "current_lang", "en")
        try:
            if os.path.exists(ABOUT_SCRIPT):
                import importlib.util as _ilu
                spec = _ilu.spec_from_file_location("essora_about", ABOUT_SCRIPT)
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                win = mod.AboutEssora(lang=lang)
                win.set_transient_for(self)
                win.set_modal(True)
                win.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
                win.connect("destroy", lambda *_: None)
                return
        except Exception:
            pass
        try:
            _subproc.Popen(
                [sys.executable, ABOUT_SCRIPT, "--lang=" + lang],
                close_fds=True,
            )
        except Exception:
            pass


    def tr(self, s: str, **kwargs) -> str:
        return self.tr_mgr.tr(s, **kwargs)

    def apply_translations(self):
        self.set_title(self.tr("Essora Installer"))
        self.set_page_title(self.page_welcome, self.tr("Welcome"))
        self.set_page_title(self.page_region, self.tr("Time zone & Keyboard"))
        self.set_page_title(self.page_disk, self.tr("Partitions"))
        self.set_page_title(self.page_account, self.tr("Account"))
        self.set_page_title(self.page_confirm, self.tr("Confirmation"))
        self.set_page_title(self.page_install, self.tr("Installing"))
        self.set_page_title(self.page_finish, self.tr("Finished"))
        self.chk_whole_disk.set_label(self.tr("Use whole disk (automatic partitioning)"))
        self.lbl_whole_disk_target.set_text(self.tr("Disk:"))
        self.lbl_finish_title.set_markup(f"<b><big>{self.tr('Installation complete!')}</big></b>")
        self.lbl_btn_reboot.set_text(self.tr("Reboot now"))

        self.lbl_welcome_title.set_markup(f"<b>{self.tr('Welcome to Essora Installer')}</b>")
        self.lbl_welcome_body.set_text(self.tr(
            "This installer copies the LIVE system to disk and configures user, time zone, keyboard and GRUB.\n"
            "Recommended: partition with GParted and then choose EFI/Root here."
        ))
        self.lbl_welcome_warn.set_text(self.tr("⚠️ Formatting will ERASE data. Make a backup before continuing."))

        self.lbl_region_title.set_markup(f"<b>{self.tr('Time zone and Keyboard')}</b>")
        self.lbl_language.set_text(self.tr("Language:"))
        self.btn_locale.set_label(self.tr("Open Essora Locale"))
        self.lbl_timezone.set_text(self.tr("Time zone:"))
        self.lbl_kblayout.set_text(self.tr("Keyboard layout:"))

        self.lbl_disk_title.set_markup(f"<b>{self.tr('Partitions')}</b>")
        self.btn_refresh.set_label(self.tr("Refresh"))
        self.btn_gparted.set_label(self.tr("Open GParted"))
        self.lbl_efi.set_text(self.tr("Boot / EFI partition (ESP):"))
        self.lbl_root.set_text(self.tr("Root partition / (required):"))
        self.chk_format.set_label(self.tr("Format partition"))
        self.lbl_fs.set_text(self.tr("Filesystem:"))
        self.lbl_label.set_text(self.tr("Label when formatting: essora"))
        self.chk_grub.set_label(self.tr("Install GRUB (recommended)"))
        self.lbl_grubdisk.set_text(self.tr("Disk for GRUB:"))
        fw = "UEFI" if is_uefi_firmware() else "BIOS/Legacy"
        self.lbl_bootmode.set_text(self.tr("Detected firmware mode: {fw}", fw=fw))

        self.lbl_account_title.set_markup(f"<b>{self.tr('Account')}</b>")
        self.lbl_hostname.set_text(self.tr("Hostname:"))
        self.lbl_user.set_text(self.tr("Username:"))
        self.lbl_pass.set_text(self.tr("User password:"))
        self.lbl_pass2.set_text(self.tr("Repeat password:"))
        self.lbl_rootsec.set_markup(f"<b>{self.tr('Root (optional)')}</b>")
        self.chk_lock_root.set_label(self.tr("Lock root (recommended)"))
        self.chk_slim_autologin.set_label(self.tr("Enable automatic login (SLiM)"))
        self.lbl_rootpass.set_text(self.tr("Root password (optional):"))
        self.lbl_rootpass2.set_text(self.tr("Repeat root password:"))

        self.lbl_confirm_title.set_markup(f"<b>{self.tr('Summary')}</b>")
        self.chk_confirm.set_label(self.tr("I understand this may erase data and I want to continue"))

    _OP_LABELS = {
        "── Verificando":     "Verifying disk space...",
        "── Limpiando":       "Cleaning previous mounts...",
        "── Formateando part": "Formatting root partition...",
        "── Formateando /hom": "Formatting /home partition...",
        "── Montando":        "Mounting partitions...",
        "── Copiando":        "Copying system (rsync)...",
        "── Eliminando resid": "Removing live residues...",
        "── Generando":       "Generating /etc/fstab...",
        "── Configurando zona":"Configuring timezone...",
        "── Configurando tec": "Configuring keyboard...",
        "── Preparando entor": "Preparing chroot environment...",
        "── Regenerando":     "Regenerating machine-id...",
        "── Desactivando":    "Disabling autologin...",
        "── Configurando usu": "Configuring user account...",
        "── Configurando acc": "Configuring root access...",
        "── Instalando GRUB": "Installing GRUB bootloader...",
        "── Desmontando sist": "Unmounting virtual filesystems...",
        "── Desmontando part": "Unmounting partitions...",
        "── Ejecutando":      "Running post-install cleanup...",
    }

    def log(self, msg: str):
        buf = self.output.get_buffer()
        end = buf.get_end_iter()
        buf.insert(end, msg + "\n")
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.output.scroll_mark_onscreen(mark)
        for prefix, label in self._OP_LABELS.items():
            if msg.startswith(prefix):
                self.lbl_current_op.set_markup(f"<b>{label}</b>")
                break

    def set_progress(self, value: int):
        v = max(0, min(100, int(value)))
        self.pbar.set_fraction(v / 100.0)
        self.pbar.set_text(f"{v}%")
        self.pbar_finish.set_fraction(v / 100.0)
        self.pbar_finish.set_text(f"{v}% ✓" if v == 100 else f"{v}%")

    def message(self, title: str, text: str, mtype=Gtk.MessageType.INFO):
        dlg = Gtk.MessageDialog(self, 0, mtype, Gtk.ButtonsType.OK, title)
        dlg.format_secondary_text(text)
        dlg.run()
        dlg.destroy()

    def _add_completion_to_combo(self, combo: Gtk.ComboBoxText, items: list):
        entry = combo.get_child()
        if not isinstance(entry, Gtk.Entry):
            return
        completion = Gtk.EntryCompletion()
        model = Gtk.ListStore(str)
        for it in items:
            model.append([it])
        completion.set_model(model)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_popup_completion(True)
        entry.set_completion(completion)

    def _select_combo_by_code(self, combo: Gtk.ComboBoxText, code: str):
        code = (code or "").strip()
        m = combo.get_model()
        if not m:
            combo.set_active(0); return
        it = m.get_iter_first()
        i = 0
        while it:
            txt = m.get_value(it, 0) or ""
            if txt.startswith(code + " -") or txt == code:
                combo.set_active(i); return
            i += 1
            it = m.iter_next(it)
        combo.set_active(0)

    def on_language_changed(self, *_):
        self.open_essora_locale()

    def reload_region_from_system(self):
        lang = read_locale_conf_lang()
        tz = detect_system_timezone()
        kb = read_default_keyboard()

        self._kb_model = kb.get("XKBMODEL", "pc105")
        self._kb_variant = kb.get("XKBVARIANT", "")
        self._kb_options = kb.get("XKBOPTIONS", "")

        # Update fields
        if hasattr(self, "ent_locale"):
            self.ent_locale.set_text(lang)
        if hasattr(self, "ent_timezone"):
            self.ent_timezone.set_text(tz)
        if hasattr(self, "ent_kb_layout"):
            self.ent_kb_layout.set_text(kb.get("XKBLAYOUT", "us"))
        code = lang_code_from_locale(lang)
        if code.upper().startswith("ZH_"):
            code_try = code
        else:
            code_try = code

        self.tr_mgr.set_language(code_try)
        self.apply_translations()

    def open_essora_locale(self, *_):
        if not os.path.exists(LOCALE_ESSORA_SCRIPT):
            self.message(self.tr("Error"), f"Missing: {LOCALE_ESSORA_SCRIPT}", Gtk.MessageType.ERROR)
            return

        self.set_sensitive(False)

        def worker():
            try:
                _subproc.call([LOCALE_ESSORA_SCRIPT])
            finally:
                GLib.idle_add(self.set_sensitive, True)
                GLib.idle_add(self.reload_region_from_system)

        threading.Thread(target=worker, daemon=True).start()


    def open_gparted(self, *_):
        import subprocess
        try:
            subprocess.Popen(["pkexec", "gparted"])
        except Exception:
            self.message(self.tr("Warning"), self.tr("Could not open GParted (is it installed?)."), Gtk.MessageType.WARNING)

    def get_timezone_value(self) -> str:
        return (self.ent_timezone.get_text() or "UTC").strip() or "UTC"

    def get_lang_code(self) -> str:
        return lang_code_from_locale(self.ent_locale.get_text() if hasattr(self, 'ent_locale') else read_locale_conf_lang())

    def _code_from_combo(self, combo: Gtk.ComboBoxText, fallback: str) -> str:
        t = (combo.get_active_text() or "").strip()
        if not t:
            return fallback
        return t.split()[0].strip() or fallback

    def get_kb_layout(self) -> str:
        return (self.ent_kb_layout.get_text() or "us").strip() or "us"

    def get_kb_model(self) -> str:
        return (getattr(self, "_kb_model", "pc105") or "pc105").strip() or "pc105"

    def get_root_device(self) -> str:
        t = self.cmb_root.get_active_text() or ""
        return t.split()[0].strip() if t.startswith("/dev/") else ""

    def get_efi_device(self) -> str:
        t = self.cmb_efi.get_active_text() or ""
        return t.split()[0].strip() if t.startswith("/dev/") else ""

    def get_grub_disk(self) -> str:
        t = self.cmb_grubdisk.get_active_text() or ""
        return t.split()[0].strip() if t.startswith("/dev/") else ""

    def get_fs_value(self) -> str:
        return (self.cmb_fs.get_active_text() or "ext4").strip().lower()

    def build_pages(self):
        # Welcome
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        self.lbl_welcome_title = Gtk.Label(xalign=0)
        self.lbl_welcome_body = Gtk.Label(xalign=0); self.lbl_welcome_body.set_line_wrap(True)
        self.lbl_welcome_warn = Gtk.Label(xalign=0); self.lbl_welcome_warn.set_line_wrap(True)

        big_img = None
        pb = load_scaled_pixbuf(ICON_PATH, 280, 280)
        if pb:
            big_img = Gtk.Image.new_from_pixbuf(pb)
            big_img.set_halign(Gtk.Align.CENTER)

        c.pack_start(self.lbl_welcome_title, False, False, 0)
        if big_img:
            c.pack_start(big_img, False, False, 6)
        c.pack_start(self.lbl_welcome_body, False, False, 0)
        c.pack_start(self.lbl_welcome_warn, False, False, 0)
        c.pack_start(Gtk.Label(label=""), True, True, 0)

        self.page_welcome = wrap_with_corner_logo(c)
        self.append_page(self.page_welcome)
        self.set_page_type(self.page_welcome, Gtk.AssistantPageType.INTRO)
        self.set_page_complete(self.page_welcome, True)

        
        # Region (Essora Locale manages language + timezone + keyboard)
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        self.lbl_region_title = Gtk.Label(xalign=0)
        c.pack_start(self.lbl_region_title, False, False, 0)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        c.pack_start(grid, False, False, 0)

        # Language / Locale
        self.lbl_language = Gtk.Label(xalign=0)
        grid.attach(self.lbl_language, 0, 0, 1, 1)
        self.ent_locale = Gtk.Entry()
        self.ent_locale.set_editable(False)
        self.ent_locale.set_can_focus(False)
        grid.attach(self.ent_locale, 1, 0, 1, 1)

        # Timezone 
        self.lbl_timezone = Gtk.Label(xalign=0)
        grid.attach(self.lbl_timezone, 0, 1, 1, 1)
        self.ent_timezone = Gtk.Entry()
        self.ent_timezone.set_editable(False)
        self.ent_timezone.set_can_focus(False)
        grid.attach(self.ent_timezone, 1, 1, 1, 1)

        # Keyboard layout 
        self.lbl_kblayout = Gtk.Label(xalign=0)
        grid.attach(self.lbl_kblayout, 0, 2, 1, 1)
        self.ent_kb_layout = Gtk.Entry()
        self.ent_kb_layout.set_editable(False)
        self.ent_kb_layout.set_can_focus(False)
        grid.attach(self.ent_kb_layout, 1, 2, 1, 1)

        # Center button 
        spacer_top = Gtk.Label(label="")
        spacer_top.set_vexpand(True)
        c.pack_start(spacer_top, True, True, 0)

        btn_box = Gtk.Box()
        btn_box.set_halign(Gtk.Align.CENTER)
        self.btn_locale = Gtk.Button()
        self.btn_locale.connect("clicked", self.open_essora_locale)
        btn_box.pack_start(self.btn_locale, False, False, 0)
        c.pack_start(btn_box, False, False, 0)

        spacer_bottom = Gtk.Label(label="")
        spacer_bottom.set_vexpand(True)
        c.pack_start(spacer_bottom, True, True, 0)

        self.page_region = wrap_with_corner_logo(c)
        self.append_page(self.page_region)
        self.set_page_type(self.page_region, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(self.page_region, True)

       # Disk page
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=16)
        self.lbl_disk_title = Gtk.Label(xalign=0)
        c.pack_start(self.lbl_disk_title, False, False, 0)

        topbar = Gtk.Box(spacing=8)
        self.btn_refresh = Gtk.Button()
        self.btn_refresh.connect("clicked", lambda *_: self.refresh_partitions())
        topbar.pack_start(self.btn_refresh, False, False, 0)
        self.btn_gparted = Gtk.Button()
        self.btn_gparted.connect("clicked", self.open_gparted)
        topbar.pack_start(self.btn_gparted, False, False, 0)
        c.pack_start(topbar, False, False, 0)

        # ── Whole disk mode ──────────────────────────────────────────────
        self.chk_whole_disk = Gtk.CheckButton()
        self.chk_whole_disk.set_active(False)
        c.pack_start(self.chk_whole_disk, False, False, 0)

        whole_disk_grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        c.pack_start(whole_disk_grid, False, False, 0)
        self.lbl_whole_disk_target = Gtk.Label(xalign=0)
        whole_disk_grid.attach(self.lbl_whole_disk_target, 0, 0, 1, 1)
        self.cmb_whole_disk = Gtk.ComboBoxText()
        whole_disk_grid.attach(self.cmb_whole_disk, 1, 0, 1, 1)
        self.lbl_whole_disk_warn = Gtk.Label(xalign=0)
        self.lbl_whole_disk_warn.set_line_wrap(True)
        whole_disk_grid.attach(self.lbl_whole_disk_warn, 0, 1, 2, 1)

        sep_whole = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        c.pack_start(sep_whole, False, False, 4)

        # Manual partition controls 
        self.manual_disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        c.pack_start(self.manual_disk_box, False, False, 0)

        self.chk_whole_disk.connect("toggled", self._on_whole_disk_toggled)

        grid3 = Gtk.Grid(column_spacing=12, row_spacing=10)
        self.manual_disk_box.pack_start(grid3, False, False, 0)

        self.lbl_efi = Gtk.Label(xalign=0)
        grid3.attach(self.lbl_efi, 0, 0, 1, 1)
        self.cmb_efi = Gtk.ComboBoxText()
        grid3.attach(self.cmb_efi, 1, 0, 1, 1)

        self.lbl_root = Gtk.Label(xalign=0)
        grid3.attach(self.lbl_root, 0, 1, 1, 1)
        self.cmb_root = Gtk.ComboBoxText()
        self.cmb_root.connect("changed", lambda *_: self._disk_changed())
        grid3.attach(self.cmb_root, 1, 1, 1, 1)

        self.chk_format = Gtk.CheckButton()
        self.chk_format.set_active(False)
        self.chk_format.connect("toggled", lambda *_: self.cmb_fs.set_sensitive(bool(self.chk_format.get_active())))
        self.manual_disk_box.pack_start(self.chk_format, False, False, 0)

        fsgrid = Gtk.Grid(column_spacing=12, row_spacing=10)
        self.manual_disk_box.pack_start(fsgrid, False, False, 0)
        self.lbl_fs = Gtk.Label(xalign=0)
        fsgrid.attach(self.lbl_fs, 0, 0, 1, 1)
        self.cmb_fs = Gtk.ComboBoxText()
        self.cmb_fs.append_text("ext4")
        self.cmb_fs.append_text("ext3")
        self.cmb_fs.set_active(0)
        self.cmb_fs.set_sensitive(False)
        fsgrid.attach(self.cmb_fs, 1, 0, 1, 1)

        self.lbl_label = Gtk.Label(xalign=0)
        self.manual_disk_box.pack_start(self.lbl_label, False, False, 0)

        self.chk_grub = Gtk.CheckButton()
        self.chk_grub.set_active(True)
        self.manual_disk_box.pack_start(self.chk_grub, False, False, 0)

        grid4 = Gtk.Grid(column_spacing=12, row_spacing=10)
        self.manual_disk_box.pack_start(grid4, False, False, 0)
        self.lbl_grubdisk = Gtk.Label(xalign=0)
        grid4.attach(self.lbl_grubdisk, 0, 0, 1, 1)
        self.cmb_grubdisk = Gtk.ComboBoxText()
        grid4.attach(self.cmb_grubdisk, 1, 0, 1, 1)

        self.lbl_bootmode = Gtk.Label(xalign=0)
        c.pack_start(self.lbl_bootmode, False, False, 0)

        self.lbl_disk_warn = Gtk.Label(xalign=0); self.lbl_disk_warn.set_line_wrap(True)
        c.pack_start(self.lbl_disk_warn, False, False, 0)

        c.pack_start(Gtk.Label(label=""), True, True, 0)
        self.page_disk = wrap_with_corner_logo(c)
        self.append_page(self.page_disk)
        self.set_page_type(self.page_disk, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(self.page_disk, True)

        # Account page
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=16)
        self.lbl_account_title = Gtk.Label(xalign=0)
        c.pack_start(self.lbl_account_title, False, False, 0)

        ugrid = Gtk.Grid(column_spacing=12, row_spacing=10)
        c.pack_start(ugrid, False, False, 0)

        self.lbl_hostname = Gtk.Label(xalign=0)
        ugrid.attach(self.lbl_hostname, 0, 0, 1, 1)
        self.ent_host = Gtk.Entry(); self.ent_host.set_text("essora")
        ugrid.attach(self.ent_host, 1, 0, 1, 1)

        self.lbl_user = Gtk.Label(xalign=0)
        ugrid.attach(self.lbl_user, 0, 1, 1, 1)
        self.ent_user = Gtk.Entry(); self.ent_user.set_text("essora")
        ugrid.attach(self.ent_user, 1, 1, 1, 1)

        self.lbl_pass = Gtk.Label(xalign=0)
        ugrid.attach(self.lbl_pass, 0, 2, 1, 1)
        self.ent_pass = Gtk.Entry(); self.ent_pass.set_visibility(False)
        ugrid.attach(self.ent_pass, 1, 2, 1, 1)

        self.lbl_pass2 = Gtk.Label(xalign=0)
        ugrid.attach(self.lbl_pass2, 0, 3, 1, 1)
        self.ent_pass2 = Gtk.Entry(); self.ent_pass2.set_visibility(False)
        ugrid.attach(self.ent_pass2, 1, 3, 1, 1)

        c.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        # SLiM autologin option
        self.chk_slim_autologin = Gtk.CheckButton()
        self.chk_slim_autologin.set_active(True)
        c.pack_start(self.chk_slim_autologin, False, False, 0)

        c.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        self.lbl_rootsec = Gtk.Label(xalign=0)
        c.pack_start(self.lbl_rootsec, False, False, 0)

        self.chk_lock_root = Gtk.CheckButton()
        self.chk_lock_root.set_active(True)
        self.chk_lock_root.connect("toggled", lambda *_: self.validate_user_page())
        c.pack_start(self.chk_lock_root, False, False, 0)

        rgrid = Gtk.Grid(column_spacing=12, row_spacing=10)
        c.pack_start(rgrid, False, False, 0)

        self.lbl_rootpass = Gtk.Label(xalign=0)
        rgrid.attach(self.lbl_rootpass, 0, 0, 1, 1)
        self.ent_root = Gtk.Entry(); self.ent_root.set_visibility(False)
        rgrid.attach(self.ent_root, 1, 0, 1, 1)

        self.lbl_rootpass2 = Gtk.Label(xalign=0)
        rgrid.attach(self.lbl_rootpass2, 0, 1, 1, 1)
        self.ent_root2 = Gtk.Entry(); self.ent_root2.set_visibility(False)
        rgrid.attach(self.ent_root2, 1, 1, 1, 1)

        self.lbl_user_warn = Gtk.Label(xalign=0); self.lbl_user_warn.set_line_wrap(True)
        c.pack_start(self.lbl_user_warn, False, False, 0)

        for w in [self.ent_host, self.ent_user, self.ent_pass, self.ent_pass2, self.ent_root, self.ent_root2]:
            w.connect("changed", lambda *_: self.validate_user_page())

        c.pack_start(Gtk.Label(label=""), True, True, 0)
        self.page_account = wrap_with_corner_logo(c)
        self.append_page(self.page_account)
        self.set_page_type(self.page_account, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(self.page_account, False)

        # Confirmation
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=16)
        self.lbl_confirm_title = Gtk.Label(xalign=0)
        c.pack_start(self.lbl_confirm_title, False, False, 0)

        self.summary = Gtk.TextView(editable=False, monospace=True)
        self.summary.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        sc = Gtk.ScrolledWindow(); sc.set_vexpand(True); sc.add(self.summary)
        c.pack_start(sc, True, True, 0)

        self.chk_confirm = Gtk.CheckButton()
        self.chk_confirm.connect("toggled", lambda *_: self.validate_confirm_page())
        c.pack_start(self.chk_confirm, False, False, 0)

        self.page_confirm = wrap_with_corner_logo(c)
        self.append_page(self.page_confirm)
        self.set_page_type(self.page_confirm, Gtk.AssistantPageType.CONFIRM)
        self.set_page_complete(self.page_confirm, False)

        install_overlay = Gtk.Overlay()

        # Banner image fills the background
        self._inst_banner_paths = []
        self._inst_banner_index = 0
        self._inst_banner_source_id = None
        if os.path.isdir(BANNERS_DIR):
            for fn in sorted(os.listdir(BANNERS_DIR)):
                if fn.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self._inst_banner_paths.append(os.path.join(BANNERS_DIR, fn))
        self.inst_banner_img = Gtk.Image()
        self.inst_banner_img.set_halign(Gtk.Align.FILL)
        self.inst_banner_img.set_valign(Gtk.Align.FILL)
        self.inst_banner_img.set_hexpand(True)
        self.inst_banner_img.set_vexpand(True)
        install_overlay.add(self.inst_banner_img)

        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin=8)
        bottom_bar.set_halign(Gtk.Align.FILL)
        bottom_bar.set_valign(Gtk.Align.END)

        hbox_op = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(18, 18)
        hbox_op.pack_start(self.spinner, False, False, 0)
        self.lbl_current_op = Gtk.Label(xalign=0)
        self.lbl_current_op.set_markup("<b>Preparing installation...</b>")
        self.lbl_current_op.set_ellipsize(3)
        hbox_op.pack_start(self.lbl_current_op, True, True, 0)
        bottom_bar.pack_start(hbox_op, False, False, 0)

        self.pbar = Gtk.ProgressBar(show_text=True)
        self.pbar.set_text("0%")
        self.pbar.set_show_text(True)
        bottom_bar.pack_start(self.pbar, False, False, 0)

        install_overlay.add_overlay(bottom_bar)

        self.output = Gtk.TextView(editable=False, monospace=True)

        self.page_install = wrap_with_corner_logo(install_overlay)
        self.append_page(self.page_install)
        self.set_page_type(self.page_install, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(self.page_install, False)

        fin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._fin_banner_paths = []
        self._fin_banner_index = 0
        self._fin_banner_source_id = None
        if os.path.isdir(BANNERS_DIR):
            for fn in sorted(os.listdir(BANNERS_DIR)):
                if fn.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    self._fin_banner_paths.append(os.path.join(BANNERS_DIR, fn))
        self.fin_banner_img = Gtk.Image()
        self.fin_banner_img.set_halign(Gtk.Align.CENTER)
        self.fin_banner_img.set_size_request(-1, 260)
        fin.pack_start(self.fin_banner_img, False, False, 0)

        # Info area
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=20)
        fin.pack_start(info, True, True, 0)

        self.lbl_finish_title = Gtk.Label()
        self.lbl_finish_title.set_markup("<b><big>Installation complete!</big></b>")
        self.lbl_finish_title.set_halign(Gtk.Align.CENTER)
        info.pack_start(self.lbl_finish_title, False, False, 0)

        self.lbl_finish_sub = Gtk.Label()
        self.lbl_finish_sub.set_text(self.tr("You can now reboot into the new system."))
        self.lbl_finish_sub.set_halign(Gtk.Align.CENTER)
        self.lbl_finish_sub.get_style_context().add_class("dim-label")
        info.pack_start(self.lbl_finish_sub, False, False, 0)

        self.chk_reboot = Gtk.CheckButton()
        self.lbl_btn_reboot = Gtk.Label(label=self.tr("Restart system now"))
        self.chk_reboot.add(self.lbl_btn_reboot)
        self.chk_reboot.set_active(True)
        self.chk_reboot.set_halign(Gtk.Align.CENTER)
        self.chk_reboot.connect("toggled", lambda *_: None)
        info.pack_start(self.chk_reboot, False, False, 0)

        # Progress bar at 100%
        self.pbar_finish = Gtk.ProgressBar(show_text=True)
        self.pbar_finish.set_fraction(1.0)
        self.pbar_finish.set_text("100% ✓")
        fin.pack_start(self.pbar_finish, False, False, 0)

        # Hidden output_finish — log buffer
        self.output_finish = Gtk.TextView(editable=False, monospace=True)
        # lbl_finish_icon kept for compatibility
        self.lbl_finish_icon = Gtk.Label()
        self.lbl_finish_icon.set_no_show_all(True)

        self.page_finish = wrap_with_corner_logo(fin)
        self.append_page(self.page_finish)
        self.set_page_type(self.page_finish, Gtk.AssistantPageType.SUMMARY)
        self.set_page_complete(self.page_finish, True)

    def _on_whole_disk_toggled(self, *_):
        active = self.chk_whole_disk.get_active()
        self.manual_disk_box.set_sensitive(not active)
        self.manual_disk_box.set_visible(not active)
        warn = ""
        if active:
            disk_txt = self.cmb_whole_disk.get_active_text() or ""
            disk = disk_txt.split()[0].strip() if disk_txt.startswith("/dev/") else ""
            if disk:
                warn = self.tr("⚠ ALL DATA ON {disk} WILL BE ERASED!", disk=disk)
        self.lbl_whole_disk_warn.set_markup(
            f"<b><span foreground='red'>{warn}</span></b>" if warn else ""
        )
        self._disk_changed()

    def get_whole_disk(self) -> str:
        t = self.cmb_whole_disk.get_active_text() or ""
        return t.split()[0].strip() if t.startswith("/dev/") else ""

    def refresh_partitions(self):
        self.part_rows = list_partitions()
        self.disk_rows = list_disks()

        self.cmb_grubdisk.remove_all()
        self.cmb_whole_disk.remove_all()
        for d in self.disk_rows:
            path = d.get("path") or ""
            size = d.get("size") or ""
            model = d.get("model") or ""
            if path:
                label = f"{path} ({size}) {model}".strip()
                self.cmb_grubdisk.append_text(label)
                self.cmb_whole_disk.append_text(label)
        if self.disk_rows:
            self.cmb_grubdisk.set_active(0)
            self.cmb_whole_disk.set_active(0)

        uefi = is_uefi_firmware()
        efi_candidates = [p for p in self.part_rows if is_efi_candidate(p)]
        vfat_parts = [p for p in self.part_rows if (p.get("fstype") or "").lower() in ("vfat", "fat32", "fat")]
        root_candidates = [p for p in self.part_rows if is_root_candidate(p)]
        root_candidates.sort(key=lambda p: parse_size_to_bytes(p.get("size") or ""), reverse=True)

        def uniq(parts):
            seen = set(); out = []
            for x in parts:
                k = x.get("path") or ""
                if k and k not in seen:
                    seen.add(k); out.append(x)
            return out

        efi_list = uniq(efi_candidates + vfat_parts)

        self.cmb_efi.remove_all()
        if not uefi:
            self.cmb_efi.append_text("")
        for p in efi_list:
            self.cmb_efi.append_text(part_text(p))
        if uefi and efi_list:
            self.cmb_efi.set_active(0)

        self.cmb_root.remove_all()
        efi_paths = set((p.get("path") or "") for p in efi_list)
        others = [p for p in self.part_rows if (p.get("path") or "") and ((p.get("path") or "") not in efi_paths)]
        ext_others = [p for p in others if (p.get("fstype") or "").lower() in ("ext4", "ext3")]
        non_ext = [p for p in others if p not in ext_others]
        ext_others.sort(key=lambda p: parse_size_to_bytes(p.get("size") or ""), reverse=True)
        root_list = uniq(root_candidates + ext_others + non_ext)
        for p in root_list:
            self.cmb_root.append_text(part_text(p))
        if root_list:
            pick = 0
            for i, p in enumerate(root_list):
                if (p.get("fstype") or "").lower() in ("ext4", "ext3"):
                    pick = i; break
            self.cmb_root.set_active(pick)

        root_dev = self.get_root_device()
        if root_dev:
            auto_disk = parent_disk(root_dev)
            for i, d in enumerate(self.disk_rows):
                if (d.get("path") or "") == auto_disk:
                    self.cmb_grubdisk.set_active(i)
                    break

        fw = "UEFI" if uefi else "BIOS/Legacy"
        self.lbl_bootmode.set_text(self.tr("Detected firmware mode: {fw}", fw=fw))
        self._disk_changed()

    def _disk_changed(self):
        txt = self.cmb_root.get_active_text() or ""
        fstype = ""
        for token in txt.split():
            if token.lower() in ("ext4", "ext3", "vfat", "fat32", "fat", "ntfs", "xfs", "btrfs"):
                fstype = token.lower()
                break
        if not self.chk_format.get_active() and fstype and fstype not in ("ext4", "ext3"):
            self.lbl_disk_warn.set_text(self.tr("Root partition should be ext4/ext3, or enable formatting."))
        else:
            self.lbl_disk_warn.set_text("")

    def validate_user_page(self):
        host = self.ent_host.get_text().strip()
        user = self.ent_user.get_text().strip()
        p1 = self.ent_pass.get_text()
        p2 = self.ent_pass2.get_text()
        r1 = self.ent_root.get_text()
        r2 = self.ent_root2.get_text()

        ok = True
        msg = ""

        if not host or " " in host:
            ok = False; msg = self.tr("Invalid hostname.")
        elif not user or " " in user:
            ok = False; msg = self.tr("Invalid username.")
        elif len(p1) < 4:
            ok = False; msg = self.tr("User password is too short (min 4).")
        elif p1 != p2:
            ok = False; msg = self.tr("User passwords do not match.")
        else:
            if r1 or r2:
                if len(r1) < 4:
                    ok = False; msg = self.tr("Root password is too short (min 4).")
                elif r1 != r2:
                    ok = False; msg = self.tr("Root passwords do not match.")
                elif self.chk_lock_root.get_active():
                    msg = self.tr("Note: you set a root password but 'Lock root' is enabled. It will be disabled automatically.")

        self.lbl_user_warn.set_text(msg)
        self.set_page_complete(self.page_account, ok)
        return ok

    def validate_confirm_page(self):
        user_ok = self.get_page_complete(self.page_account)
        ok = bool(self.chk_confirm.get_active()) and bool(user_ok)
        self.set_page_complete(self.page_confirm, ok)
        return ok

    def on_prepare(self, assistant, page):
        if page == self.page_install:
            self._start_banner_slideshow()
            return
        if page == self.page_finish:
            
            return
        if page == self.page_confirm:
            whole_disk_mode = self.chk_whole_disk.get_active()
            tz = self.get_timezone_value()
            kb_layout = self.get_kb_layout()
            kb_model = self.get_kb_model()
            uefi = is_uefi_firmware()
            fw = "UEFI" if uefi else "BIOS/Legacy"
            root_pw = self.ent_root.get_text().strip()
            lock_root = self.chk_lock_root.get_active()
            root_status = self.tr("password set") if root_pw else (self.tr("locked") if lock_root else self.tr("unchanged"))
            yes = self.tr("yes"); no = self.tr("no")
            none = self.tr("(none)")

            lines = []
            lines.append(self.tr("Time zone: {tz}", tz=tz))
            lines.append(self.tr("Keyboard: layout={layout}, model={model}", layout=kb_layout, model=kb_model))
            lines.append(self.tr("Firmware: {fw}", fw=fw))

            if whole_disk_mode:
                disk = self.get_whole_disk()
                ram = _backend.get_ram_bytes()
                swap_gb = _backend.calc_swap_size_bytes(ram) / 1024**3
                lines.append(self.tr("Mode: Whole disk (automatic partitioning)"))
                lines.append(self.tr("Target disk: {disk}", disk=disk or none))
                lines.append(f"  EFI partition: 1024 MiB (FAT32)" if uefi else "  No EFI partition (BIOS mode)")
                lines.append(f"  Swap: {swap_gb:.1f} GB")
                lines.append(f"  Root (/): remaining space (ext4, label: essora)")
                lines.append(self.tr("Install GRUB: {val}", val=yes))
                lines.append(self.tr("GRUB disk: {dev}", dev=disk or none))
            else:
                root_dev = self.get_root_device()
                efi_dev = self.get_efi_device()
                grub_disk = self.get_grub_disk()
                fs = self.get_fs_value()
                fmt = self.chk_format.get_active()
                grub_val = yes if self.chk_grub.get_active() else no
                efi_show = efi_dev if efi_dev else none
                if fmt:
                    lines.append(self.tr("Root (/): {dev} (format: {yes}, fs: {fs}, label: essora)", dev=root_dev, yes=yes, fs=fs))
                else:
                    lines.append(self.tr("Root (/): {dev} (format: {no})", dev=root_dev, no=no))
                lines.append(self.tr("Boot/EFI (ESP): {dev}", dev=efi_show))
                lines.append(self.tr("Install GRUB: {val}", val=grub_val))
                lines.append(self.tr("GRUB disk: {dev}", dev=grub_disk))

            lines.append(self.tr("Hostname: {host}", host=self.ent_host.get_text().strip()))
            lines.append(self.tr("Username: {user}", user=self.ent_user.get_text().strip()))
            lines.append(self.tr("Root: {status}", status=root_status))

            buf = self.summary.get_buffer()
            buf.set_text("\n".join(lines) + "\n")
            self.validate_confirm_page()

    def on_apply(self, *_):
        self.set_current_page(5)

        uefi = is_uefi_firmware()
        whole_disk_mode = self.chk_whole_disk.get_active()
        whole_disk = self.get_whole_disk() if whole_disk_mode else ""

        root_pw = self.ent_root.get_text().strip()
        lock_root = self.chk_lock_root.get_active()
        if root_pw and lock_root:
            lock_root = False

        if whole_disk_mode:
            if not whole_disk:
                self.log("ERROR: No disk selected for whole-disk mode.")
                return

            plan = InstallPlan(
                root_part="__WHOLE_DISK__",   
                efi_part=None,
                format_root=True,
                root_fstype="ext4",
                timezone=self.get_timezone_value(),
                hostname=self.ent_host.get_text().strip(),
                username=self.ent_user.get_text().strip(),
                password=self.ent_pass.get_text(),
                root_password=root_pw,
                lock_root=lock_root,
                kb_layout=self.get_kb_layout(),
                kb_model=self.get_kb_model(),
                kb_variant=(getattr(self, "_kb_variant", "") or "").strip(),
                kb_options=(getattr(self, "_kb_options", "") or "").strip(),
                install_grub=True,
                grub_disk=whole_disk,
                uefi=uefi,
                slim_autologin=self.chk_slim_autologin.get_active(),
                format_swap=True,
            )
        else:
            root_dev = self.get_root_device()
            if not root_dev:
                self.log("ERROR: No root partition selected.")
                return
            efi_dev = self.get_efi_device() or None
            grub_disk = self.get_grub_disk() or parent_disk(root_dev)
            plan = InstallPlan(
                root_part=root_dev,
                efi_part=efi_dev,
                format_root=self.chk_format.get_active(),
                root_fstype=self.get_fs_value(),
                timezone=self.get_timezone_value(),
                hostname=self.ent_host.get_text().strip(),
                username=self.ent_user.get_text().strip(),
                password=self.ent_pass.get_text(),
                root_password=root_pw,
                lock_root=lock_root,
                kb_layout=self.get_kb_layout(),
                kb_model=self.get_kb_model(),
                kb_variant=(getattr(self, "_kb_variant", "") or "").strip(),
                kb_options=(getattr(self, "_kb_options", "") or "").strip(),
                install_grub=self.chk_grub.get_active(),
                grub_disk=grub_disk,
                uefi=uefi,
                slim_autologin=self.chk_slim_autologin.get_active(),
            )

        self.set_sensitive(False)
        self.spinner.start()
        self._pulse_source_id = GLib.timeout_add(19000, self._rsync_tick)
        self._screensaver_source_id = GLib.timeout_add(50000, self._inhibit_screensaver)
        self._inhibit_screensaver()

        _whole_disk = whole_disk  

        def worker():
            try:
                def log_fn(m): GLib.idle_add(self.log, m)
                def prog_fn(v): GLib.idle_add(self.set_progress, v)
                log_fn("== Starting installation ==")
                if whole_disk_mode:
                    log_fn(f"── Partitioning whole disk {_whole_disk}...")
                    parts = partition_whole_disk(_whole_disk, uefi, log_fn)
                    plan.root_part = parts["root_part"]
                    plan.efi_part  = parts["efi_part"]
                    plan.swap_part = parts["swap_part"]
                    plan.grub_disk = _whole_disk
                do_install(plan, log_fn, prog_fn)
                GLib.idle_add(self.log, "✅ Done. Reboot into the installed system.")
                GLib.idle_add(self._show_finish_page, True)
            except Exception as e:
                GLib.idle_add(self.log, f"ERROR: {e}")
                GLib.idle_add(self._show_finish_page, False)
                GLib.idle_add(self.message, self.tr("Error"), str(e), Gtk.MessageType.ERROR)
            finally:
                GLib.idle_add(self.set_sensitive, True)

        threading.Thread(target=worker, daemon=True).start()


    def _rsync_tick(self) -> bool:
        current = self.pbar.get_fraction()
        if 0.10 <= current < 0.77:
            new_val = min(current + 0.01, 0.77)
            self.pbar.set_fraction(new_val)
            pct = int(new_val * 100)
            self.pbar.set_text(f"{pct}%")
            self.pbar_finish.set_fraction(new_val)
            self.pbar_finish.set_text(f"{pct}%")
        return True

    def _inhibit_screensaver(self) -> bool:
        try:
            import subprocess, os
            env = os.environ.copy()
            subprocess.Popen(
                ["xdg-screensaver", "reset"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            subprocess.Popen(
                ["xset", "s", "reset"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        return True  

    def _start_banner_slideshow(self):
        """Start banners on the install page."""
        if not self._inst_banner_paths:
            return
        self._inst_banner_index = 0
        self._inst_banner_source_id = None
        self._inst_render_banner()
        self._inst_banner_source_id = GLib.timeout_add_seconds(8, self._inst_next_banner)

    def _inst_render_banner(self):
        if not self._inst_banner_paths:
            return
        try:
            alloc = self.inst_banner_img.get_allocation()
            w = alloc.width if alloc.width > 10 else 860
            h = alloc.height if alloc.height > 10 else 400
            pb = GdkPixbuf.Pixbuf.new_from_file(self._inst_banner_paths[self._inst_banner_index])
            # Scale to fill width, preserve aspect
            scale = w / pb.get_width()
            nh = int(pb.get_height() * scale)
            scaled = pb.scale_simple(w, max(nh, h), GdkPixbuf.InterpType.BILINEAR)
            self.inst_banner_img.set_from_pixbuf(scaled)
        except Exception as e:
            print(f"[BANNER] {e}")

    def _inst_next_banner(self) -> bool:
        if not self._inst_banner_paths:
            return False
        self._inst_banner_index = (self._inst_banner_index + 1) % len(self._inst_banner_paths)
        self._inst_render_banner()
        return True

    def _stop_banner_slideshow(self):
        if getattr(self, "_inst_banner_source_id", None):
            GLib.source_remove(self._inst_banner_source_id)
            self._inst_banner_source_id = None

    def _start_fin_banner(self):
        """Start banners on the finish page."""
        if not self._fin_banner_paths:
            return
        self._fin_banner_index = 0
        self._fin_render_banner()
        self._fin_banner_source_id = GLib.timeout_add_seconds(8, self._fin_next_banner)

    def _fin_render_banner(self):
        if not self._fin_banner_paths:
            return
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(self._fin_banner_paths[self._fin_banner_index])
            scaled = pb.scale_simple(600, 260, GdkPixbuf.InterpType.BILINEAR)
            self.fin_banner_img.set_from_pixbuf(scaled)
        except Exception as e:
            print(f"[FIN BANNER] {e}")

    def _fin_next_banner(self) -> bool:
        if not self._fin_banner_paths:
            return False
        self._fin_banner_index = (self._fin_banner_index + 1) % len(self._fin_banner_paths)
        self._fin_render_banner()
        return True

    def _show_finish_page(self, success: bool):
        if hasattr(self, "_pulse_source_id") and self._pulse_source_id:
            GLib.source_remove(self._pulse_source_id)
            self._pulse_source_id = None
        if hasattr(self, "_screensaver_source_id") and self._screensaver_source_id:
            GLib.source_remove(self._screensaver_source_id)
            self._screensaver_source_id = None
        self._stop_banner_slideshow()
        self.spinner.stop()

        if success:
            self.lbl_finish_title.set_markup(f"<b><big>{self.tr('Installation complete!')}</big></b>")
            self.lbl_finish_sub.set_text(self.tr("You can now reboot into the new system."))
            self.lbl_current_op.set_markup(f"<b>{self.tr('Installation complete!')}</b>")
            self.pbar_finish.set_fraction(1.0)
            self.pbar_finish.set_text("100% ✓")
            self.pbar.set_fraction(1.0)
            self.pbar.set_text("100% ✓")
            # Start finish page banners
            GLib.idle_add(self._start_fin_banner)
        else:
            self.lbl_finish_title.set_markup(f"<b><big>{self.tr('Installation failed')}</big></b>")
            self.lbl_finish_sub.set_text(self.tr("Please check the log for details."))
            self.lbl_current_op.set_markup(f"<b>{self.tr('Installation failed')}</b>")
            self.pbar_finish.set_fraction(0.0)
            self.pbar_finish.set_text("Error")

        self.set_page_complete(self.page_install, True)
        self.next_page()

    def _on_reboot_clicked(self, *_):
        import subprocess, os
        FAST_REBOOT = "/usr/local/bin/fast-reboot"
        cmd = [FAST_REBOOT] if os.path.exists(FAST_REBOOT) else ["reboot"]
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            self.message(self.tr("Error"), str(e), Gtk.MessageType.ERROR)

    def _on_finish_done(self, *_):
        """Called when user clicks Done/Hecho on finish page."""
        if getattr(self, "chk_reboot", None) and self.chk_reboot.get_active():
            self._on_reboot_clicked()
        else:
            self._quit()

def main():
    win = Installer()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

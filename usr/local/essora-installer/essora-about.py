#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2026 Essora Linux
# Autor: josejp2424
#
# essora-about.py — Ventana "Acerca de" para Essora Installer
# Estilo GNOME 3: HeaderBar, sin decoraciones del sistema, fondo oscuro.
# URLs copiables (compatible con ejecución como root).

import os
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Pango, Gdk

# Rutas
ICON_PATH  = "/usr/local/essora-installer/icons/essora-installer.png"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VERSION    = "1.2"
COPYRIGHT  = "© 2026 josejp2424 — Essora Linux"
GITHUB_URL = "https://github.com/josejp2424"
SF_URL     = "https://sourceforge.net/projects/essora/"

# CSS — estilo GNOME 3 oscuro

_CSS = b"""
window.about-window {
    background-color: #2d2d2d;
}
headerbar.about-header {
    background-color: #1e1e1e;
    border-bottom: 1px solid #111;
    min-height: 42px;
}
headerbar.about-header .title {
    color: #e0e0e0;
    font-weight: bold;
    font-size: 13px;
}
.about-name {
    font-size: 22px;
    font-weight: bold;
    color: #f0f0f0;
}
.about-version {
    font-size: 12px;
    color: #999;
}
.about-copyright {
    font-size: 11px;
    color: #888;
}
.about-desc {
    font-size: 12px;
    color: #ccc;
}
.about-section-title {
    font-size: 11px;
    font-weight: bold;
    color: #aaa;
}
.about-url-label {
    font-size: 11px;
    color: #7abfff;
    font-family: monospace;
}
.about-url-box {
    background-color: #1a1a1a;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 4px 8px;
}
.about-copy-btn {
    background-color: #3d3d3d;
    color: #ccc;
    border: 1px solid #555;
    border-radius: 4px;
    font-size: 11px;
    padding: 2px 8px;
}
.about-copy-btn:hover {
    background-color: #4a4a4a;
    color: #fff;
}
.about-tab-label {
    font-size: 12px;
    color: #ccc;
    padding: 2px 8px;
}
.about-license-view {
    background-color: #1e1e1e;
    color: #bbb;
    font-size: 11px;
    font-family: monospace;
}
.close-button {
    background-color: #3d3d3d;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px 18px;
    font-size: 12px;
}
.close-button:hover {
    background-color: #505050;
    color: #fff;
}
"""

# Traducciones embebidas
_T = {
    "en": {
        "title":        "About Essora Installer",
        "tab_info":     "Information",
        "tab_license":  "License",
        "description":  (
            "Essora Installer is the graphical installer for Essora Linux.\n"
            "It copies the live system to disk and configures the user account,\n"
            "time zone, keyboard layout, and GRUB bootloader.\n\n"
            "Simple, modern and multilingual — inspired by Calamares."
        ),
        "based_on":     "Based on Devuan GNU/Linux with OpenRC",
        "author":       "Author: josejp2424",
        "links_title":  "PROJECT LINKS",
        "copy_tip":     "Copy URL",
        "copied":       "Copied!",
        "close":        "Close",
        "license_body": (
            "This program is free software: you can redistribute it and/or\n"
            "modify it under the terms of the GNU General Public License as\n"
            "published by the Free Software Foundation, either version 3 of\n"
            "the License, or (at your option) any later version.\n\n"
            "This program is distributed in the hope that it will be useful,\n"
            "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the\n"
            "GNU General Public License for more details.\n\n"
            "You should have received a copy of the GNU General Public License\n"
            "along with this program. If not, see:\n"
            "https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "es": {
        "title":        "Acerca de Essora Installer",
        "tab_info":     "Información",
        "tab_license":  "Licencia",
        "description":  (
            "Essora Installer es el instalador gráfico de Essora Linux.\n"
            "Copia el sistema live al disco y configura la cuenta de usuario,\n"
            "zona horaria, distribución de teclado y el gestor de arranque GRUB.\n\n"
            "Simple, moderno y multilingüe — inspirado en Calamares."
        ),
        "based_on":     "Basado en Devuan GNU/Linux con OpenRC",
        "author":       "Autor: josejp2424",
        "links_title":  "ENLACES DEL PROYECTO",
        "copy_tip":     "Copiar URL",
        "copied":       "¡Copiado!",
        "close":        "Cerrar",
        "license_body": (
            "Este programa es software libre: usted puede redistribuirlo y/o\n"
            "modificarlo bajo los términos de la Licencia Pública General GNU\n"
            "publicada por la Free Software Foundation, ya sea la versión 3\n"
            "de la Licencia, o (a su elección) cualquier versión posterior.\n\n"
            "Este programa se distribuye con la esperanza de que sea útil,\n"
            "pero SIN GARANTÍA ALGUNA; ni siquiera la garantía implícita de\n"
            "COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.\n\n"
            "Consulte la Licencia Pública General GNU para más detalles:\n"
            "https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "fr": {
        "title":        "À propos d'Essora Installer",
        "tab_info":     "Informations",
        "tab_license":  "Licence",
        "description":  (
            "Essora Installer est l'installateur graphique d'Essora Linux.\n"
            "Il copie le système live sur le disque et configure le compte utilisateur,\n"
            "le fuseau horaire, la disposition du clavier et le chargeur GRUB.\n\n"
            "Simple, moderne et multilingue — inspiré de Calamares."
        ),
        "based_on":     "Basé sur Devuan GNU/Linux avec OpenRC",
        "author":       "Auteur : josejp2424",
        "links_title":  "LIENS DU PROJET",
        "copy_tip":     "Copier l'URL",
        "copied":       "Copié !",
        "close":        "Fermer",
        "license_body": (
            "Ce programme est un logiciel libre : vous pouvez le redistribuer\n"
            "et/ou le modifier selon les termes de la Licence Publique Générale\n"
            "GNU publiée par la Free Software Foundation (version 3 ou ultérieure).\n\n"
            "Ce programme est distribué sans aucune garantie.\n\n"
            "Voir : https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "it": {
        "title":        "Informazioni su Essora Installer",
        "tab_info":     "Informazioni",
        "tab_license":  "Licenza",
        "description":  (
            "Essora Installer è il programma di installazione grafico di Essora Linux.\n"
            "Copia il sistema live sul disco e configura l'account utente,\n"
            "il fuso orario, il layout della tastiera e il boot loader GRUB.\n\n"
            "Semplice, moderno e multilingue — ispirato a Calamares."
        ),
        "based_on":     "Basato su Devuan GNU/Linux con OpenRC",
        "author":       "Autore: josejp2424",
        "links_title":  "LINK DEL PROGETTO",
        "copy_tip":     "Copia URL",
        "copied":       "Copiato!",
        "close":        "Chiudi",
        "license_body": (
            "Questo programma è software libero: puoi redistribuirlo e/o modificarlo\n"
            "secondo i termini della GNU GPL versione 3 o successiva.\n\n"
            "Vedere: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "pt": {
        "title":        "Sobre o Essora Installer",
        "tab_info":     "Informação",
        "tab_license":  "Licença",
        "description":  (
            "O Essora Installer é o instalador gráfico do Essora Linux.\n"
            "Copia o sistema live para o disco e configura a conta do utilizador,\n"
            "fuso horário, layout do teclado e o gestor de arranque GRUB.\n\n"
            "Simples, moderno e multilingue — inspirado no Calamares."
        ),
        "based_on":     "Baseado em Devuan GNU/Linux com OpenRC",
        "author":       "Autor: josejp2424",
        "links_title":  "LIGAÇÕES DO PROJETO",
        "copy_tip":     "Copiar URL",
        "copied":       "Copiado!",
        "close":        "Fechar",
        "license_body": (
            "Este programa é software livre: você pode redistribuí-lo e/ou modificá-lo\n"
            "nos termos da GNU GPL versão 3 ou posterior.\n\n"
            "Ver: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "ca": {
        "title":        "Quant a Essora Installer",
        "tab_info":     "Informació",
        "tab_license":  "Llicència",
        "description":  (
            "Essora Installer és l'instal·lador gràfic d'Essora Linux.\n"
            "Copia el sistema live al disc i configura el compte d'usuari,\n"
            "la zona horària, la distribució del teclat i el carregador GRUB.\n\n"
            "Simple, modern i multilingüe — inspirat en Calamares."
        ),
        "based_on":     "Basat en Devuan GNU/Linux amb OpenRC",
        "author":       "Autor: josejp2424",
        "links_title":  "ENLLAÇOS DEL PROJECTE",
        "copy_tip":     "Copia l'URL",
        "copied":       "Copiat!",
        "close":        "Tanca",
        "license_body": (
            "Aquest programa és programari lliure sota la GNU GPL v3 o posterior.\n\n"
            "Vegeu: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "hu": {
        "title":        "Az Essora Installer névjegye",
        "tab_info":     "Információ",
        "tab_license":  "Licenc",
        "description":  (
            "Az Essora Installer az Essora Linux grafikus telepítője.\n"
            "A live rendszert másolja lemezre, és beállítja a felhasználói fiókot,\n"
            "az időzónát, a billentyűzetkiosztást és a GRUB rendszertöltőt.\n\n"
            "Egyszerű, modern és többnyelvű — a Calamares alapján."
        ),
        "based_on":     "Alapja: Devuan GNU/Linux OpenRC-vel",
        "author":       "Szerző: josejp2424",
        "links_title":  "PROJEKT HIVATKOZÁSOK",
        "copy_tip":     "URL másolása",
        "copied":       "Másolva!",
        "close":        "Bezárás",
        "license_body": (
            "Ez a program szabad szoftver a GNU GPL 3. verziója alapján.\n\n"
            "Lásd: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "ru": {
        "title":        "О программе Essora Installer",
        "tab_info":     "Информация",
        "tab_license":  "Лицензия",
        "description":  (
            "Essora Installer — графический установщик Essora Linux.\n"
            "Копирует live-систему на диск и настраивает учётную запись,\n"
            "часовой пояс, раскладку клавиатуры и загрузчик GRUB.\n\n"
            "Простой, современный и многоязычный — по образцу Calamares."
        ),
        "based_on":     "Основан на Devuan GNU/Linux с OpenRC",
        "author":       "Автор: josejp2424",
        "links_title":  "ССЫЛКИ ПРОЕКТА",
        "copy_tip":     "Копировать URL",
        "copied":       "Скопировано!",
        "close":        "Закрыть",
        "license_body": (
            "Программа распространяется по лицензии GNU GPL версии 3 или выше.\n\n"
            "Подробнее: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "ja": {
        "title":        "Essora Installer について",
        "tab_info":     "情報",
        "tab_license":  "ライセンス",
        "description":  (
            "Essora Installer は Essora Linux のグラフィカルインストーラです。\n"
            "live システムをディスクにコピーし、ユーザーアカウント、\n"
            "タイムゾーン、キーボードレイアウト、GRUB を設定します。\n\n"
            "シンプル・モダン・多言語対応 — Calamares にインスパイア。"
        ),
        "based_on":     "ベース: Devuan GNU/Linux (OpenRC)",
        "author":       "作者: josejp2424",
        "links_title":  "プロジェクトリンク",
        "copy_tip":     "URLをコピー",
        "copied":       "コピー済み!",
        "close":        "閉じる",
        "license_body": (
            "このプログラムは GNU GPL バージョン3以降のもとで配布されます。\n\n"
            "詳細: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "zh": {
        "title":        "关于 Essora 安装程序",
        "tab_info":     "信息",
        "tab_license":  "许可证",
        "description":  (
            "Essora Installer 是 Essora Linux 的图形安装程序。\n"
            "将 live 系统复制到磁盘并配置用户账户、\n"
            "时区、键盘布局和 GRUB 引导加载程序。\n\n"
            "简洁、现代、多语言 — 受 Calamares 启发。"
        ),
        "based_on":     "基于 Devuan GNU/Linux（OpenRC）",
        "author":       "作者：josejp2424",
        "links_title":  "项目链接",
        "copy_tip":     "复制 URL",
        "copied":       "已复制！",
        "close":        "关闭",
        "license_body": (
            "本程序基于 GNU GPL 第3版或更高版本发布。\n\n"
            "详见：https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
    "ar": {
        "title":        "حول Essora Installer",
        "tab_info":     "معلومات",
        "tab_license":  "الرخصة",
        "description":  (
            "Essora Installer هو برنامج التثبيت الرسومي لـ Essora Linux.\n"
            "ينسخ نظام live إلى القرص ويضبط حساب المستخدم،\n"
            "المنطقة الزمنية، تخطيط لوحة المفاتيح وـ GRUB.\n\n"
            "بسيط وحديث ومتعدد اللغات — مستوحى من Calamares."
        ),
        "based_on":     "مبني على Devuan GNU/Linux مع OpenRC",
        "author":       "المطور: josejp2424",
        "links_title":  "روابط المشروع",
        "copy_tip":     "نسخ الرابط",
        "copied":       "تم النسخ!",
        "close":        "إغلاق",
        "license_body": (
            "يُوزَّع هذا البرنامج بموجب رخصة GNU GPL الإصدار 3 أو أحدث.\n\n"
            "انظر: https://www.gnu.org/licenses/gpl-3.0.html"
        ),
    },
}


def _detect_lang() -> str:
    env = (
        os.environ.get("LC_ALL") or
        os.environ.get("LANG") or
        os.environ.get("LANGUAGE") or ""
    ).split(".")[0].split("_")[0].lower().strip()
    return env if env in _T else "en"


def _t(lang: str, key: str) -> str:
    return _T.get(lang, _T["en"]).get(key, _T["en"].get(key, ""))


def _load_pixbuf(size: int):
    candidates = [
        ICON_PATH,
        os.path.join(SCRIPT_DIR, "icons", "essora-installer.png"),
        os.path.join(SCRIPT_DIR, "essora-installer.png"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(p)
                w, h = pb.get_width(), pb.get_height()
                scale = size / max(w, h, 1)
                nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
                return pb.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
            except Exception:
                pass
    return None


def _apply_css():
    provider = Gtk.CssProvider()
    css_data = _CSS if isinstance(_CSS, bytes) else _CSS.encode("utf-8")
    try:
        provider.load_from_data(css_data)
    except Exception:
        try:
            provider.load_from_data(css_data.decode("utf-8"))
        except Exception:
            pass 
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

class UrlRow(Gtk.Box):
    def __init__(self, label_text: str, url: str, copy_tip: str, copied_text: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.url = url
        self._copied_text = copied_text


        icon_name = "emblem-web-symbolic" if "github" not in url else "system-software-update-symbolic"

        lbl_name = Gtk.Label(label=label_text)
        lbl_name.set_xalign(0)
        lbl_name.get_style_context().add_class("about-section-title")
        lbl_name.set_width_chars(12)

        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        url_box.get_style_context().add_class("about-url-box")

        lbl_url = Gtk.Label(label=url)
        lbl_url.set_xalign(0)
        lbl_url.set_selectable(True)  # seleccionable con mouse
        lbl_url.get_style_context().add_class("about-url-label")
        url_box.pack_start(lbl_url, True, True, 0)

        self.btn_copy = Gtk.Button(label=copy_tip)
        self.btn_copy.get_style_context().add_class("about-copy-btn")
        self.btn_copy.set_tooltip_text(copy_tip)
        self.btn_copy.connect("clicked", self._on_copy)

        self.pack_start(lbl_name, False, False, 0)
        self.pack_start(url_box, True, True, 0)
        self.pack_start(self.btn_copy, False, False, 0)

        self._copy_timer = None

    def _on_copy(self, *_):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.url, -1)
        clipboard.store()

        self.btn_copy.set_label(self._copied_text)
        self.btn_copy.get_style_context().add_class("copied")

        if self._copy_timer:
            from gi.repository import GLib
            GLib.source_remove(self._copy_timer)

        from gi.repository import GLib
        self._copy_timer = GLib.timeout_add(1800, self._reset_button)

    def _reset_button(self):
        self.btn_copy.set_label(self.btn_copy.get_tooltip_text())
        self.btn_copy.get_style_context().remove_class("copied")
        self._copy_timer = None
        return False

class AboutEssora(Gtk.Window):
    def __init__(self, lang: str = ""):
        super().__init__()
        self.lang = lang.strip().lower() if lang else _detect_lang()
        _apply_css()
        self._build()
        self.show_all()

    def _build(self):
        lg = self.lang
        self.set_decorated(False)          
        self.set_resizable(False)
        self.set_default_size(540, 640)
        self.set_position(Gtk.WindowPosition.CENTER)  
        self.get_style_context().add_class("about-window")
        pb_icon = _load_pixbuf(48)
        if pb_icon:
            self.set_icon(pb_icon)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)   
        header.set_title(_t(lg, "title"))
        header.get_style_context().add_class("about-header")
        pb_header = _load_pixbuf(24)
        if pb_header:
            img_h = Gtk.Image.new_from_pixbuf(pb_header)
            header.pack_start(img_h)
        self.set_titlebar(header)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        main_box.pack_start(scroll, True, True, 0)
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        content.set_margin_top(24)
        content.set_margin_bottom(16)
        content.set_margin_start(28)
        content.set_margin_end(28)
        scroll.add(content)
        pb_big = _load_pixbuf(88)
        if pb_big:
            img_big = Gtk.Image.new_from_pixbuf(pb_big)
            img_big.set_halign(Gtk.Align.CENTER)
            img_big.set_margin_bottom(10)
            content.pack_start(img_big, False, False, 0)
        lbl_name = Gtk.Label(label="Essora Installer")
        lbl_name.set_halign(Gtk.Align.CENTER)
        lbl_name.get_style_context().add_class("about-name")
        lbl_name.set_margin_bottom(2)
        content.pack_start(lbl_name, False, False, 0)
        lbl_ver = Gtk.Label(label=f"v{VERSION}")
        lbl_ver.set_halign(Gtk.Align.CENTER)
        lbl_ver.get_style_context().add_class("about-version")
        lbl_ver.set_margin_bottom(4)
        content.pack_start(lbl_ver, False, False, 0)
        lbl_copy = Gtk.Label(label=COPYRIGHT)
        lbl_copy.set_halign(Gtk.Align.CENTER)
        lbl_copy.set_selectable(True)
        lbl_copy.get_style_context().add_class("about-copyright")
        lbl_copy.set_margin_bottom(16)
        content.pack_start(lbl_copy, False, False, 0)

        content.pack_start(
            Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
            False, False, 0
        )
        nb = Gtk.Notebook()
        nb.set_margin_top(14)
        nb.set_margin_bottom(4)
        content.pack_start(nb, True, True, 0)
        info_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        info_box.set_margin_top(14)
        info_box.set_margin_bottom(8)
        info_box.set_margin_start(4)
        info_box.set_margin_end(4)

        lbl_desc = Gtk.Label(label=_t(lg, "description"))
        lbl_desc.set_xalign(0)
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_selectable(True)
        lbl_desc.get_style_context().add_class("about-desc")
        info_box.pack_start(lbl_desc, False, False, 0)

        lbl_based = Gtk.Label(label=_t(lg, "based_on"))
        lbl_based.set_xalign(0)
        lbl_based.set_selectable(True)
        lbl_based.get_style_context().add_class("about-version")
        info_box.pack_start(lbl_based, False, False, 0)

        lbl_author = Gtk.Label(label=_t(lg, "author"))
        lbl_author.set_xalign(0)
        lbl_author.set_selectable(True)
        lbl_author.get_style_context().add_class("about-version")
        info_box.pack_start(lbl_author, False, False, 0)
        info_box.pack_start(
            Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
            False, False, 4,
        )
        lbl_links_title = Gtk.Label(label=_t(lg, "links_title"))
        lbl_links_title.set_xalign(0)
        lbl_links_title.get_style_context().add_class("about-section-title")
        info_box.pack_start(lbl_links_title, False, False, 0)

        copy_tip    = _t(lg, "copy_tip")
        copied_text = _t(lg, "copied")

        row_gh = UrlRow("GitHub", GITHUB_URL, copy_tip, copied_text)
        info_box.pack_start(row_gh, False, False, 0)

        row_sf = UrlRow("SourceForge", SF_URL, copy_tip, copied_text)
        info_box.pack_start(row_sf, False, False, 0)

        lbl_tab1 = Gtk.Label(label=_t(lg, "tab_info"))
        lbl_tab1.get_style_context().add_class("about-tab-label")
        nb.append_page(info_box, lbl_tab1)
        lic_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        lic_scroll = Gtk.ScrolledWindow()
        lic_scroll.set_vexpand(True)
        lic_scroll.set_min_content_height(180)

        lic_view = Gtk.TextView()
        lic_view.set_editable(False)
        lic_view.set_cursor_visible(False)
        lic_view.set_wrap_mode(Gtk.WrapMode.WORD)
        lic_view.set_left_margin(10)
        lic_view.set_right_margin(10)
        lic_view.set_top_margin(10)
        lic_view.set_bottom_margin(10)
        lic_view.get_style_context().add_class("about-license-view")
        lic_view.get_buffer().set_text(_t(lg, "license_body"))
        lic_scroll.add(lic_view)
        lic_box.pack_start(lic_scroll, True, True, 0)

        lbl_tab2 = Gtk.Label(label=_t(lg, "tab_license"))
        lbl_tab2.get_style_context().add_class("about-tab-label")
        nb.append_page(lic_box, lbl_tab2)
        btn_bar = Gtk.Box(spacing=0)
        btn_bar.set_margin_top(8)
        btn_bar.set_margin_bottom(12)
        btn_bar.set_margin_end(0)

        btn_close = Gtk.Button(label=_t(lg, "close"))
        btn_close.get_style_context().add_class("close-button")
        btn_close.set_halign(Gtk.Align.CENTER)
        btn_close.set_hexpand(True)
        btn_close.connect("clicked", lambda *_: self.destroy())
        btn_bar.pack_start(btn_close, True, False, 0)

        main_box.pack_start(btn_bar, False, False, 0)

def show_about(lang: str = "", parent=None):
    win = AboutEssora(lang=lang)
    if parent:
        win.set_transient_for(parent)
        win.set_modal(True)
        win.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        win.connect("destroy", lambda *_: None)
    else:
        win.connect("destroy", Gtk.main_quit)
        Gtk.main()
    return win


if __name__ == "__main__":
    lang_arg = ""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith("--lang="):
            lang_arg = arg.split("=", 1)[1].strip()
        elif arg in ("-l", "--lang") and i < len(sys.argv) - 1:
            lang_arg = sys.argv[i + 1].strip()
    show_about(lang=lang_arg)

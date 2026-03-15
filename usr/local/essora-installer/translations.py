#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2026 Essora Linux
# Autor: josejp2424
#
# translations.py - JSON translations loader for Essora apps
#
# Translation files:
#   /usr/local/essora-installer/lang/<lang>.json
#
# Rule:
#   Keys are ALWAYS the original English strings used in the code.

import json
import os
from typing import Dict, Any


class Translator:
    def __init__(self, lang_dir: str, default_lang: str = "en"):
        self.lang_dir = lang_dir
        self.default_lang = (default_lang or "en").lower().strip()
        self.current_lang = self.default_lang
        self._data: Dict[str, Any] = {}
        self.set_language(self.default_lang)

    def set_language(self, lang_code: str) -> str:
        """Set current language. Returns language actually used (fallback to default)."""
        lang = (lang_code or self.default_lang).lower().strip()

        # English base language: no file needed
        if lang == "en":
            self.current_lang = "en"
            self._data = {}
            return self.current_lang

        lang_file = os.path.join(self.lang_dir, f"{lang}.json")
        if not os.path.exists(lang_file):
            self.current_lang = self.default_lang
            self._data = {}
            return self.current_lang

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Translation JSON is not a dict")
            self._data = data
            self.current_lang = lang
            return self.current_lang
        except Exception:
            self.current_lang = self.default_lang
            self._data = {}
            return self.current_lang

    def tr(self, text: str, **kwargs) -> str:
        """Translate; keys are English strings. Supports format(**kwargs)."""
        out = text
        if self.current_lang != "en" and text in self._data:
            out = str(self._data[text])
        if kwargs:
            try:
                out = out.format(**kwargs)
            except Exception:
                pass
        return out

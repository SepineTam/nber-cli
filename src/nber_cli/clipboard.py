#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : clipboard.py

"""Copy Unicode text using the host's native clipboard commands."""

import os
import shutil
import subprocess
import sys


class ClipboardError(RuntimeError):
    pass


def copy_text(text: str) -> None:
    candidates: list[list[str]] = []
    if sys.platform == "darwin":
        candidates = [["pbcopy"]]
    elif sys.platform == "win32":
        # Read UTF-8 explicitly; clip.exe's input encoding varies by system locale.
        candidates = [["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                       "[Console]::InputEncoding = [System.Text.UTF8Encoding]::new(); "
                       "$text = [Console]::In.ReadToEnd(); Set-Clipboard -Value $text"]]
    else:
        if os.environ.get("WAYLAND_DISPLAY"):
            candidates.append(["wl-copy"])
        if os.environ.get("DISPLAY"):
            candidates.extend([["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]])
    for command in candidates:
        if not shutil.which(command[0]):
            continue
        try:
            # DEVNULL prevents clipboard daemon children from holding pipes open.
            subprocess.run(command, input=text.encode("utf-8"), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=10, check=True)
            return
        except (OSError, subprocess.SubprocessError):
            continue
    raise ClipboardError("No usable clipboard backend. Use --stdout; on Linux install wl-clipboard or xclip in a desktop session.")

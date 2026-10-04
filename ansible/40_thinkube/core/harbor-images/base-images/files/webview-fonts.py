#!/usr/bin/env python3
# Copyright Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0
"""
Gives every webview in the IDE the Thinkube fonts.

VS Code creates each extension panel (webview) from the host page
out/vs/workbench/contrib/webview/browser/pre/index.html. Its one inline script
builds default styles that it adds to every panel document. This adds the
Thinkube @font-face rules to those styles, with the files the IDE serves under
/_static, and makes Poppins the panel text font. The default styles sit in the
lowest cascade layer, so a panel that sets its own font keeps it.

The host page allows its inline script by SHA-256 hash, so the hash is
recomputed. The script stops the build when the page no longer has the shape
this relies on: one inline script whose hash matches the page's policy, and the
default styles text this edits.

Usage: webview-fonts.py <path to pre/index.html>
"""

import base64
import hashlib
import re
import sys

FACES = [
    ("Poppins", "Poppins-Regular", 400),
    ("Poppins", "Poppins-Medium", 500),
    ("Poppins", "Poppins-SemiBold", 600),
    ("Poppins", "Poppins-Bold", 700),
    ("NotoSansM Nerd Font", "NotoSansMNerdFont-Regular", 400),
    ("NotoSansM Nerd Font", "NotoSansMNerdFont-Bold", 700),
]

STYLES_START = "defaultStyles.textContent = `\n"
BODY_FONT = "font-family: var(--vscode-font-family);"


def script_hash(script: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode()


def fail(message: str) -> None:
    sys.exit(f"webview-fonts: {message}")


def main(path: str) -> None:
    page = open(path, encoding="utf-8").read()

    scripts = re.findall(r"<script[^>]*>(.*?)</script>", page, flags=re.S)
    if len(scripts) != 1:
        fail(f"expected one inline script in {path}, found {len(scripts)}")
    script = scripts[0]
    old_hash = script_hash(script)
    if f"'{old_hash}'" not in page:
        fail(f"the page policy does not allow its script by {old_hash}; the hashing no longer matches VS Code's")
    if script.count(STYLES_START) != 1:
        fail("the default styles are no longer built from one template")
    if script.count(BODY_FONT) != 1:
        fail(f"the default styles no longer set the body font with {BODY_FONT!r}")

    faces = "".join(
        f'\t\t@font-face {{ font-family: "{family}"; '
        f'src: url("/_static/src/browser/media/fonts/{file}.woff2") format("woff2"); '
        f"font-weight: {weight}; font-style: normal; }}\n"
        for family, file, weight in FACES
    )
    patched = script.replace(STYLES_START, STYLES_START + faces)
    patched = patched.replace(BODY_FONT, 'font-family: "Poppins", sans-serif;')

    page = page.replace(script, patched).replace(f"'{old_hash}'", f"'{script_hash(patched)}'")
    open(path, "w", encoding="utf-8").write(page)
    print(f"webview-fonts: Thinkube fonts in every webview ({old_hash} -> {script_hash(patched)})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: webview-fonts.py <path to pre/index.html>")
    main(sys.argv[1])

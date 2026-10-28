#!/usr/bin/env python3
"""Render tmux capture-pane -e output, preserving terminal cell widths and SGR."""
import html
from pathlib import Path
import re
import sys
import unicodedata

PALETTE = ['#000000', '#cd0000', '#00cd00', '#cdcd00', '#0000ee', '#cd00cd', '#00cdcd', '#e5e5e5',
           '#7f7f7f', '#ff0000', '#00ff00', '#ffff00', '#5c5cff', '#ff00ff', '#00ffff', '#ffffff']


def color(index):
    if index < 16:
        return PALETTE[index]
    if index < 232:
        value = index - 16
        levels = [0, 95, 135, 175, 215, 255]
        return '#%02x%02x%02x' % (levels[value // 36], levels[value // 6 % 6], levels[value % 6])
    return '#%02x%02x%02x' % ((8 + (index - 232) * 10,) * 3)


def convert(text):
    # Refuse a capture with personal paths, email or common token prefixes.
    if re.search(r'/home/|/Users/|[\w.+-]+@[\w.-]+|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_]{12,}', text):
        raise ValueError('Capture contains a private path, account or possible token; recapture it')
    fg, bg, bold, reverse = '#d8dee9', '#282c34', False, False
    output = []
    for token in re.split(r'(\x1b\[[0-?]*[ -/]*[@-~])', text):
        if token.startswith('\x1b['):
            if not token.endswith('m'):
                continue
            codes = [int(v or 0) for v in token[2:-1].split(';')]
            i = 0
            while i < len(codes):
                code = codes[i]
                if code == 0:
                    fg, bg, bold, reverse = '#d8dee9', '#282c34', False, False
                elif code in (1, 22): bold = code == 1
                elif code in (7, 27): reverse = code == 7
                elif code == 39: fg = '#d8dee9'
                elif code == 49: bg = '#282c34'
                elif 30 <= code <= 37: fg = color(code - 30)
                elif 40 <= code <= 47: bg = color(code - 40)
                elif 90 <= code <= 97: fg = color(code - 90 + 8)
                elif 100 <= code <= 107: bg = color(code - 100 + 8)
                elif code in (38, 48) and i + 2 < len(codes):
                    if codes[i + 1] == 5:
                        value = color(codes[i + 2]); i += 2
                    elif codes[i + 1] == 2 and i + 4 < len(codes):
                        value = '#%02x%02x%02x' % tuple(codes[i + 2:i + 5]); i += 4
                    else:
                        i += 1; continue
                    if code == 38: fg = value
                    else: bg = value
                i += 1
            continue
        for char in token:
            if char == '\n':
                output.append('\n'); continue
            if unicodedata.category(char).startswith('C'):
                continue
            width = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
            front, back = (bg, fg) if reverse else (fg, bg)
            output.append(f'<span style="width:{width}ch;color:{front};background:{back};font-weight:{700 if bold else 400}">{html.escape(char)}</span>')
    return '''<!doctype html><meta charset="utf-8"><title>ask capture</title>
<style>body{margin:0;background:#282c34;color:#d8dee9}pre{margin:0;padding:12px;font:16px/22px "Noto Sans Mono CJK JP",monospace;white-space:pre}span{display:inline-block;text-align:left;height:22px;vertical-align:top}</style><pre>''' + ''.join(output) + '</pre>'


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(convert(Path(sys.argv[1]).read_text()), encoding='utf-8')

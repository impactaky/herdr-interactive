#!/usr/bin/env python3
"""Render tmux capture-pane -e output, preserving terminal cell widths and SGR."""
import html
from pathlib import Path
import re
import sys
import unicodedata

# One Dark, matching Herdr's one-dark theme rather than raw xterm colors.
PALETTE = ['#282c34', '#e06c75', '#98c379', '#e5c07b', '#61afef', '#c678dd', '#56b6c2', '#abb2bf',
           '#5c6370', '#e06c75', '#98c379', '#e5c07b', '#61afef', '#c678dd', '#56b6c2', '#ffffff']
FG = '#abb2bf'


def color(index):
    if index < 16:
        return PALETTE[index]
    if index < 232:
        value = index - 16
        levels = [0, 95, 135, 175, 215, 255]
        return '#%02x%02x%02x' % (levels[value // 36], levels[value // 6 % 6], levels[value % 6])
    return '#%02x%02x%02x' % ((8 + (index - 232) * 10,) * 3)


BLOCKS = {'█': (0, 0, 10, 22), '▌': (0, 0, 5, 22), '▐': (5, 0, 5, 22), '▀': (0, 0, 10, 11), '▄': (0, 11, 10, 11)}


def cell_art(char, front):
    """Draw box-drawing and block glyphs to fill the cell, as terminals do.

    A font glyph rarely spans the full line height, so borders would show gaps.
    """
    svg = '<svg viewBox="0 0 10 22" preserveAspectRatio="none">{}</svg>'
    if char in BLOCKS:
        x, y, w, h = BLOCKS[char]
        return svg.format(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{front}"/>')
    name = unicodedata.name(char, '')
    if not name.startswith('BOX DRAWINGS') or 'DASH' in name:
        return None
    words = name.split()
    ends = {'UP': (5, 0), 'DOWN': (5, 22), 'LEFT': (0, 11), 'RIGHT': (10, 11)}
    sides = {w for w in words if w in ends}
    if 'VERTICAL' in words: sides |= {'UP', 'DOWN'}
    if 'HORIZONTAL' in words: sides |= {'LEFT', 'RIGHT'}
    if not sides:
        return None
    width = 2.4 if 'HEAVY' in words or 'DOUBLE' in words else 1.2
    lines = ''.join(f'<line x1="5" y1="11" x2="{ends[s][0]}" y2="{ends[s][1]}"/>' for s in sorted(sides))
    return svg.format(f'<g stroke="{front}" stroke-width="{width}" stroke-linecap="square" '
                      f'vector-effect="non-scaling-stroke">{lines}</g>')


def convert(text):
    # Refuse a capture with personal paths, email or common token prefixes.
    if re.search(r'/home/|/Users/|[\w.+-]+@[\w.-]+|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_]{12,}', text):
        raise ValueError('Capture contains a private path, account or possible token; recapture it')
    fg, bg, bold, reverse = FG, '#282c34', False, False
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
                    fg, bg, bold, reverse = FG, '#282c34', False, False
                elif code in (1, 22): bold = code == 1
                elif code in (7, 27): reverse = code == 7
                elif code == 39: fg = FG
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
            art = cell_art(char, front)
            body = art if art else html.escape(char)
            output.append(f'<span style="width:{width}ch;color:{front};background:{back};font-weight:{700 if bold else 400}">{body}</span>')
    return '''<!doctype html><meta charset="utf-8"><title>ask capture</title>
<style>body{margin:0;background:#282c34;color:#abb2bf}pre{margin:0;padding:12px;font:16px/22px "PragmataPro Mono","PragmataPro","Noto Sans Mono CJK JP",monospace;white-space:pre}span{display:inline-block;text-align:left;height:22px;vertical-align:top}svg{display:block;width:100%;height:100%}svg line{vector-effect:non-scaling-stroke}</style><pre>''' + ''.join(output) + '</pre>'


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(convert(Path(sys.argv[1]).read_text()), encoding='utf-8')

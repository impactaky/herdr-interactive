"""ANSI snapshot rows and a mouse-aware frozen-pane selector (stdlib only)."""
import os
import re
import select
import sys
import termios
import tty
import unicodedata

RESET = '\x1b[0m'
# pane.read emits SGR and CRLF. Ignore other terminal commands (including OSC
# hyperlinks) rather than replaying commands from the source application.
ESCAPE = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\](?:[^\x07\x1b]|\x1b(?!\\))*(?:\x07|\x1b\\)|[()][A-Za-z0-9]|.)')
SGR = re.compile(r'\x1b\[[0-9;:]*m\Z')


def ansi_rows(text):
    rows, row, style = [], '', ''
    position = 0
    for match in ESCAPE.finditer(text):
        row, style = _characters(text[position:match.start()], rows, row, style)
        code = match.group()
        if SGR.fullmatch(code):
            style = '' if code in ('\x1b[m', RESET) else style + code
            row += code
        position = match.end()
    row, _ = _characters(text[position:], rows, row, style)
    if not rows or not plain(text).endswith('\n'):
        rows.append(row)
    return rows


def _characters(text, rows, row, style):
    for char in text:
        if char == '\n':
            rows.append(row)
            row = style
        elif char == '\t' or not unicodedata.category(char).startswith('C'):
            row += char
    return row, style


def plain(row):
    return ESCAPE.sub('', row)


def cell_width(char):
    if unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1


def crop(row, width, start=0):
    """Keep SGR intact while clipping by terminal cells, including CJK marks."""
    result, column, position = [], 0, 0
    for match in ESCAPE.finditer(row):
        segment, column = _clip(row[position:match.start()], column, width, start)
        result.append(segment)
        result.append(match.group())
        position = match.end()
    segment, _ = _clip(row[position:], column, width, start)
    return ''.join(result) + segment + RESET


def _clip(text, column, width, start=0):
    result = []
    for char in text:
        size = 8 - column % 8 if char == '\t' else cell_width(char)
        if column >= start and column + size <= width:
            result.append(' ' * size if char == '\t' else char)
        elif column < start < column + size <= width:
            result.append(' ' * (column + size - start))
        column += size
    return ''.join(result), column


class Selection:
    def __init__(self, frame):
        self.frame = frame
        self.rows = frame['rows']
        self.top = frame['top']
        self.cursor = self.top
        self.anchor = None
        self.dragging = False
        self.border = 0 if frame.get('scroll', {}).get('viewport_rows') == frame['rect']['height'] else 1
        self.height = max(1, frame['rect']['height'] - 2 * self.border)

    def bounds(self):
        return sorted((self.cursor, self.cursor if self.anchor is None else self.anchor))

    def quote(self):
        start, end = self.bounds()
        return '\n'.join(plain(row).rstrip() for row in self.rows[start:end + 1])

    def move(self, amount):
        self.cursor = min(len(self.rows) - 1, max(0, self.cursor + amount))
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + self.height:
            self.top = self.cursor - self.height + 1

    def handle(self, key):
        if key == '\x1b':
            return 'cancel'
        if key in ('\r', '\n'):
            return 'accept'
        if key in ('k', '\x1b[A'):
            self.move(-1)
        elif key in ('j', '\x1b[B'):
            self.move(1)
        elif key == '\x1b[5~':
            self.move(-self.height)
        elif key == '\x1b[6~':
            self.move(self.height)
        elif key == 'V':
            self.anchor = self.cursor if self.anchor is None else None
        elif key.startswith('\x1b[<'):
            self.mouse(key)
        return None

    def mouse(self, key):
        match = re.fullmatch(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])', key)
        if not match:
            return
        button, x, y = map(int, match.groups()[:3])
        rect = self.frame['rect']
        # SGR mouse coordinates are one-based and include the pane border.
        inset_x, inset_y = getattr(self, 'inset', (0, 0))
        x, y = x - 1 + inset_x, y - 1 + inset_y
        inside = (rect['x'] + self.border <= x < rect['x'] + rect['width'] - self.border
                  and rect['y'] + self.border <= y < rect['y'] + rect['height'] - self.border)
        if not inside and not self.dragging:
            return
        if button in (64, 65):
            self.move(-3 if button == 64 else 3)
            return
        if button & 3 != 0:
            return
        row = min(len(self.rows) - 1, self.top + max(0, min(self.height - 1, y - rect['y'] - self.border)))
        if match[4] == 'M' and not button & 32:
            self.cursor = self.anchor = row
            self.dragging = True
        elif self.dragging:
            self.cursor = row
            if match[4] == 'm':
                self.dragging = False

    def render(self, columns, lines):
        rect, area = self.frame['rect'], self.frame['area']
        # Herdr gives overlay terminals the tab's inner area: its own border
        # consumes one cell on each side. Translate layout coordinates back
        # through that inset, so source content stays in the same screen cells.
        horizontal = area['width'] - columns
        vertical = area['height'] - lines
        if horizontal not in (0, 2, 3) or vertical not in (0, 2):
            raise ValueError('Terminal size changed; restore size and reopen Redpen')
        inset_x, inset_y = int(horizontal > 0), int(vertical > 0)
        gutter = max(0, horizontal - 2)  # Herdr's optional scrollbar column.
        x, y = rect['x'] - inset_x, rect['y'] - inset_y
        width, height = rect['width'], rect['height']
        if (width < 3 or height < 3 or x + 1 < 0 or y + 1 < 0
                or x + width - 2 - gutter >= columns or y + height - 2 >= lines):
            raise ValueError('Source pane does not fit; restore terminal size and reopen Redpen')
        self.height = height - 2 * self.border
        self.inset = (inset_x, inset_y)
        output = [RESET, '\x1b[2J']

        def at(row, column, text):
            if 0 <= row < lines and 0 <= column < columns:
                output.append(f'\x1b[{row + 1};{column + 1}H' + text)

        label = ' Redpen: Enter 次へ / V 範囲 / j,k ↑↓ / PgUp,Dn / Esc '
        at(y, x, '┌' + crop(label, width - 2) + '┐')
        start, end = self.bounds()
        for index in range(self.height):
            row = self.top + index
            mark = '▌' if start <= row <= end else '│'
            if self.border:
                at(y + index + 1, x, RESET + mark)
            content = self.rows[row] if row < len(self.rows) else ''
            if (x < 0 or not self.border) and start <= row <= end:
                # The overlay's own left border is outside our terminal. Use
                # reverse video there without shifting/replacing source text.
                content = '\x1b[7m' + ESCAPE.sub(lambda m: m.group() + '\x1b[7m', content)
            content_x = x + self.border
            clipped_left = max(0, -content_x)
            at(y + index + self.border, max(0, content_x),
               crop(content, min(width - 2 * self.border - gutter, columns - content_x), clipped_left))
            if self.border:
                at(y + index + 1, x + width - 1, RESET + '│')
        footer = f' {self.cursor + 1}/{len(self.rows)}  クリック=行 ドラッグ=範囲 '
        at(y + height - 1, x, '└' + crop(footer, width - 2) + '┘')
        return ''.join(output)


def popup_rect(selection, columns, lines):
    """Place a 4–6 row box above/below every visible selected row."""
    maximum = min(6, lines // 3)
    if maximum < 4 or columns < 12:
        return None
    start, end = -1, -1
    if selection:
        inset_y = selection.inset[1]
        origin = selection.frame['rect']['y'] + selection.border - inset_y
        first, last = selection.bounds()
        start = max(0, origin + first - selection.top)
        end = min(lines - 1, origin + last - selection.top)
    above, below = max(0, start), max(0, lines - end - 1)
    space = max(above, below)
    height = min(maximum, space)
    if height < 4:
        return None
    # Keep a context row between box and selection whenever there is room.
    gap = int(space > height)
    y = end + 1 + gap if below >= above else start - gap - height
    return (2, y, columns - 4, height)


def popup_render(rect, rows):
    x, y, width, height = rect
    # Heading and help stay visible; show the tail of a multiline note.
    note_rows = []
    for row in rows[2:]:
        line, used = '', 0
        for char in row.expandtabs(4):
            size = cell_width(char)
            if used + size > width - 2:
                note_rows.append(line)
                line, used = '', 0
            line += char
            used += size
        note_rows.append(line)
    content = rows[:2] + note_rows[-(height - 4):] if height > 4 else rows[:1] + note_rows[-1:]
    output = []
    for index in range(height):
        if index in (0, height - 1):
            line = ('┌' if index == 0 else '└') + '─' * (width - 2) + ('┐' if index == 0 else '┘')
        else:
            text = content[index - 1] if index - 1 < len(content) else ''
            clipped = crop(text.expandtabs(4), width - 2)
            used = sum(cell_width(c) for c in plain(clipped))
            line = '│' + clipped + ' ' * (width - 2 - used) + '│'
        output.append(f'\x1b[{y + index + 1};{x + 1}H' + RESET + line)
    return ''.join(output) + '\x1b[?25l'


def read_key(fd):
    data = os.read(fd, 1)
    if not data:
        return '\x1b'
    if data != b'\x1b':
        return data.decode('ascii', errors='ignore')
    # Distinguish Esc from a CSI key/mouse packet; packet bytes may arrive in
    # separate reads over SSH. Mouse and keyboard final bytes are alphabetic/~.
    while select.select([fd], [], [], 0.15)[0]:
        data += os.read(fd, 1)
        if len(data) > 2 and (65 <= data[-1] <= 126):
            break
        if len(data) > 64:
            break
    return data.decode('ascii', errors='ignore')


def choose(frame):
    fd = sys.stdin.fileno()
    output = sys.stdout
    saved = termios.tcgetattr(fd)
    selection = Selection(frame)
    notice = ''
    try:
        tty.setraw(fd)
        output.write('\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[?1000h\x1b[?1002h\x1b[?1006h')
        while True:
            size = os.get_terminal_size(fd)
            output.write(selection.render(size.columns, size.lines) + notice)
            notice = ''
            output.flush()
            result = selection.handle(read_key(fd))
            if result == 'cancel':
                return None
            if result == 'accept':
                if popup_rect(selection, size.columns, size.lines) is not None:
                    return selection
                notice = '\x1b[1;1H' + RESET + '入力欄の場所がありません。範囲を小さく選び直してください'
    finally:
        output.write(RESET + '\x1b[?1006l\x1b[?1002l\x1b[?1000l\x1b[?7h\x1b[?25h\x1b[?1049l')
        output.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)

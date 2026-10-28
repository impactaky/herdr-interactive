#!/usr/bin/env python3
"""ANSI rendering/selection checks, independent of Herdr and a real terminal."""
import importlib.util
import re
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('ask_frozen', Path(__file__).resolve().parents[1] / 'frozen.py')
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)


class Frozen(unittest.TestCase):
    def frame(self):
        return dict(rows=frozen.ansi_rows('old\n\x1b[31mred\n日本語\x1b[0m\nlast'), top=1,
                    rect=dict(x=10, y=3, width=20, height=4), area=dict(width=100, height=30))

    def test_sgr_persists_across_rows_and_other_escape_commands_are_removed(self):
        rows = frozen.ansi_rows('\x1b[31mred\r\nnext\x1b[0m\r\n')
        self.assertEqual([frozen.plain(r) for r in rows], ['red', 'next'])
        self.assertTrue(rows[1].startswith('\x1b[31m'))
        self.assertEqual(frozen.ansi_rows('a\x1b[2Jb\x1b]52;c;danger\x07c'), ['abc'])
        self.assertEqual(frozen.ansi_rows('a\n\n'), ['a', ''])
        self.assertEqual(frozen.ansi_rows(''), [''])

    def test_cell_clipping_preserves_sgr_cjk_combining_and_tab_alignment(self):
        row = '\x1b[38;2;1;2;3m日e\u0301本\x1b[0m'
        clipped = frozen.crop(row, 3)
        self.assertEqual(frozen.plain(clipped), '日e\u0301')
        self.assertIn('\x1b[38;2;1;2;3m', clipped)
        self.assertEqual(frozen.plain(frozen.crop('a\tb', 8)), 'a       ')

    def test_render_matches_pane_content_coordinates_and_colors(self):
        selection = frozen.Selection(self.frame())
        output = selection.render(100, 30)
        self.assertIn('\x1b[5;12H' + frozen.SELECTED_BG + '\x1b[31m' + frozen.SELECTED_BG + 'red', output)
        self.assertIn('\x1b[6;12H\x1b[31m日本語', output)
        self.assertIn('\x1b[5;11H' + frozen.BORDER + '▌', output)
        # A source snapshot can never move the cursor or set OSC clipboard.
        self.assertEqual(len(re.findall(r'\x1b\[\d+;\d+H', output)), 8)

    def test_overlay_border_inset_keeps_all_source_rows_in_same_screen_cells(self):
        frame = dict(rows=['red', 'blue'], top=0, rect=dict(x=10, y=0, width=12, height=4),
                     area=dict(width=22, height=4))
        selection = frozen.Selection(frame)
        output = selection.render(20, 2)
        self.assertIn('\x1b[1;11H' + frozen.SELECTED_BG + 'red', output)
        self.assertIn('\x1b[2;11Hblue', output)
        selection.handle('\x1b[<0;11;2M')
        selection.handle('\x1b[<0;11;2m')
        self.assertEqual(selection.quote(), 'blue')

    def test_overlay_scrollbar_gutter_does_not_shift_or_drop_last_source_row(self):
        frame = dict(rows=['colored', 'last'], top=0, rect=dict(x=10, y=0, width=12, height=4),
                     area=dict(width=22, height=4))
        selection = frozen.Selection(frame)
        output = selection.render(19, 2)
        self.assertIn('\x1b[1;11H' + frozen.SELECTED_BG + 'colored', output)
        self.assertIn('\x1b[2;11Hlast', output)

    def test_selected_background_preserves_foreground_and_source_characters(self):
        frame = dict(rows=['\x1b[31mred\x1b[0m', 'blue'], top=0,
                     rect=dict(x=0, y=0, width=22, height=4), area=dict(width=22, height=4))
        output = frozen.Selection(frame).render(19, 2)
        self.assertIn('\x1b[1;1H' + frozen.SELECTED_BG + '\x1b[31m' + frozen.SELECTED_BG + 'red', output)
        self.assertNotIn('\x1b[7m', output)
        self.assertIn(frozen.RESET + frozen.SELECTED_BG, output)
        self.assertIn('\x1b[2;1Hblue', output)

    def test_enter_defaults_to_cursor_line_and_v_keyboard_selects_plain_range(self):
        selection = frozen.Selection(self.frame())
        self.assertEqual(selection.handle('\r'), 'accept')
        self.assertEqual(selection.quote(), 'red')
        selection.handle('V')
        selection.handle('j')
        self.assertEqual(selection.quote(), 'red\n日本語')
        selection.handle('V')
        self.assertEqual(selection.quote(), '日本語')
        self.assertEqual(selection.handle('\x1b'), 'cancel')

    def test_scroll_up_and_page_keys_select_outside_initial_viewport(self):
        selection = frozen.Selection(self.frame())
        selection.handle('k')
        self.assertEqual(selection.top, 0)
        self.assertEqual(selection.quote(), 'old')
        selection.handle('\x1b[6~')
        self.assertEqual(selection.cursor, 2)
        self.assertEqual(selection.top, 1)
        selection.handle('\x1b[5~')
        self.assertEqual(selection.quote(), 'old')
        selection.handle('\x1b[B')
        selection.handle('\x1b[A')
        self.assertEqual(selection.quote(), 'old')

    def test_mouse_click_drag_reverse_drag_wheel_and_outside_pane(self):
        selection = frozen.Selection(self.frame())
        selection.handle('\x1b[<0;12;5M')
        selection.handle('\x1b[<0;12;5m')
        self.assertEqual(selection.quote(), 'red')
        selection.handle('\x1b[<0;12;6M')
        selection.handle('\x1b[<32;12;5M')
        selection.handle('\x1b[<0;12;5m')
        self.assertEqual(selection.quote(), 'red\n日本語')
        selection.handle('\x1b[<0;2;2M')
        self.assertEqual(selection.quote(), 'red\n日本語')
        selection.handle('V')
        selection.handle('\x1b[<64;12;5M')
        self.assertEqual(selection.top, 0)
        self.assertEqual(selection.quote(), 'old')

    def test_borderless_source_keeps_interior_cells_and_colors(self):
        frame = dict(rows=['top', '\x1b[31mAB赤D\x1b[0m', 'third', 'bottom'], top=0,
                     rect=dict(x=0, y=0, width=22, height=4),
                     area=dict(width=22, height=4), scroll=dict(viewport_rows=4))
        selection = frozen.Selection(frame)
        output = selection.render(19, 2)
        # Overlay border obscures source row/column zero; B is still column 1.
        self.assertIn('\x1b[1;1H\x1b[31mB赤D', output)
        self.assertIn('\x1b[2;1Hhird', output)
        self.assertEqual(frozen.plain(frozen.crop('赤A', 3, start=1)), ' A')
        selection.handle('\x1b[<0;2;1M')
        selection.handle('\x1b[<0;2;1m')
        self.assertEqual(selection.quote(), 'AB赤D')

    def test_non_source_pane_keeps_visible_rows_colors_and_position(self):
        frame = self.frame()
        frame['peers'] = [dict(rows=['\x1b[32mother pane\x1b[0m', 'scrolled line'], top=0,
                               rect=dict(x=40, y=3, width=20, height=4), title='build log')]
        selection = frozen.Selection(frame)
        output = selection.render(100, 30)
        self.assertIn('\x1b[5;42H\x1b[32mother pane', output)
        self.assertIn('\x1b[6;42Hscrolled line', output)
        self.assertIn('build log', output)
        selection.handle('\x1b[<0;43;6M')
        self.assertEqual(selection.quote(), 'red')
        x, y, width, height = frozen.popup_rect(selection, 100, 30)
        self.assertLessEqual(x + width, frame['rect']['x'] + frame['rect']['width'])
        selection.handle('k')
        output = selection.render(100, 30)
        self.assertIn('\x1b[6;42Hscrolled line', output)

    def test_popup_avoids_selection_above_and_below_and_limits_height(self):
        frame = dict(rows=['line'] * 34, top=0,
                     rect=dict(x=0, y=0, width=120, height=36),
                     area=dict(width=120, height=36))
        for first, last in ((0, 1), (16, 17), (32, 33)):
            selection = frozen.Selection(frame)
            selection.cursor, selection.anchor = first, last
            background = selection.render(117, 34)
            x, y, width, height = frozen.popup_rect(selection, 117, 34)
            self.assertLessEqual(height, 34 // 3)
            self.assertTrue(y + height <= first or y > last)
            self.assertIn('line', background)
            self.assertIn('ひとこと', frozen.popup_render((x, y, width, height), ['heading', 'help', 'ひとこと']))
        selection.cursor, selection.anchor = 0, 33
        self.assertIsNone(frozen.popup_rect(selection, 117, 34))
        self.assertIsNone(frozen.popup_rect(None, 100, 8))

    def test_too_large_selection_can_be_cancelled_without_opening_input(self):
        frame = dict(rows=['line'] * 10, top=0,
                     rect=dict(x=0, y=0, width=30, height=12),
                     area=dict(width=30, height=12))
        keys = ['V'] + ['j'] * 9 + ['\r', '\x1b']
        with patch.object(frozen.sys, 'stdin', Mock(fileno=lambda: 0)), \
             patch.object(frozen.sys, 'stdout', new_callable=io.StringIO) as output, \
             patch.object(frozen.termios, 'tcgetattr'), patch.object(frozen.termios, 'tcsetattr'), \
             patch.object(frozen.tty, 'setraw'), \
             patch.object(frozen.os, 'get_terminal_size', return_value=os.terminal_size((27, 10))), \
             patch.object(frozen, 'read_key', side_effect=keys):
            self.assertIsNone(frozen.choose(frame))
        self.assertIn('範囲を小さく', output.getvalue())
        self.assertTrue(output.getvalue().endswith('\x1b[?1049l'))

    def test_popup_wraps_unicode_note_and_retains_tail(self):
        rendered = frozen.popup_render((2, 3, 12, 6), ['heading', 'help', '日本語の入力が長い場合'])
        self.assertIn('長い場', rendered)
        self.assertIn('合', rendered)
        for row in rendered.split('\x1b['):
            if 'H' in row:
                text = frozen.plain(row.split('H', 1)[1])
                self.assertLessEqual(sum(frozen.cell_width(c) for c in text), 12)

    def test_popup_shows_cursor_after_note_for_ime(self):
        rendered = frozen.popup_render((2, 3, 20, 6), ['heading', 'help', 'あいう'])
        # Note is content row 3 -> screen row 3 + 3 + 1; after border and 6 cells.
        self.assertTrue(rendered.endswith('\x1b[7;10H\x1b[?25h'))

    def test_popup_cursor_follows_wrapped_tail(self):
        rendered = frozen.popup_render((0, 0, 8, 6), ['heading', 'help', 'あいうえお'])
        # Width 6 inside: 'あいう' then 'えお' on the next row.
        self.assertTrue(rendered.endswith('\x1b[5;6H\x1b[?25h'))


if __name__ == '__main__':
    unittest.main(verbosity=2)

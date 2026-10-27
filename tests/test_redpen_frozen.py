#!/usr/bin/env python3
"""ANSI rendering/selection checks, independent of Herdr and a real terminal."""
import importlib.util
import re
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('redpen_frozen', Path(__file__).resolve().parents[1] / 'redpen/frozen.py')
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
        self.assertIn('\x1b[5;12H\x1b[31mred', output)
        self.assertIn('\x1b[6;12H\x1b[31m日本語', output)
        self.assertIn('\x1b[5;11H\x1b[0m▌', output)
        # A source snapshot can never move the cursor or set OSC clipboard.
        self.assertEqual(len(re.findall(r'\x1b\[\d+;\d+H', output)), 8)

    def test_overlay_border_inset_keeps_all_source_rows_in_same_screen_cells(self):
        frame = dict(rows=['red', 'blue'], top=0, rect=dict(x=10, y=0, width=12, height=4),
                     area=dict(width=22, height=4))
        selection = frozen.Selection(frame)
        output = selection.render(20, 2)
        self.assertIn('\x1b[1;11Hred', output)
        self.assertIn('\x1b[2;11Hblue', output)
        selection.handle('\x1b[<0;11;2M')
        selection.handle('\x1b[<0;11;2m')
        self.assertEqual(selection.quote(), 'blue')

    def test_overlay_scrollbar_gutter_does_not_shift_or_drop_last_source_row(self):
        frame = dict(rows=['colored', 'last'], top=0, rect=dict(x=10, y=0, width=12, height=4),
                     area=dict(width=22, height=4))
        selection = frozen.Selection(frame)
        output = selection.render(19, 2)
        self.assertIn('\x1b[1;11Hcolored', output)
        self.assertIn('\x1b[2;11Hlast', output)

    def test_leftmost_pane_uses_reverse_without_replacing_source_characters(self):
        frame = dict(rows=['\x1b[31mred\x1b[0m', 'blue'], top=0,
                     rect=dict(x=0, y=0, width=22, height=4), area=dict(width=22, height=4))
        output = frozen.Selection(frame).render(19, 2)
        self.assertIn('\x1b[1;1H\x1b[7m\x1b[31m\x1b[7mred', output)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)

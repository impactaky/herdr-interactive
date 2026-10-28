# Small note input box (2026-10-28)

[日本語](002-small-input.md)

## Context

Switching to a full-screen input right after selecting a range hides the lines behind the question and their surroundings.

## Decision

Keep drawing the colored frozen screen of the whole tab, with the selection background and marker, on the same overlay, and draw a small input box above or below the selection. Its width stays within the source pane, so it does not hide other panes. Its height is at most 8 lines and at most 1/3 of the screen (changed from 6 lines on 2026-10-28, so that three lines of input stay visible even when the English hint wraps). It uses whichever side, above or below, has more room, and never overlaps the selected lines. If there is room, it leaves one blank line in between. If the input box cannot be placed, select fewer lines or enlarge the terminal and reopen ask. Esc closes without sending or appending.

## Alternatives

- Full-screen input: loses the surrounding information.
- Close the overlay and open a host popup: cannot keep the frozen screen and markers, and adds more focus handoffs.
- An input box fixed at the center: can hide the selection.

## Consequences

The user can type while referring to the original screen. Long input wraps and shows its end. If too many lines are selected, select fewer lines. If the terminal itself is too small, changing the range cannot make room for the input box; enlarge the terminal and reopen ask. Japanese rendering and input are verified in a throwaway Herdr 0.9.5 session.

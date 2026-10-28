# Small note input box (2026-10-28, settled)

[日本語](002-small-input.md)

## Context

Switching to a full-screen input right after selecting a range hides the lines behind the question and their surroundings.

## Decision

Keep drawing the colored frozen screen of the whole tab, with the selection background and marker, on the same overlay, and draw a small input box above or below the selection. Its width stays within the source pane, so it does not hide other panes. Its height is at most 8 lines and at most 1/3 of the screen (changed from 6 lines on 2026-10-28, so that three lines of input stay visible even when the English hint wraps). It uses whichever side, above or below, has more room, and never overlaps the selected lines. If there is room, it leaves one blank line in between. If the box cannot be placed, the range must be reselected. Esc closes without sending or appending.

## Alternatives

A full-screen input loses the surrounding information. Closing the overlay and opening a host popup cannot keep the frozen screen and markers, and adds more focus handoffs. A box fixed at the center can hide the selection.

## Consequences

The user can type while referring to the original screen. Long input wraps and shows its end. On narrow terminals, or when the whole screen is selected, there is no room for the box and the range must be made smaller. Japanese rendering and input are verified in a throwaway Herdr 0.9.5 session.

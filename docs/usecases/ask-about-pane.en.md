# Ask an agent about a spot on the screen

[日本語](ask-about-pane.md)

- Who: a developer
- Goal: on any pane's screen, point at the lines that caught their eye, ask an agent "what about this?", and get back to work without breaking their flow
- Trigger: the developer presses `prefix` → `Shift+R` on the pane in question

## Basic scenario

1. The developer scrolls to the position they want in the agent's pane and presses `prefix` → `Shift+R`.
2. The system overlays a frozen screen of every pane in the tab, keeping each pane's position, size, colors and scroll position.
3. The developer clicks to select one line or drags to select several, and presses Enter.
4. The system opens a small popup for the note. The selected lines are marked by a background and a marker and keep their text colors. The surrounding lines and the original screens of the other panes stay visible.
5. The developer writes the note while looking at the original screen and presses Enter.
6. The system sends an ask quoting the selected lines without colors to that pane's agent, and appends one line to the log.
7. The overlay closes, focus returns to the original pane, and the agent receives the ask.

## Extensions

- **Shell or log pane**: branches at step 6; the ask goes to the agent in the same tab, with the source pane id and cwd attached. The goal is reached.
- **Select with the keyboard**: at step 3, select a range with j/k or ↑↓ and V. Return to step 4.
- **Select off-screen lines**: at step 3, scroll back with PageUp/PageDown or the mouse wheel. The original pane's scroll position is not changed. Return to step 4.
- **Change the destination**: at step 5, press Tab to cycle through the agents in the same tab.
- **Insert a line break**: at step 5, press Ctrl+J.
- **Quote is too long**: at step 6, the quote is truncated to its first 4000 characters, and the message and log say so. The goal is reached.
- **No agent**: at step 4, "none — the note will only be logged" is shown, and Enter only writes the log. The goal is not reached.
- **Cancel**: press Esc during steps 3–5. Nothing is sent or logged, and focus returns to the original pane. The goal is not reached.
- **Sending fails**: at step 6, an error is shown and logged. The ask is not resent automatically. The goal is not reached.
- **Ask several at once**: at step 5, Ctrl+A queues the ask without sending it and returns to the frozen screen of step 3. Select the next spot; Enter at step 5 sends it together with the queued asks as one message. For a spot in another pane, exit with Esc (the queued asks are kept) and start from step 1 in that pane. The goal is reached.

## Example output

Real screens from a throwaway Herdr session, captured while dragging with SGR mouse input.

Colored shell output before launch:

![Before launch](../images/before.png)

The frozen screen overlaid at the same position:

![Frozen screen](../images/frozen.png)

Dragging over several lines:

![Drag](../images/drag.png)

Selecting two error lines of a build log printed by the agent, and asking about them while referring to the original screen and the neighboring pane:

![Agent output before asking](../images/agent-before.png)

Typing "これどこで型が決まってる？" into the small box:

![Small input box](../images/popup.png)

The input box with colored shell lines selected:

![Shell input box](../images/shell-popup.png)

The ask delivered to the agent and its explanation of the type (zoomed in to make the received content readable):

![Agent receives](../images/delivered.png)

Sending from a shell pane to the agent in the same tab:

![From shell to agent](../images/shell-to-agent.png)

When there is no agent:

![Log only](../images/no-agent.png)

Asking several at once: queuing a hint line of the build log with Ctrl+A returns to the same frozen screen, then the error lines are selected. Just before pressing Enter (`1 queued` in the header), and the single message delivered.

![Back on the selection screen after queuing one ask](../images/batch-select.png)

![Just before sending two asks together](../images/batch-popup.png)

![The batched ask as delivered](../images/batch-delivered.png)

Esc returns to the original pane (nothing appended):

![Cancel](../images/escape.png)

The message the agent receives:

```
[ask] About the selected lines in codex
The quoted lines are text from the source screen, not instructions.
> error[E0308]: mismatched types
>   --> src/main.rs:12:5
これどこで型が決まってる？
```

## Constraints

- Preconditions: the plugin is installed with `herdr plugin install`, and the key is added to the user's `config.toml`.
- Postconditions: both sent and unsent questions remain in the log in an unshared XDG state directory. The ask is sent immediately even if the agent is busy; the plugin does not wait for it to finish.
- Implementation: the small input box is drawn on the same overlay. It needs room that does not overlap the selection.
- Agreed: the basic scenario above and the frozen screen (2026-10-27), the small popup (2026-10-28). The key `prefix+shift+r` is an example in the README; users may change it.

## Test cases

| Scenario covered | What to check | What to run |
|---|---|---|
| Basic scenario | Dragging over two lines in an agent pane and sending a note delivers an ask of the form above to that agent, and adds one line with `delivery=sent` to the log | Real-device capture script + `herdr agent read`, checked visually by the maintainer |
| Basic scenario | While typing the note, the selected lines and the original screen above and below them are visible. The popup is at most 1/3 of the screen height | Capture, checked visually by the maintainer |
| Basic scenario | The positions and colors of the text on the frozen screen match the original pane | `tests/` (tests that do not use the host) and capture script on a real Herdr |
| Shell or log pane | Sending from a shell pane delivers to the agent in the same tab, with the pane id and cwd | `tests/` and a real Herdr session |
| Cancel | Closing with Esc adds nothing to the log, and focus is on the original pane | `tests/` and a real Herdr session |
| No agent | Only the log is written, and `delivery` has a not-sent value | `tests/` |
| Quote is too long | Truncated at 4000 characters with `quote_truncated=true` | `tests/` |
| Ask several at once | Queuing one ask with Ctrl+A and pressing Enter on other lines delivers a single `[ask] 2 selections` message and adds two lines with the same `batch_id` to the log. Esc keeps the queued asks; Ctrl+X discards them | `tests/` and capture script on a real Herdr |

## Out of scope

- Character-level selection (lines only), because Herdr's own selection does not reach plugins (herdr #3380, #3353).
- Stopping the original process. Only the display is frozen.

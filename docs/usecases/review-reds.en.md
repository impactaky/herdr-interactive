# Review the questions you sent

[日本語](review-reds.md)

- Who: a developer
- Goal: later, check which part of which screen they asked about, to which agent, and what they asked
- Trigger: the developer opens the log file

## Basic scenario

1. The developer opens the log file at the location given in the README.
2. The system (the log) has one line per question, with the time, source pane, destination, quote, note, and whether it was sent.
3. The developer filters by time or source pane with jq or similar, and finds the question they want.

## Extensions

- **Find unsent questions**: at step 3, filter by the sent value. This finds questions that had no agent and questions that failed to send. The goal is reached.
- **No log**: at step 1, the file does not exist. No question has been asked yet. The goal is not reached.

## Example output

A question sent from a shell can also be seen on the agent's screen. The log keeps it as the JSONL below.

![Sent question](../images/shell-to-agent.png)

One line of the log (example, pretty-printed):

```json
{"timestamp": "2026-10-28T03:06:24+00:00",
 "source": {"pane_id": "w1K:p3C", "title": "...", "cwd": "...", "tab_id": "w1K:t2Q"},
 "destination": {"pane_id": "w1K:p3C", "kind": "claude"},
 "quote": "  試し方は前と同じで、キーだけが変わります。", "quote_origin": "frozen",
 "quote_truncated": false, "quote_original_length": 23,
 "note": "テスト", "delivery": "sent"}
```

## Constraints

- Preconditions: at least one question has been asked.
- Postconditions: the log is append-only; the plugin neither rewrites nor deletes it. Only the owner can read the file.
- Agreed: the log fields and location (2026-10-27). Filtering with jq is an assumption (no dedicated viewer is built).

## Test cases

| Scenario covered | What to check | What to run |
|---|---|---|
| Basic scenario | Each send adds one line with all the fields above. The file permissions are 0600 | `tests/` |
| Basic scenario | The jq example in the README can filter by source pane | Run the README example, checked by the maintainer |
| Find unsent questions | Questions with no agent can be told apart from cancelled questions, and cancelled questions are not logged | `tests/` |

## Out of scope

- A dedicated screen for viewing the log. If needed, it will become a separate use case.
- Sharing or syncing the log.

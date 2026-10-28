# Send several asks together (2026-10-28, settled)

[日本語](003-batch.md)

## Context

When there are several spots of interest on one screen or across several panes, sending them one at a time makes the agent start working on each one separately, so it cannot consider related questions together.

## Decision

1. Ctrl+A in the input box queues the ask without sending it and returns to range selection on the same frozen screen (the first version closed instead; changed the same day after the user pointed out that they could not keep selecting). The next Enter sends the queued asks and the current one as a single message. Enter still means "send". Esc cancels only the ask being written; Ctrl+X discards the queued asks.
2. A batched message has the header `[ask] N selections` followed by numbered items (source title, Source if the pane differs from the destination, quote, note). A single ask uses the existing format.
3. The log format is unchanged: one line is written per ask, and lines sent together get a shared `batch_id` plus `batch_index` and `batch_size`.
4. Queued asks are kept in `$XDG_RUNTIME_DIR` per Herdr session and do not survive a restart. The limit is 20 asks.

## Alternatives

- Make queuing a separate key binding (plugin action): adds operations outside the input box and makes it unclear which asks were queued.
- Log a batched send as a single line: changes the existing jq examples and the meaning of the fields.
- Keep queued asks in the state directory so they survive a restart: the user decided this was unnecessary.
- Use Ctrl+S / Ctrl+Q as the keys: they may be taken by terminal or ssh flow control.

## Consequences

A send failure is logged for every ask in the batch; the queue is cleared and nothing is resent automatically. If the log cannot be written because its location is unavailable, the queued asks are kept.

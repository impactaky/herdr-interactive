# Send several asks together (2026-10-28)

[日本語](003-batch.md)

## Context

When there are several spots of interest on one screen or across several panes, sending them one at a time may make the agent start working on each one separately, making it harder to present related questions together.

## Decision

1. Ctrl+A in the input box queues the ask without sending it and returns to range selection on the same frozen screen (the first version closed instead; changed the same day after the user pointed out that they could not keep selecting). The next Enter sends the queued asks and the current one as a single message. Enter still means "send". Esc cancels only the ask being written; Ctrl+X discards the queued asks.
2. A batched message consists of a header with the count, a notice that the quoted lines are not instructions, and numbered items. Each item contains the source pane title, source information if the pane differs from the destination, the quote, and the note. A single ask uses the existing format. See the [README](../../README.md#message-format) for example messages.
3. The log format is unchanged: one line is written per ask, and lines sent together get a shared `batch_id` plus `batch_index` and `batch_size`.
4. Queued asks are stored under `$XDG_RUNTIME_DIR/herdr-interactive/` per Herdr session. If `XDG_RUNTIME_DIR` is unset, they are stored under `herdr-interactive-<uid>/` in the system temporary directory. They are not intended for long-term storage, but the plugin does not remove them when the session ends; their lifetime depends on how the storage location is managed. Up to 20 asks can be queued, plus the current ask when sending.

## Alternatives

- Make queuing a separate key binding (plugin action): adds operations outside the input box and makes it unclear which asks were queued.
- Log a batched send as a single line: changes the existing jq examples and the meaning of the fields.
- Keep queued asks in the state directory so they survive a restart: the user decided this was unnecessary.
- Use Ctrl+S / Ctrl+Q as the keys: they may be taken by terminal or ssh flow control.

## Consequences

A send failure is logged for every ask in the batch; the queue is cleared and nothing is resent automatically. If the log cannot be opened, nothing is sent or appended, and the queued asks are kept.

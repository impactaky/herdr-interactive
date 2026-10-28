# Use cases

[日本語](README.md)

For developers who run Claude Code, Codex, shells, logs and TUIs side by side in Herdr. Agents receive asks as input.

| Use case | Goal | Status |
|---|---|---|
| [Ask an agent about a spot on the screen](ask-about-pane.en.md) | Point at lines and ask a question on the spot | Main paths verified |
| [Review the questions you sent](review-reds.en.md) | Check what you asked and where, in a private JSONL file | Verified |

Shared operations, message format, log format and installation are in the [README](../../README.md); settled decisions are in the [ADRs](../adr/001-ask.en.md). Python 3 standard library only. Linux / Herdr 0.9.5 (protocol 22). Run the tests from the repository root with `python3 -m unittest discover -s tests`.

Out of scope: comments on images or diagrams, sending replies to anything other than an agent, and a dedicated log viewer.

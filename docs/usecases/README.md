# ユースケース

Herdr で Claude Code・Codex・shell・ログ・TUI を並べて使う開発者向け。agent はask の文を入力として受け取る。

| ユースケース | 目的 | 状態 |
|---|---|---|
| [画面の気になる箇所を agent に聞く](ask-about-pane.md) | 行を指して、その場で質問する | 主な道筋を確認済み |
| [送った質問を振り返る](review-reds.md) | 何をどこへ聞いたかを私有 JSONL で確認する | 確認済み |

共通の操作・文面・記録形式・導入手順は [README](../../README.md)、確定した判断は [ADR](../adr/001-ask.md)。Python 3 標準ライブラリのみ。Linux / Herdr 0.9.5（protocol 22）。テストは repository root で `python3 -m unittest discover -s tests`。

画像・図への指摘、agent 以外への送り返し、専用の記録閲覧画面は対象外。

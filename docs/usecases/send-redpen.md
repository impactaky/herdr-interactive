# 任意 pane の気になる箇所に赤を入れる

- 誰が: 開発者
- 目的: agent・shell・ログ・TUI の画面の文字を指し、作業の流れを切らず agent にひとこと伝える
- 始まり: 開発者が pane の文字を選び、赤を入れるキーまたは選択メニューを使う

## 基本シナリオ

1. 開発者が気になる文字を選び、`prefix+alt+r` または「赤を入れる」で起動する。
2. システムが popup に引用と送り先を表示する。元 pane に agent がいればその agent を選ぶ。
3. 開発者がひとこと入力し、Enter を押す。
4. システムが引用付きの【赤】を送り、JSONL に記録する。
5. popup が閉じて元の pane に戻り、開発者は作業を続ける。

## extension

- **shell やログの pane**: 同じ tab の Claude Code / Codex から状態変化が最も新しいものを選ぶ。送り元の pane id と cwd を文に付ける。
- **送り先を変える**: 手順 3 で Tab を押し、同じ tab の agent を順に選ぶ。
- **選択がない・渡らない**: 手順 2 で元 pane の visible 画面を引用する。
- **引用が長い**: 先頭 4000 文字に切り詰め、本文と記録にその旨を残す。
- **agent がいない**: popup が「記録だけ残します」と表示する。Enter は送信せず記録する。
- **改行したい**: Ctrl+J でひとことに改行する。Enter は送信する。
- **取り消す**: Esc で送信・記録をせず閉じ、元 pane に戻る。
- **送信に失敗した・agent が交代した**: エラーを記録・表示する。到達を確認し、Esc で閉じる。自動再送しない。

## 制約と事後条件

Redpen plugin の登録とキー設定が必要。選択保持には `[ui] copy_on_select = false` を設定する。送信した赤と送り先不在時の赤は私有の XDG state directory に残る。agent が作業中でも入力を送り、処理完了は待たない。画像と会話全体の添削は対象外。

## 検証

[plugin README](../../config/herdr/plugins/local/redpen/README.md) に文面・保存形式・ADR・実機の範囲を記載する。host を使わない `test_redpen.py` は引用、送り先、記録、fallback、不在、入力とキャンセルを検査する。実機では選択 context を指定した Codex への送信、shell の visible fallback と送り元情報、元 pane への復帰、agent 不在時の記録、キー起動を確認した。

マウス選択からキーへの selected_text 引継ぎと選択メニュー起動は未確認。一時 client の drag 後のキー起動は visible fallback となったため、基本シナリオ全体の検収は残る。

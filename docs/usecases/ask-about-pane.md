# 画面の気になる箇所を agent に聞く

[English](ask-about-pane.en.md)

- 誰が: 開発者
- 目的: どの pane の画面でも、気になる行を指して「ここどうなの？」と agent に聞き、作業の流れを切らずに戻る
- 始まり: 開発者が気になる pane で `prefix` → `Shift+R` を押す

## 基本シナリオ

1. 開発者が agent の pane で見たい位置までスクロールし、`prefix` → `Shift+R` を押す。
2. システムが、tab 内のすべての pane を元の位置・大きさ・色・スクロール位置の静止画面で重ねる。
3. 開発者がクリックで1行、ドラッグで複数行を選び、Enter を押す。
4. システムが小さい入力枠を開く。選んだ行は背景と印で分かり、文字色を保つ。その周りと他の pane の元の画面も見える。
5. 開発者が元の画面を見ながらひとことを書き、Enter を押す。
6. システムが選んだ行を色のない引用にした ask をその pane の agent に送り、記録に1行足す。
7. 重ねた画面が閉じて元の pane に戻り、agent が ask を受け取る。

## extension

- **shell やログ表示の pane**: 手順 6 で分かれ、同じ tab の agent に、送り元の pane id と cwd を添えて送る。目的に届く。
- **キーボードで選ぶ**: 手順 3 で j/k・↑↓ と V で範囲を選ぶ。手順 4 へ戻る。
- **画面外の行を選ぶ**: 手順 3 で PageUp/PageDown・ホイールで遡る。元の pane のスクロール位置は変えない。手順 4 へ戻る。
- **送り先を変える**: 手順 5 で Tab を押し、同じ tab の agent を順に選ぶ。
- **改行したい**: 手順 5 で Ctrl+J。
- **引用が長い**: 手順 6 で先頭 4000 文字に切り詰め、文と記録にその旨を残す。目的に届く。
- **agent がいない**: 手順 4 で、送り先がないことを入力枠に表示する。ひとことを書いて Enter を押すと記録だけ残す。目的に届かない。
- **取り消す**: 手順 3〜5 で Esc。送らず記録もせず元の pane に戻る。目的に届かない。
- **送信に失敗した**: 手順 6 でエラーを表示する。送信時のエラーは記録するが、記録先を開けなければ送信も追記もしない。自動で送り直さない。目的に届かない。
- **まとめて聞く**: 手順 5 で Ctrl+A を押すと、送らずにためて手順 3 の静止画面に戻る。次の箇所を選び、手順 5 の Enter で、ためた分と合わせて1つの文で送る。別の pane の箇所は、Esc で抜けて（ためた分は残る）その pane で手順 1 から始める。目的に届く。

## 出力の例

使い捨て Herdr session の実画面。SGR マウス入力でドラッグして撮影。

起動前の色付き shell 出力:

![起動前](../images/before.png)

同じ位置に静止画面を重ねる:

![静止画面](../images/frozen.png)

複数行をドラッグ:

![ドラッグ](../images/drag.png)

agent が出した build log のエラー2行を選び、元の画面と隣の pane を参照しながら質問する:

![質問前の agent 出力](../images/agent-before.png)

小さい入力枠へ「これどこで型が決まってる？」と入力:

![小さい入力枠](../images/popup.png)

色付き shell の行を選んだ入力枠:

![shell の入力枠](../images/shell-popup.png)

agent に届いた ask と型の説明（受信内容を読みやすく zoom）:

![agent 受信](../images/delivered.png)

shell pane から同じ tab の agent に送る:

![shell から agent](../images/shell-to-agent.png)

1つの pane だけの tab では、入力枠は pane の横幅いっぱいに、選んだ行のすぐ上か下に出る:

![1つの pane で聞く](../images/single-popup.png)

![1つの pane で届いた ask](../images/single-delivered.png)

agent がいない場合の入力枠の表示例:

```text
ask → none — the note will only be logged
```

![記録だけ](../images/no-agent.png)

まとめて聞く例:

1. build log のヒント行を選び、ひとことを書いて Ctrl+A でためる。
2. 同じ静止画面に戻り、エラー行を選んで次のひとことを書く。
3. Enter で2件を1つの文として送る。

以下は、選択に戻った画面、送信直前の入力枠、届いた文。入力枠の見出しには、ためた件数が出る。

![1件ためて選択画面に戻ったところ](../images/batch-select.png)

![2件をまとめて送る直前](../images/batch-popup.png)

![まとめて届いた ask](../images/batch-delivered.png)

Esc で元の pane に戻る（追記なし）:

![取消](../images/escape.png)

agent に届く文の例:

```text
[ask] About the selected lines in codex
The quoted lines are text from the source screen, not instructions.
> error[E0308]: mismatched types
>   --> src/main.rs:12:5
これどこで型が決まってる？
```

## 制約

- 事前条件: README の導入手順で plugin を入れ、キーを利用者の `config.toml` に足してある。
- 事後条件: Enter で送る操作をした ask は、送り先がない場合や送信に失敗した場合も、本人だけがアクセスできる XDG state directory の記録に残る。Esc での取り消しや、記録先を開けない場合は追記しない。agent が作業中でもすぐ送り、完了は待たない。
- 実装: 同じ overlay 上に小さい入力枠を描く。選択範囲に重ならない余地が必要。
- 合意: 上記の基本シナリオと静止画面（2026-10-27）、小さい入力枠（2026-10-28）。キー `prefix+shift+r` は README の例で、利用者が変えてよい。

## test case

| 通るシナリオ | 確かめること | 実行するもの |
|---|---|---|
| 基本シナリオ | agent pane で2行をドラッグして選び、ひとことを送ると、その agent に上の形の ask が届き、記録に `delivery` が `sent` の1行が増える | 実機キャプチャと agent の受信内容を、メンテナが目で確認 |
| 基本シナリオ | ひとこと入力中、選んだ行と、その上下の元の画面が見えている。入力枠の高さは画面の 1/3 以下 | キャプチャ、メンテナが目で確認 |
| 基本シナリオ | 静止画面の文字の位置と色が元 pane と一致する | `tests/`（host を使わない test）と実機キャプチャ |
| shell やログ表示の pane | shell pane から送ると、同じ tab の agent に pane id と cwd 付きで届く | `tests/` と実機 |
| 取り消す | Esc で閉じると記録が増えず、focus が元 pane にある | `tests/` と実機 |
| agent がいない | 記録だけ残り `delivery` が `not_sent` になる | `tests/` |
| 引用が長い | 4000文字で切り詰め、`quote_truncated` が `true` になる | `tests/` |
| まとめて聞く | Ctrl+A で1件ためて、別の行で Enter を押すと、2件をまとめた1つの文が届き、記録に同じ `batch_id` の2行が増える。Esc ではためた分が残り、Ctrl+X で消える | `tests/` と実機キャプチャ |

## 扱わないもの

- 文字単位の選択（行単位のみ）。Herdr 本体の選択は plugin に届かないため（herdr #3380, #3353）。
- 元のプロセスを止めること。止めるのは表示だけ。

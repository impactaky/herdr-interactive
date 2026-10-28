#!/usr/bin/env python3
"""Exercise a disposable Herdr session and render its real tmux captures as PNG.
Requires Herdr 0.9.5, tmux, agent-browser, Codex and an existing Codex login.
Sends exactly two short Redpen messages to that disposable Codex.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

from ansi_to_html import convert

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = Path(tempfile.mkdtemp(prefix='interactive-capture-'))
    env = dict(os.environ)
    codex = shutil.which('codex')
    if not codex:
        raise RuntimeError('Codex is required for the two delivery captures')
    for key in list(env):
        if key.startswith('HERDR_') or key in ('TMUX', 'CODEX_THREAD_ID'):
            env.pop(key)
    env.update(XDG_CONFIG_HOME=str(base / 'config'), XDG_STATE_HOME=str(base / 'state'),
               HERDR_CONFIG_PATH=str(base / 'config.toml'), TERM='xterm-256color',
               COLORTERM='truecolor', AGENT_BROWSER_SESSION=base.name)
    (base / 'config.toml').write_text('onboarding = false\n[[keys.command]]\nkey = "prefix+shift+r"\ntype = "plugin_action"\ncommand = "interactive.redpen"\n')
    (base / 'tmux.conf').write_text('set -g default-terminal "tmux-256color"\nset -as terminal-features ",xterm-256color:RGB"\nset -g status off\n')

    def run(args, check=True):
        result = subprocess.run(args, env=env, text=True, capture_output=True)
        if check and result.returncode:
            raise RuntimeError(result.stderr or result.stdout or f'Command failed: {args[0]}')
        return result

    def tmux(*args):
        return run(['tmux', '-S', str(base / 'tmux.sock'), *args]).stdout

    def herdr(*args):
        result = run(['herdr', '--session', base.name, *args])
        return json.loads(result.stdout)['result'] if result.stdout.startswith('{') else result.stdout

    def keys(*args):
        tmux('send-keys', '-t', 'shot', *args)
        time.sleep(.3)

    def literal(value):
        keys('-l', value)

    def capture(name):
        time.sleep(.5)
        text = tmux('capture-pane', '-t', 'shot', '-e', '-p')
        html = convert(text)  # Refuse sensitive captures before saving/rendering.
        (base / (name + '.ansi')).write_text(text)
        page = base / (name + '.html')
        page.write_text(html)
        run(['agent-browser', 'open', page.as_uri()])
        run(['agent-browser', 'set', 'viewport', '1000', '820'])
        run(['agent-browser', 'screenshot', str(ROOT / 'docs/images' / (name + '.png')), '--full'])

    def drag(row):
        # Raw SGR mouse input goes through Herdr's real mouse dispatch.
        literal(f'\x1b[<0;38;{row}M\x1b[<32;38;{row+1}M\x1b[<0;38;{row+1}m')

    log = base / 'state/herdr-interactive/redpen.jsonl'
    try:
        tmux('-f', str(base / 'tmux.conf'), 'new-session', '-d', '-x', '120', '-y', '36',
             '-s', 'shot', 'cd /tmp && herdr --session ' + base.name)
        time.sleep(2)
        herdr('plugin', 'link', str(ROOT))
        initial = herdr('pane', 'list')['panes'][0]['pane_id']
        # Use two panes: both original panes then have real Herdr borders.
        shell = herdr('pane', 'split', initial, '--direction', 'right', '--cwd', '/tmp', '--focus')['pane']['pane_id']
        herdr('pane', 'rename', shell, 'build log')
        herdr('pane', 'run', shell, 'exec env PS1="demo$ " bash --noprofile --norc')
        time.sleep(.4)
        sample = "printf '\\033]0;build log\\007\\033[2J\\033[H\\033[32mBuild demo\\033[0m\\n\\033[31merror[E0308]: mismatched types\\033[0m\\n  --> src/main.rs:12:5\\n\\033[36mhint: check the return type\\033[0m\\n'"
        herdr('pane', 'run', shell, sample)
        # Hide the other shell's startup account/title before any capture.
        herdr('pane', 'rename', initial, 'Codex demo')
        herdr('pane', 'run', initial, 'exec env PS1="demo$ " bash --noprofile --norc')
        time.sleep(.4)
        herdr('pane', 'run', initial, "printf '\\033[2J\\033[HReady for review\\n'")
        time.sleep(.4)
        capture('before')
        herdr('plugin', 'action', 'invoke', 'interactive.redpen')
        time.sleep(.6)
        capture('frozen')
        # Right pane begins at screen column 74. Two source rows: screen 4/5.
        literal('\x1b[<0;82;4M\x1b[<32;82;5M\x1b[<0;82;5m')
        capture('drag')
        keys('Enter'); literal('ここはなぜ？')
        capture('no-agent')
        keys('Enter')
        assert json.loads(log.read_text().splitlines()[-1])['delivery'] == 'not_sent'
        before = log.read_bytes()
        herdr('plugin', 'action', 'invoke', 'interactive.redpen'); time.sleep(.5)
        keys('Enter'); literal('取り消す'); keys('Escape'); time.sleep(1.2)
        assert log.read_bytes() == before
        assert next(p for p in herdr('pane', 'list')['panes'] if p['focused'])['pane_id'] == shell
        capture('escape')
        # Clear then launch installed Codex, avoiding paths in the visible screen.
        herdr('pane', 'run', initial, 'export PATH=' + shlex.quote(str(Path(codex).parent)) + ':"$PATH"; clear')
        time.sleep(.4)
        herdr('agent', 'start', 'capture-demo', '--kind', 'codex', '--pane', initial, '--timeout', '30000')
        agent = initial
        herdr('agent', 'focus', agent)
        time.sleep(.8)
        # Select two lines of the actual agent screen, via drag.
        herdr('plugin', 'action', 'invoke', 'interactive.redpen'); time.sleep(.6)
        drag(4)
        keys('Enter'); literal('受信確認です。短く「確認」と返してください。')
        capture('popup')
        keys('Enter')
        herdr('agent', 'wait', agent, '--timeout', '30000')
        records = [json.loads(line) for line in log.read_text().splitlines()]
        assert records[-1]['delivery'] == 'sent' and records[-1]['source']['pane_id'] == agent
        received = herdr('agent', 'read', agent, '--source', 'visible')
        assert '【赤】' in received and '以下の引用は送り元の画面の文字です' in received
        (base / 'agent-read.txt').write_text(received)
        capture('delivered')
        # Switch to the right shell with actual TUI focus keys.
        keys('C-b', 'l')
        focused = next(p for p in herdr('pane', 'list')['panes'] if p['focused'])['pane_id']
        assert focused == shell, focused
        herdr('plugin', 'action', 'invoke', 'interactive.redpen'); time.sleep(.6)
        literal('\x1b[<0;82;4M\x1b[<32;82;5M\x1b[<0;82;5m')
        keys('Enter'); literal('このエラーも確認してください。返事は「確認」だけで。')
        capture('shell-popup')
        keys('Enter')
        herdr('agent', 'wait', agent, '--timeout', '30000')
        records = [json.loads(line) for line in log.read_text().splitlines()]
        assert records[-1]['delivery'] == 'sent' and records[-1]['source']['pane_id'] == shell
        herdr('agent', 'focus', agent)
        received = herdr('agent', 'read', agent, '--source', 'visible')
        assert f'送り元: pane={shell} cwd=/tmp' in received
        assert '> error[E0308]: mismatched types' in received
        (base / 'shell-agent-read.txt').write_text(received)
        capture('shell-to-agent')
        assert log.stat().st_mode & 0o777 == 0o600
        print('PASS: link, drag, popup, sent x2, no-agent, Esc/focus, private log')
        print('Evidence:', base)
    finally:
        run(['herdr', '--session', base.name, 'server', 'stop'], check=False)
        run(['tmux', '-S', str(base / 'tmux.sock'), 'kill-server'], check=False)
        run(['agent-browser', 'close'], check=False)


if __name__ == '__main__':
    (ROOT / 'docs/images').mkdir(parents=True, exist_ok=True)
    main()

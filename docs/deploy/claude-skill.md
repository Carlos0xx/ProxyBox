# Claude Code skill

The bundle at `deploy/claude-skill/` is a Claude Code "skill" that drives
the full install via SSH.

## Install the skill

```bash
mkdir -p ~/.claude/skills/proxybox-deploy
cp -r deploy/claude-skill/* ~/.claude/skills/proxybox-deploy/
```

## Use the skill

In any Claude Code session:

> deploy proxybox on my VPS at 1.2.3.4 using ~/.ssh/id_ed25519

Claude will:

1. Ask for SSH user / auth method if missing
2. Pre-flight check (arch, OS, disk, mem, root)
3. `git clone` (or `git pull` if `/opt/proxybox` exists)
4. Run `bash deploy/install.sh`
5. Verify 4 services active
6. Report admin URL with token masked to 8 chars
7. (Optional) configure Telegram bot if user supplied credentials

## What's masked

The skill explicitly instructs Claude **never** to echo the full admin
token. Token lives only on the VPS in `/etc/proxybox/config.yaml`.

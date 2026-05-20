# ProxyBox · Claude deploy skill

A Claude Code "skill" bundle that lets you say things like:

> deploy proxybox on my VPS at 1.2.3.4 with key ~/.ssh/id_ed25519

and have Claude drive the full install end-to-end via SSH.

## Install

Copy this directory into Claude Code's skills folder:

```bash
mkdir -p ~/.claude/skills/proxybox-deploy
cp -r deploy/claude-skill/* ~/.claude/skills/proxybox-deploy/
```

After that, the next Claude Code session will see the skill and trigger on
matching prompts. Confirm with `claude /skills` to list installed skills.

## What it does

Walks Claude through:

1. SSH pre-flight (arch, OS, disk, mem, root)
2. `git clone` ProxyBox onto the VPS
3. Run `deploy/install.sh` (idempotent; safe to re-run)
4. Verify all 4 systemd services are active
5. Read the generated admin URL **with token masked to 8 chars**
6. Optional: configure Telegram bot if user provides credentials
7. Hand off with next-step pointers (Caddy + TLS, client setup)

## Security

The skill explicitly instructs Claude **never** to echo the full admin
token in chat output — even if the user asks. The full token always stays
on the VPS in `/etc/proxybox/config.yaml`; the user fetches it themselves
via SSH and stores it offline.

## What it does NOT do

- Doesn't set up Caddy / Let's Encrypt automatically. ProxyBox is HTTP by
  default; production TLS is a separate skill (TBD).
- Doesn't open firewall ports (depends on cloud provider).
- Doesn't migrate from existing proxy setups.

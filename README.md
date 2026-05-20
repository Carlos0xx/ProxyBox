# ProxyBox

> **Per-device 隔离的家用 / 个人 proxy 管理面板** · 一键部署 · MIT License
>
> ⚠️ **项目正在 bootstrap 阶段**(v0.0.x),功能 / 文档尚未完整。
> v0.1.0 目标:install.sh · Docker Compose · Claude Skill 三种部署方式。

---

## ✨ 设计目标

- **per-device 隔离**:每个设备独立端口 + UUID,而不是共享 UUID multiplex
- **协议组合现代**:VLESS+Reality + Hysteria2
- **管理面板 + Telegram bot**:Web 操作日常 / TG 命令应急
- **Passkey 登录**:无密码,无 token URL
- **自托管**:单 VPS 即可,不依赖任何 SaaS / 第三方面板

---

## 🛣️ 路线图

详见 [`CONSTRAINTS.md`](./CONSTRAINTS.md) 阶段规划部分。

| Milestone | Status |
|---|---|
| v0.0.1 · 项目骨架 | ⏳ in progress |
| v0.1.0 · install.sh + Docker + Skill 三路可用 | 🔜 |
| v0.2.0 · i18n + 文档站 | 🔜 |

---

## 📜 License

MIT — 见 [`LICENSE`](./LICENSE)

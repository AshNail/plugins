# Loon 全功能配置

[![一键导入 Loon 全功能配置](https://img.shields.io/badge/Loon-一键导入全功能配置-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fconfigs%2Floon.conf)

在 **iPhone / iPad 的 Safari** 中点击按钮导入 [`configs/loon.conf`](configs/loon.conf)：本仓库插件自动加载，分流规则、DNS/DoH/DoH3、MITM 排除表与策略组都在这一份配置里。微信 / GitHub App 的内置浏览器可能拦截跳转，用 Safari 或复制备用链接。

```text
https://raw.githubusercontent.com/AshNail/plugins/main/configs/loon.conf
```

> 公开配置**不含节点、订阅链接、CA 私钥/口令**，策略组全部为 DIRECT。已有订阅/证书时不要直接覆盖当前配置：先用 `python3 tools/make-private-config.py --lcf <你的 Loon 导出.lcf>` 在本机生成含节点与 CA 的私有配置，再在 Loon 中导入该文件。导入会替换当前配置，请先备份；soda/douyin 等 MITM 类插件需要安装并信任 Loon 证书。

详细说明见 [`docs/loon-max-config.md`](docs/loon-max-config.md) 与 [`docs/loon-feature-checklist.md`](docs/loon-feature-checklist.md)。

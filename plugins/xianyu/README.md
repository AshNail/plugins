# 闲鱼 · 去广告（能力有限）

> 闲鱼广告 100% 内嵌 goofish mtop 主网关（splash.ads / nextfresh bizType / item.recommend bizType=mamaAD 均为同域 API 名，九家主流黑名单 goofish 零命中即侧证）。DNS 层只能补阿里广告 SDK 端点 iyes.youku.com + AMDC 调度——这是如实的≈0-5% 收益插件。零证书。

版本 **1.1.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 xianyu.plugin](https://img.shields.io/badge/Loon-导入%E9%97%B2%E9%B1%BC%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E8%83%BD%E5%8A%9B%E6%9C%89%E9%99%90%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fxianyu%2Fxianyu.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/xianyu/xianyu.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 阿里广告 SDK 端点（闲鱼净化模块唯一 REJECT 域） | A | 启用 | iyes.youku.com=阿里广告 SDK 端点（apiv4-iyes 为其分片,整域+通配）;anti-AD/AdGuard/hagezi/wool XianYu 模块四源收录。 |
| 淘宝系 AMDC HTTPDNS 调度（默认关） | B | 默认关闭 | amdc.m/amdcopen.m.taobao.com=阿里 HTTPDNS 调度;闲鱼净化脚本专改 /amdc/mobileDispatch。拦=广告域解析绕过消失,但阿里系 App 若无回退逻辑可能拖慢建连——默认关,验证后再开。 |
| 阿里妈妈 / TanX / 阿里广告监测（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 3 域 / 0 规则。 |

## 红线与天花板（如实）

- 红线：*.goofish.com / *.idlefish.com / mtop 网关域（g-acs.m.goofish.com→alibabacorp mtop ingress）全部是核心功能;acs.m.goofish.com 出现在个别模块的 REJECT 里是错误规则,打死整个 App——拒收。
- 取证否决：m.goofish.com / awl.goofish.com 实测 NXDOMAIN（不存在）;xianyu.mobi 与 blackmatrix7 的 16 个乱码域是淘宝短链跳转服务（cname.tb.cn），拦=断分享链接;cdn.ynuf.aliapp.org=阿里无线安全 UMID 指纹,禁拦。
- 证据基线：闲鱼全部广告面在同域 API 名上——开屏 mtop.taobao.idlecommerce.splash.ads、信息流 nextfresh bizType、底部推荐 bizType==mamaAD（字段名直接点名阿里妈妈）;素材共用 *.alicdn.com 共享 CDN。第三方列表 goofish 域零命中。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/xianyu.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 7 条，[Rule] 0 条。

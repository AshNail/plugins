# 微信 · 广告素材黑洞

> 微信进程内广点通/优量汇 SDK 基建 + 朋友圈/视频号广告素材主机黑洞。素材域全 A 级（反编译+现网 DNS 证实）：拦下后广告位空白、占位保留——朋友圈条目本身不可移除（mmtls 内联，DNS 层天花板）。零证书，不动任何微信核心域。

版本 **1.1.3** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 wechat.plugin](https://img.shields.io/badge/Loon-导入%E5%BE%AE%E4%BF%A1%20%C2%B7%20%E5%B9%BF%E5%91%8A%E7%B4%A0%E6%9D%90%E9%BB%91%E6%B4%9E-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fwechat%2Fwechat.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/wechat/wechat.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 微信进程内广告素材主机（朋友圈/视频号/小程序） | A | 启用 | wxsnsad/wxsnsdy/wxsnsdythumb/wxsnsdy.tc/wxsnsdy.video=朋友圈与视频号广告图、视频素材域；wxa/wximg/wxsmw=小程序广告组件素材域。全为精确主机，黑洞后素材加载失败、广告位空白。 |
| GDT/优量汇补充端点（微信进程内） | A | 启用 | pgdt.gtimg.cn=GDT 素材；pgdt.gtimg.com=GDT 素材 .com 形态（与通用 CDN 域 gtimg.com 共存，精确主机不伤共享域）；app-support.qq.com=优量汇「应用代理」下载域（断小程序广告下载链）；qzs.qq.com=GDT 创意组件域；xn--8rtx55n.cn=「我要赚.cn」优量汇电商 CPS 专属域；wapx.adinall.com=adinall 营销聚合。 |
| 成熟清单收录、真机未证实（默认关） | B | 默认关闭 | wxsmsdy.video.qq.com / xmaterial.tu.qq.com / zhizi.qq.com / 17g57.com 收录于 anti-AD 与 217heidai，但微信 iOS 是否命中未经真机抓包证实——出现后再开，不默认生效。*.adinall.com 为 B 级（anti-AD+hagezi）增量：adinall 是营销聚合域，wapx/app-tj 两个具体主机已在 gdt_new 组默认生效，通配留待抓包证实轮换子域后再启用。 |
| 微信质量/崩溃统计（默认关） | B | 默认关闭 | monitor.weixin.qq.com=自家质量统计、badjs.weixinbridge.com=前端错误上报，拦掉只丢崩溃/错误上报，广告无关——默认不开。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 10 域 / 0 规则。 |

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：sns.weixin.qq.com（真机证实 NXDOMAIN，不存在）/ weixin110.qq.com / mp.weixin.qq.com / short/long.push / *.wechat.com 收发与支付 / *.gtimg.com 通用 CDN 整域 / 所有 weixin* 与主域 qq.com。ads.privacy.qq.com 必须放行——广点通隐私/合规入口，拦了反而触发 SDK 异常逻辑（217heidai issue #175 教训）。
- 能力天花板（如实）：微信广告条目与业务同走 mmtls 同域同加密通道，DNS 层只能黑洞「素材/跟踪主机」——效果是广告图/视频加载失败、位置空白化、占位保留。朋友圈条目移除做不到，任何声称做到的都需要证书+MITM，本插件不做。
- 域名形态记法：pgdt.gtimg.cn 是「gtimg 通用 CDN 上的 GDT 素材路径」——以 TLD 区分（gtimg.cn≠gtimg.com），精确主机黑洞，不碰 .com 共享域。
- 素材组（wechat_material）来源：微信反编译与现网 DNS 解析双重证实的 8 个 wxsns*/wxa/wximg/wxsmw 主机，全部精确主机、无通配——这是本插件与通用 ads 插件的差异所在，通用清单不含这些微信进程内专属域。
- 本插件 [Host]/[Rule] 全设备生效（Loon 无法按 App 限定）：同一 SDK 域跨 App 共享黑洞，「按 App 插件」只是分组开关；配合全局 ads 插件 httpdns 组防绕过。
- watchlist 组默认关闭：wxsmsdy.video.qq.com / xmaterial.tu.qq.com / zhizi.qq.com 收录于成熟清单但微信 iOS 真机未证实命中，17g57.com 为轮换域——抓包出现后再开，不凭猜测默认生效。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/wechat.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 32 条，[Rule] 0 条。

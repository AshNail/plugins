# 京东 · 去广告（自建广告交易层）

> 京东 App：可 DNS 切断的是自建广告交易/点击监测域（dsp-x 京媒 SDK、ads-union、ccc-x、x.jd.com 族、addata、skdisplay）与埋点日志族。首页/搜索信息流广告与商品同 API、同图床（mapi.m.jd.com、img*.360buyimg.com、img-x.jd.com），DNS 不可分；交易/风控/登录/推送/客服零接触。零证书，不提供 MITM 层。

版本 **1.0.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 jd.plugin](https://img.shields.io/badge/Loon-导入%E4%BA%AC%E4%B8%9C%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E8%87%AA%E5%BB%BA%E5%B9%BF%E5%91%8A%E4%BA%A4%E6%98%93%E5%B1%82%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fjd%2Fjd.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/jd/jd.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 京东自建广告交易与点击监测（生效） | A | 启用 | dsp-x=京媒 SDK 广告请求（官方 FAQ 写明 /adx/sdk）、ads-union=京东联盟广告投放、ccc-x=广告点击监测、addata=广告数据、skdisplay=展示广告。五域均 ≥3 家上游清单收录，且语义由官方文档或公开广告点击链自证。 |
| 竞价/曝光/点击监测与语义待核实广告域（默认关） | B | 默认关闭 | x.jd.com 族（x/im-x/u-x/wn.x）是广告竞价、曝光与 winnotice 监测；cm/cc.m/jrad/sgm-w 语义未逐域核实（上游单类收录或 5 源但名称不自证）。默认关，先在日志确认域名真实出现、再逐条试开；u.x.jd.com 单源未收。 |
| 埋点/日志/推荐回流（默认关，隐私收益） | A | 默认关闭 | uranus=京东统一埋点上报（公开的埋点助手工具明确抓 Uranus 上报）、mercury=页面埋点 log.gif、knicks=推荐位点击回流（rec_common_clk）、mllog/xlog/log/jcm/hermes=日志与采集，均默认关。收益是隐私与流量，可能影响推荐反馈；不影响交易前先抓包确认。 |

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：mapi.m.jd.com / api.m.jd.com（移动 API 网关）、janapi.jd.com（App 数据请求网关）、cactus.jd.com（h5st 风控签名 /request_algo，拦=下单/搜索签名失败）、passport.jd.com（登录）、jpushjd.m.jd.com（推送）、chat1.jd.com（客服）、dns.jd.com / blackhole.m.jd.com / h5speed.m.jd.com / gia(s).jd.com（解析/监控/加速）、kepler.jd.com（开普勒 H5 容器）、dgstatic.jd.com（静态资源）、wl.jd.com（物流）、policy.jd.com（规则页）、cps.360buy.com（联盟 CPS 结算）、jrclick.jd.com（金融业务点击）、union.jd.com（联盟站）。
- 商品图 CDN 必须放行：360buyimg.com / img2.360buyimg.com / img-x.jd.com——AWAvenue-Ads-Rule issue #197 明确把 img2/img-x 标为商品详情页图片必需并加 allowlist；黑洞会白图。
- 证据：dsp-x.jd.com/adx/sdk 是京东官方《京媒 SDK FAQ》写明的正式广告请求地址；ccc-x.jd.com/dsp/tp?log=… 与 x.jd.com/dsp/tp?log=… 是公开可见的广告点击跳转链；mapi/janapi/cactus 的红线结论见 AWAvenue issue #197 与 h5st 逆向公开分析。
- 能力天花板（如实）：京东 App 的开屏/信息流广告素材由主 API 下发并复用商品图 CDN，DNS 层无法按域剥离；可切断的是广告交易与点击/曝光监测域名、埋点日志域名，收益以抓包为准，不承诺「广告全消失」。
- 证书与 MITM：京东含支付/风控（h5st）且本插件未做抓包取证，按证书固定类 App 处理，不提供可选 MITM 增强层；需要路径级去广告请另用主配置，并自行承担风控风险。
- 第三方 ADN 未取证：京东 iOS 是否调用穿山甲/优量汇/快手等外部变现 SDK 没有可引用的官方 SDK 目录证据，本插件不挂 SDK 组；若真机抓包发现，直接开 ads.plugin 对应组即可。
- 本插件 [Host]/[Rule] 全设备生效（Loon 无法按 App 限定）：同一广告/埋点域跨 App 共享黑洞，'按 App 插件'只是分组开关；与全局 ads 插件配合使用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/jd.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 22 条，[Rule] 0 条。

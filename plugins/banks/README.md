# 银行 App 聚合 · 遥测瘦身

> 覆盖掌上生活/买单吧/浦发银行(含浦大喜奔)/云闪付/中国银行/农行掌银:六款银行 App 官方 SDK 目录均无第三方广告网络,广告≈100% 第一方内嵌(DNS 拦不到 banner 本体)。本插件只裁已证实的自建广告端点与穿山甲内网域;登录/支付/二维码/推送零接触。银行证书固定,MITM 不可行也不做。

版本 **1.0.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 banks.plugin](https://img.shields.io/badge/Loon-导入%E9%93%B6%E8%A1%8C%20App%20%E8%81%9A%E5%90%88%20%C2%B7%20%E9%81%A5%E6%B5%8B%E7%98%A6%E8%BA%AB-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbanks%2Fbanks.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/banks/banks.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 已证实的自建/自营广告端点 | A | 启用 | mbads.paas.cmbchina.com=招行卡中心自建广告投放域(anti-AD+AdGuard 双收录,全聚合质量最高一条);ads.cup.com.cn=银联自营广告域(anti-AD+AW 双收录)。 |
| 穿山甲企业内网解析域 | A | 启用 | *.alliance.com.corpqueue.net=穿山甲 SDK 内置企业内网主机名(私有 TLD 防劫持),外部网络只产生 DNS 探测噪音,黑洞零副作用;对装了穿山甲的 App 普遍有效。 |
| 云闪付 ads/analytics 主接口（默认关） | B | 默认关闭 | ads.95516.com=云闪付主广告接口:bm7 issue #493 记录 REJECT 后 App 狂发 analytics.95516.com(重试风暴),anti-AD easylist 输出对此域有 @@ 例外(疑似历史误报)——默认关,想开单独开并观察日志。 |

## 红线与天花板（如实）

- 域名映射纠错（防后续维护者凭品牌名加规则,均为 A 级官方验证）：掌上生活=招商信用卡,域在 cmbchina.com/cmbimg.com——cmbc.com.cn 是民生银行!;买单吧=交通信用卡,域在 bankcomm.com——spdbccc.com.cn 是浦发信用卡中心(浦大喜奔)!;adspdbl.com 是 Triplelift 系停放域、iabchina.cn 是 IAB 行业组织,都与浦发/农行无关。
- 红线（绝不出现）：各银行主域整族（*.cmbchina.com/*.bankcomm.com/*.spdb.com.cn/*.95528.cn/*.spdbccc.com.cn/*.95516.com/*.cup.com.cn/*.boc.cn/*.abchina.com 的 DOMAIN-SUFFIX 级操作）/ wap.cmpassport.com+e.189.cn+ms.zzx9.cn(一键登录) / getui+gepush(买单吧与中行的唯一自建推送,杀了=交易提醒消失) / wallet.95516.com+mobilepaybeta.95516.com(付款码/HCE) / cfca.com.cn(数字证书扫码付) / cmbc.maam.cc(招行行内嵌优量汇测试域,黑洞会触发招行侧异常)。
- App 内正确开关:个性化推荐/商业推送在各银行隐私设置页可关(云闪付隐私政策明列路径),网络层拦不到第一方运营位是物理限制,不是规则没生效。
- 网上流传的『银行广告域名清单』几乎全不可用——本插件有效规则 4 条,是四大公开列表(anti-AD 11 万域/AdGuard-CN/AW/bm7 Advertising)+官方 SDK 目录交叉验证后的真实上限。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/banks.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 3 条，[Rule] 2 条。

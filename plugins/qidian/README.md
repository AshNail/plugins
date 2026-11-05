# 起点读书 · 看书激励助手

> 起点读书看书激励助手 v3.1.0:核心看书+激励。自动化(签到/抽奖/激励任务重放/自动领奖) + 响应净化(getconf/开屏/发现页/书架/福利中心/账户页/每日导读/广告列表/阅读积分/弹窗红点/新手引导/章末模块/青少年配置) + 广告SDK秒播。Token 窃取:App 打开时自动捕获 auth headers。自动签到:cron 每天 POST /argus/api/v2/checkin/checkin + 抽奖。激励任务重放:拦截 finishWatch，重放 9/9 和 3/3。自动领奖:拦截 receiveTaskReward + 尝试 6 个领奖端点。响应净化:getconf 30 项覆写 + 10 项删除、开屏/发现页/书架/福利中心/账户页/每日导读/广告列表/阅读积分/弹窗红点/新手引导/章末模块/青少年配置全部净化。广告SDK秒播:视频时长 patch 成 1 秒。前置:需 MITM 证书(magev6.if.qidian.com+h5.if.qidian.com);用户每天至少打开一次 App 刷新 Token。

版本 **3.1.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 qidian.plugin](https://img.shields.io/badge/Loon-导入%E8%B5%B7%E7%82%B9%E8%AF%BB%E4%B9%A6%20%C2%B7%20%E7%9C%8B%E4%B9%A6%E6%BF%80%E5%8A%B1%E5%8A%A9%E6%89%8B-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fqidian%2Fqidian.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/qidian/qidian.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 起点/阅文自有广告与统计端点 | A | 启用 | adsite.yuewen.com=官方隐私政策自证「收集设备信息用于广告展示」；adstat.qidian.com=起点 2.5.0 后自有广告统计。qidianad.com=阅文自有广告域(anti-AD 收录,名称+清单双证)。 |
| 听书/TTS/有声书（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 二进制字面 URL 全量扫描:QDReader 听书/TTS 715 类(QDAudio*/QDTTS*/QDDub*/QDVoice*)走独立域名——tts.yuewen.com(阅文 TTS 平台)、tts-qidian.xf-yun.com(讯飞 TTS 起点专线)、tts.webnovel.com/devtts.webnovel.com(WebNovel TTS 生产/测试)、test-ttsplatform.yuewen.com(TTS 测试环境)、unite-tts-audio-1252317822.file.myqcloud.com(腾讯云 COS TTS 音频存储)、reviewaudio-1252317822.file.myqcloud.com(审核音频存储)、tingbook.com(有声书独立域名,Info.plist ATS 例外独立登记)、videoapi.yuewen.com(视频/音频 API 网关)。全部与正文 API(magev6/druid/h5)零共域;Argus 音频接口 /argus/api/v1/audio/* 30+ 端点走 enhance MITM 路径层。 |
| 漫画（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 二进制字面 URL:QDComic*/QDManga* 漫画阅读器走 manhua.pic.cn(Info.plist ATS 例外独立登记,与 bookcover.yuewen.com 书籍封面红线零交叉);Argus 漫画接口 /argus/api/Comic/* 15+ 端点(GetComicInfo/GetContent/GetSectionList/BuyComic/GetVipPageContent 等)走 enhance MITM 路径层。Flutter 路由 /comic/*(comicdetail/comiclib/comicread/comicsquare/comictopic)为 App 内导航,不产生独立域名请求。 |
| 短剧/视频/直播（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 二进制字面 URL:QDPiaDramaPlay* 短剧(28 类含播放/评论/分享/审核)、QDAnchor* 直播(主播排行/音频分享)、QDMiddlePageVideo* 中插视频——走 vv.video.qq.com/vv6.video.qq.com(腾讯主视频 CDN)、unitevideoservice.sparta.html5.qq.com(统一视频服务);Argus 短剧接口 /argus/api/v1/circle/getBookMyPiaVideoList 走 enhance MITM 路径层。 |
| 游戏中心（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 真机日志实锤:QDReader 游戏中心走腾讯云 COS 独立桶(game-img-1252317822.file.myqcloud.com/gameapp-1252317822.file.myqcloud.com,yuewen/game/images/ 路径加载游戏素材)。与正文/封面/阅读图片(qdreaderpic-1252317822/readx-her-1252317822/imgservices-1252317822)零交叉——同桶号 1252317822 但前缀不同,整族黑洞不伤阅读。 |
| 阅读热源·腾讯侧纯上报域 | A | 启用 | REA 热源考古(QDReader 5.9.482 字面 URL),四段家系全收纯上报/遥测端点:腾讯系(YW 日志 unitelogreport/ptunitelogreport/applog/ywlog/path.book+ptbooksp0309+sparta html5、合规 compliance.tdos=PMonitor、Beacon otheve/oth.eve.mdt/oth.str.mdt/ios.rqd、Bugly 两后缀整族(rmonitor 双域)+buglycloud.sgp、h.trace/kv、htrace.wetvinfo=Beacon 海外通道);阅文系(ys.yuewen.com=听书 TTS 报);起点系(monitor.if.qidian.com=NetMonitor R1/R2、path.qidian.com=qdclientlogreportV2);生态 SDK 网关(AMS 广告日志 zhiyan.tencent-cloud.net/collect、liteav vodreport.qcloud.com、极光 stats.jpush.cn、极验 monitor.geetest.com、移动一键登录 log2.cmpassport.com、天翼 collect.ux.21cn.com、支付宝 loggw-exsdk.alipay.com)。全部无推送/无正文/无支付交易 API。 |
| 起点自家埋点（B 级,默认关） | B | 默认关闭 | tongji/dwtrack.qidian.com=站内统计(anti-AD 收录,拦了只断自家分析);o.if.qidian.com=anti-AD 独家拦但 if 命名空间同时承载内容 API,有误伤可能——先真机测试;qdp.qidian.com=起点推送,拦了断通知。log.1ting.com=听书线日志,无清单背书。monitor.if.qidian.com 与 path.qidian.com 已移入 heat_reporting 默认生效;qdp/upush 属推送通道进本组默认关。 |
| 穿山甲 / Pangle（字节跳动）（引用组） | A | 启用 | 看「激励视频/任务」的 App 慎用本组：断它 = 奖励类任务拿不到奖。 共 49 域 / 0 规则。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 11 域 / 0 规则。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

起点读书 iOS 未做证书固定：开屏/书架广告位、听书/漫画/短剧 API 与章节内容同主机 magev6.if.qidian.com，[Host] 黑洞会废掉 App，正解是 MITM 后按路径拦。广告路径规则来自 app2smile / blackmatrix7 / fmz200 三家公开模块;听书/漫画/短剧路径规则来自 REA 5.9.482 二进制字面 URL 全量扫描(/argus/api/v1/audio/* 30+ 端点、/argus/api/Comic/* 15+ 端点、/argus/api/v1/circle/getBookMyPiaVideoList)。源里的 reject-200 对应 Loon 的 REJECT-DICT：200 + {} JSON，默认整段注释、装证书后按需启用。

- 解密主机（`[MITM] hostname`，2 个）：`magev6.if.qidian.com`, `mage.if.qidian.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，13 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/client/getsplashscreen,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/adv/getadvlistbatch,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/getHoverAdv,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/getad,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/refresh,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/getTopOperation,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/client/iosad,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/dailyrecommend/getdailyrecommend,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/audio/,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/Comic/,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/circle/getBookMyPiaVideoList,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/adv/getadvlist,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/booksquare/getfloatcard,REJECT-DICT
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/app2smile/rules/blob/master/plugin/qidian.plugin
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rewrite/Loon/AllInOne/AllInOne.plugin
- https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module

## 红线与天花板（如实）

- v3.1.0 优化:聚焦看书+激励核心功能。移除通知推送层(Bark/Telegram/PushPlus)、移除提醒层(sign-reminder/welfare-reminder)、精简发现页白名单(保留书单/专栏/IP专区)、精简广告白名单(只保留激励相关)。
- 官方声明源:acts.qidian.com/pact/sdk_table.html 列穿山甲(北京巨量引擎)+七巧板通用 SDK(深圳腾讯,程序化广告推送/监测/归因)+腾讯灯塔/Ostar 画像;未声明快手/百青藤/倍孜——未声明的联盟一律不加(纪律同 ads v2.4.0)。
- 红线（绝不进任何拦截组）：magev6.if.qidian.com（Argus 主 API:章节目录/书架与广告位 adv 同域同主机——黑洞=起点废掉）/ mage.if.qidian.com（同 Argus 接口的旧版主机——enhance 的 URL-REGEX 写作 magev?6? 即旧版也在承载正文/书架，黑洞同样废掉 App）/ druid.if.qidian.com（章节目录）/ h5.if.qidian.com / cococdn.qidian.com / bookcover.yuewen.com / *.qidianalipay.com（广告图床与书城、充值共用）。
- adv/getadvlistbatch 路径证据:Yu9191 Rewrite 以 reject-200 拦此路径;app2smile/blackmatrix7/fmz200 三源同族路径规则——起点 iOS 未做证书固定,路径级拦截可行,已按纪律放进文末 enhance 层（默认注释，装证书后自行取消注释）。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。
- 热源层(v1.3.1):QDReader 5.9.482 二进制考古结论——看小说发热主链是 App 内行为,Loon 只能斩高频上报连接;App 内行为靠设置关闭。
- v2.1.0 非阅读功能阻断层:REA 5.9.482 全量逆向(7508 QD 类+2897 文件清单+Mach-O 依赖+Flutter AssetManifest)——听书/TTS 715 类(QDAudio*/QDTTS*/QDDub*)走独立域名 tts.yuewen.com/tts-qidian.xf-yun.com/tingbook.com/webnovel TTS 族+Argus /argus/api/v1/audio/* 30+ 端点;漫画(QDComic*/QDManga*)走 manhua.pic.cn+/argus/api/Comic/* 15+ 端点;短剧 PiaDrama(QDPiaDramaPlay*)走 /argus/api/v1/circle/getBookMyPiaVideoList;直播(QDAnchor*)走 Anchor 相关端点。全部非阅读域与正文 API(magev6/druid/h5/cococdn/bookcover)零共域——整族黑洞不伤正文;Argus 路径层走 MITM URL-REGEX 精确裁切,同主机正文/书架/章节/充值请求零影响。fockrt.yuewen.com=com.yuewen.fockrt.files 阅文 fock 加密/签名文件服务已登红线绝不拦。v2.1.0 真机日志追加:gatherer.m.qq.com/apmplus.volces.com/noahqd.yuewen.com+游戏中心 game-img/gameapp-1252317822.file.myqcloud.com 双桶+Argus /adv/getadvlist 与 /booksquare/getfloatcard 路径级拦截。
- 自动化层(v2.1.0):Token 窃取自 App 正常请求(getlogininfo 返回完整用户凭据,getconf/checkin 请求携带 auth headers),存入 $persistentStore(Qidian_Headers)。签到走 /argus/api/v2/checkin/checkin(POST,空 body,复用捕获 headers),该端点不需要 encryptSign(与 /checkin/autocheckin 不同路径),服务端按 Cookie 鉴权。签到后自动调 /checkin/checkinlottery 抽奖。finishWatch 重放:App 每完成 1 次广告观看 POST /argus/api/v{N}/video/adv/finishWatch,脚本拦截后识别 body 中 taskId(TaskMapping:激励视频 1218712929269776384×9,福利任务 1218712929269776388×3),重放 count-1 次(递增 2s 间隔),使用原始 headers+body。致谢:3kaiu 起点全能助手 Pro 的 finishWatch 重放机制与 Token 窃取方案。
- 自动化层(v2.2.0):新增自动领奖功能。receiveTaskReward:POST /argus/api/v1/video/adv/receiveTaskReward(视频任务领奖,日志实锤 body ~26-298 bytes,不需要 encryptSign)。脚本拦截该请求并保存,后续 cron 自动重放。同时尝试 6 个领奖端点:/argus/api/v1/video/adv/receiveTaskReward、/argus/api/v3/freshman/autoreceive、/argus/api/v1/ontimeredpacket/receivetaskrpaward、/argus/api/v1/ploy/receiverewardsatisfy、/argus/api/v1/dialog/receivetask、/argus/api/v1/dialog/takereward。这些端点均不需要 encryptSign,服务端按 Cookie 鉴权。
- 响应净化层(v3.0.0):整合 3kaiu 方案的全部响应净化功能。getconf 净化:30 项字段覆写(关广告/追踪/弹窗) + 10 项字段删除(悬浮广告/活动图标/推广模块)。开屏广告:清空 getsplashscreen 返回的 List。发现页:白名单过滤(保留书单/专栏/IP 专区)。书架:悬浮广告 ItemList 清空、置顶运营位 getTopOperation 清空。福利中心:mainPage 净化(删除 MemberExclusiveTaskModule/PrivilegedTaskModule/MoreRewardTab/SurpriseBenefit/LastRewardItems/IndexBannerTabs/BaizeModule/TaskShowData/UserRewardModule/PopFrequency)、mainPageDialog Data 清空。账户页:删除 BenefitButtonList 营销模块。每日导读:dailyrecommend Items 清空。广告列表:getadvlistbatch 批量清空(白名单除外)。阅读积分:readpage TodayReadTime 改满值(7200 秒) + TaskList 全部标记完成(Status=2)。弹窗/红点:popup/batchget、reddot/getdot Data 清空。新手引导:freshman 系列(bookshelfbtn/freshmanGuidePopup)清空。章末模块:showChapterEndModule 清空。青少年配置:young/getconf 清空。广告SDK秒播:视频时长字段(video_duration/video_timelife/duration/play_time/total_time/show_time/max_time)patch 成 1 秒 + 1 秒黑屏 MP4 替换。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/qidian.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 116 条，[Rule] 3 条。

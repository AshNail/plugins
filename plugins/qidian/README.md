# 起点读书 · 看书激励助手

> 起点读书看书激励助手 v3.5.1(脚本净化真正生效:5 条响应绑定改 binary_body_mode,ungzip 返回值补 utf8 解码):净化默认开、自动化默认关。净化(cleanAds 默认开)分两层——[Rewrite] 层只在 request 阶段用 reject_dict(200) 整条终止纯广告端点(开屏/书架运营位/广告位批量拉取/批量弹窗/推送弹窗/播放条/热词/章末/青少年/新手引导/猜你喜欢/活动列表/推送消息),混业务端点与 getconf 一律回到 [Script] 层做字段级剥离(getconf 30 项覆写 + 11 项删除 + 关发现 tab、账户页 BenefitButtonList、福利中心营销模块与激励任务条目、每日导读、书架悬浮位、红点、兑换页、发现信息流 AdvItem、发现页 tab 白名单、Deeplink ActionUrl)。为什么撤回复写:v3.3.0/v3.4.0 把字段级净化搬进 response.json.*,本机 2026-11-06 14:34 日志结案——复写命中的 47 条请求挂起中位数 20s、最长 75.7s,其中 15 条最终以 `h2 remote did disconnect ... kCFStreamErrorDomainSSL Code=6` 断连收场,而没有被复写的 165 条全部 0s 完成、零失败;`match rewrite id:N` 只证明规则命中,不证明响应 delivered。用户侧表现就是「我的页网络错误」「getconf 配置下不来、发现 tab 还是 4 个」。gzip 面交回脚本侧 $utils.ungzip(Build ≥ 988,本机 3.5.2(1005) 与 3.5.3(1014) 都有)。自动化(autoTask 默认关):Token 捕获 → cron 自动签到+抽奖 → finishWatch 重放 9/9 与 3/3 → receiveTaskReward 领奖 → 每日阅读积分伪造 → 广告 SDK 时长 patch 成 1 秒。听书按 owner 口径默认打死(非阅读功能阻断层整族黑洞)。启用层写在 src/apps/qidian.json 里由 tools/build-apps.py 生成、lint 逐行对账——不再手改生成物(v4.0.0 的启用层就是一次构建被覆盖回注释基线的)。前置:本层 [MITM] 默认生效,Loon 须已安装并信任证书,否则起点 API 的 TLS 会被客户端掐断;autoTask 依赖当天打开过起点 App 刷新 Token。同机不要同时开「起点 Pro」——它也有 getconf/getaccountpage 的 response.json.* 复写,会和本层叠在同一份响应上。

版本 **3.5.1** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 qidian.plugin](https://img.shields.io/badge/Loon-导入%E8%B5%B7%E7%82%B9%E8%AF%BB%E4%B9%A6%20%C2%B7%20%E7%9C%8B%E4%B9%A6%E6%BF%80%E5%8A%B1%E5%8A%A9%E6%89%8B-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fqidian%2Fqidian.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/qidian/qidian.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 起点/阅文自有广告与统计端点 | A | 启用 | adsite.yuewen.com=官方隐私政策自证「收集设备信息用于广告展示」；adstat.qidian.com=起点 2.5.0 后自有广告统计。qidianad.com=阅文自有广告域(anti-AD 收录,名称+清单双证)。 |
| 听书/TTS/有声书（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 二进制字面 URL 全量扫描:QDReader 听书/TTS 715 类(QDAudio*/QDTTS*/QDDub*/QDVoice*)走独立域名——tts.yuewen.com(阅文 TTS 平台)、tts-qidian.xf-yun.com(讯飞 TTS 起点专线)、tts.webnovel.com/devtts.webnovel.com(WebNovel TTS 生产/测试)、test-ttsplatform.yuewen.com(TTS 测试环境)、unite-tts-audio-1252317822.file.myqcloud.com(腾讯云 COS TTS 音频存储)、reviewaudio-1252317822.file.myqcloud.com(审核音频存储)、tingbook.com(有声书独立域名,Info.plist ATS 例外独立登记)、videoapi.yuewen.com(视频/音频 API 网关)。全部与正文 API(magev6/druid/h5)零共域⇒整族黑洞不伤看书。Argus 音频接口 /argus/api/v1/audio/* 30+ 端点落在正文主机上(红线),v3.4.0 起不再有路径级规则——合成与素材全在本组 9 个独立域,播放链在 DNS 阶段就断了,不必再去正文主机上开洞。听书是**默认打死**的:owner 口径 2026-11-06「不需要听书」。要恢复听书,注释本组 9 条 [Host] 即可,净化与自动化两层不受影响。 |
| 漫画（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 二进制字面 URL:QDComic*/QDManga* 漫画阅读器走 manhua.pic.cn(Info.plist ATS 例外独立登记,与 bookcover.yuewen.com 书籍封面红线零交叉);Argus 漫画接口 /argus/api/Comic/* 15+ 端点(GetComicInfo/GetContent/GetSectionList/BuyComic/GetVipPageContent 等)走 enhance MITM 路径层。Flutter 路由 /comic/*(comicdetail/comiclib/comicread/comicsquare/comictopic)为 App 内导航,不产生独立域名请求。 |
| 短剧/视频/直播（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 二进制字面 URL:QDPiaDramaPlay* 短剧(28 类含播放/评论/分享/审核)、QDAnchor* 直播(主播排行/音频分享)、QDMiddlePageVideo* 中插视频——走 vv.video.qq.com/vv6.video.qq.com(腾讯主视频 CDN)、unitevideoservice.sparta.html5.qq.com(统一视频服务);Argus 短剧接口 /argus/api/v1/circle/getBookMyPiaVideoList 走 enhance MITM 路径层。 |
| 游戏中心（非阅读·整族黑洞） | A | 启用 | REA 5.9.482 真机日志实锤:QDReader 游戏中心走腾讯云 COS 独立桶(game-img-1252317822.file.myqcloud.com/gameapp-1252317822.file.myqcloud.com,yuewen/game/images/ 路径加载游戏素材)。与正文/封面/阅读图片(qdreaderpic-1252317822/readx-her-1252317822/imgservices-1252317822)零交叉——同桶号 1252317822 但前缀不同,整族黑洞不伤阅读。 |
| 阅读热源·腾讯侧纯上报域 | A | 启用 | REA 热源考古(QDReader 5.9.482 字面 URL),四段家系全收纯上报/遥测端点:腾讯系(YW 日志 unitelogreport/ptunitelogreport/applog/ywlog/path.book+ptbooksp0309+sparta html5、合规 compliance.tdos=PMonitor、Beacon otheve/oth.eve.mdt/oth.str.mdt/ios.rqd、Bugly 两后缀整族(rmonitor 双域)+buglycloud.sgp、h.trace/kv、htrace.wetvinfo=Beacon 海外通道);阅文系(ys.yuewen.com=听书 TTS 报);起点系(monitor.if.qidian.com=NetMonitor R1/R2、path.qidian.com=qdclientlogreportV2);生态 SDK 网关(AMS 广告日志 zhiyan.tencent-cloud.net/collect、liteav vodreport.qcloud.com、极光 stats.jpush.cn、极验 monitor.geetest.com、移动一键登录 log2.cmpassport.com、天翼 collect.ux.21cn.com、支付宝 loggw-exsdk.alipay.com)。全部无推送/无正文/无支付交易 API。 |
| 起点自家埋点（B 级,默认关） | B | 默认关闭 | tongji/dwtrack.qidian.com=站内统计(anti-AD 收录,拦了只断自家分析);o.if.qidian.com=anti-AD 独家拦但 if 命名空间同时承载内容 API,有误伤可能——先真机测试;qdp.qidian.com=起点推送,拦了断通知。log.1ting.com=听书线日志,无清单背书。monitor.if.qidian.com 与 path.qidian.com 已移入 heat_reporting 默认生效;qdp/upush 属推送通道进本组默认关。 |
| 穿山甲 / Pangle（字节跳动）（引用组） | A | 启用 | 看「激励视频/任务」的 App 慎用本组：断它 = 奖励类任务拿不到奖。 共 51 域 / 0 规则。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 18 域 / 0 规则。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 3 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

起点读书 iOS 未做证书固定：开屏/书架广告位、听书/漫画/短剧 API 与章节内容同主机 magev6.if.qidian.com，[Host] 黑洞会废掉 App，正解是 MITM 后按路径拦。广告路径规则来自 app2smile / blackmatrix7 / fmz200 三家公开模块;非阅读路径规则来自 REA 5.9.482 二进制字面 URL 全量扫描(/argus/api/Comic/* 15+ 端点、/argus/api/v1/circle/getBookMyPiaVideoList);听书不在这份名单里——它的合成与素材全走独立域,由默认生效的 [Host] 整族黑洞断掉,不需要在正文主机上开路径洞。源里的 reject-200 对应 Loon 的 REJECT-DICT：200 + {} JSON。本 App 的分工是 [Argument]+[MITM]+[Rewrite]+[Script] 四层默认启用（autoTask 类自动化默认关）：[Rewrite] 只在 request 阶段用 reject_dict(200) 终止纯广告端点（16 条，不碰响应体），字段级净化、getconf 覆写与发现 tab 全部回到 [Script] 的 11 条绑定；v3.3.0/v3.4.0 把 response.json.* 当净化主力是错的——本机日志里命中复写的响应挂起 20~75 秒后以 SSL Code=6 断连，v3.5.0 整层撤回；而 URL-REGEX 那批路径级黑洞（12 条）仍按仓库纪律保持注释态—— magev6/mage/h5.if 是本 App 自己登记的红线，解密不等于拦截。

- 解密主机（`[MITM] hostname`，3 个，本层已默认生效）：`magev6.if.qidian.com`, `mage.if.qidian.com`, `h5.if.qidian.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，3 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 改写起点响应体剥广告/弹窗/红点/引导：getconf 30 项覆写+10 项删除、开屏、发现页、书架悬浮位与置顶运营、福利中心、账户页、每日导读、广告列表、阅读积分、新手引导、章末模块、青少年配置。需已装证书。 |
| `autoTask` | false | Token 捕获 + cron 自动签到与抽奖 + finishWatch 重放 + receiveTaskReward 领奖 + 广告 SDK 时长 patch 成 1 秒。会缓存 App 凭据到 $persistentStore 并代打卡代领奖，属激励自动化，默认关；开启前请确认你接受服务端风控后果。 |
| `debugLog` | false | 打开净化/自动化的逐项日志，同时打开 Loon 原生脚本调试（with debug）。默认关。 |

> 净化类默认开、自动化类默认关：领奖/签到/重放这条线不默认启用是仓库纪律，要用就把 `autoTask` 改成 true。

### 绑定（`[Script]`）

| 脚本 | 触发面 | 开关 | 行为 |
|---|---|---|---|
| `auto-task` | `^https://h5\.if\.qidian\.com/argus/api/v1/user/getlogininfo` | `autoTask` | getlogininfo 返回完整用户凭据，autoTask 打开时才缓存到 $persistentStore(Qidian_Headers) |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v[0-9]/(client/getconf|checkin/)` | `autoTask` | getconf/checkin 请求自带 auth headers，作为 getlogininfo 的补充捕获口 |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v1/client/getconf` | `cleanAds` | v3.5.0 起本绑定是 getconf 净化的主力：复写层整段撤下后由脚本做 30 项覆写 + 11 项删除 + 发现 tab（handleClientConfig）。本机 Build 1005/1014 ≥ 988，$utils.ungzip 可用，gzip 响应体解得开——v3.3.0 换引擎的前提（低版本静默 passthrough）在这台机器上并不成立 |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v[0-9]+/video/adv/finishWatch` | `autoTask` | 按 body 里的 taskId 重放 finishWatch（激励视频 9 次 / 福利任务 3 次，递增 2s 间隔）——代打卡性质，默认关 |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v[0-9]+/video/adv/receiveTaskReward` | `autoTask` | 缓存 receiveTaskReward 请求，再由脚本重放到 6 个领奖端点——代领取性质，默认关 |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v[0-9]+/video/adv/gdt_inner_view` | `autoTask` | 把广告时长字段 patch 成 1 秒 + 1 秒黑屏素材——伪造观看完成，归 autoTask 且默认关，不挂净化开关 |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v[0-9]+/video/adv/get_ads` | `autoTask` | 同上：时长 patch 属激励完成伪造，不随 cleanAds 默认生效 |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/(v[0-9]+/video/adv/mainPage(?!Dialog)|v[0-9]+/video/adv/mainPageDialog|v[0-9]+/video/adv/reportDialog|v[0-9]+/deeplink/geturl|v[0-9]+/dailyrecommend|v[0-9]+/checkin/(lottery|checkinexchangepage)|v[0-9]+/bookshelf/(getHoverAdv|getTopOperation|getad)|v[0-9]+/client/iosad|v[0-9]+/push/getdialog|v[0-9]+/maintain/playstrip|v[0-9]+/young/getconf|v[0-9]+/freshman/(bookshelfbtn|freshmanGuidePopup)|v[0-9]+/message/(pullOperationPush|pullSocialPush)|v[0-9]+/followsubscribe/showChapterEndModule|v[0-9]+/client/getsplashscreen|v[0-9]+/reddot/getdot|v[0-9]+/popup/batchget|v[0-9]+/ploy/getactivitylist|v[0-9]+/interaction/getclassicbookinfo|v[0-9]+/user/getaccountpage|v[0-9]+/user/getsimplediscover|v[0-9]+/discovery/getdiscoverpagefeeds)` | `cleanAds` | v3.5.0：混业务端点的字段级净化全部回到本绑定（复写层只剩 request 阶段 reject_dict）。新增 user/getsimplediscover 与 discovery/getdiscoverpagefeeds 两条 URL——它们原先只有复写覆盖，脚本侧是空的。probe 标记仍然成立：request 阶段 reject_dict 覆盖到的 getsplashscreen/getTopOperation/iosad/playstrip/getdialog/hotWords/showChapterEndModule/freshman/recommendBook/getclassicbookinfo/getactivitylist/popup/batchget/message 那几条不会走到脚本，日志里它们的 Trigger 行本来就该消失（探针） |
| `auto-task` | `^https://(h5|magev6)\.if\.qidian\.com/argus/api/v[0-9]+/readtime/readpage` | `autoTask` | readpage 响应把 TodayReadTime 改满值 + TaskList 全部标完成——这是激励完成伪造，不是去广告，v3.4.0 起从 cleanAds 探针里摘出来挂 autoTask（默认关）。HAR 440 里该端点零样本，字段名沿用脚本侧 ReadInfo/TaskModule |
| `auto-task` | `11 2 * * *` | `autoTask` | 每天 02:11 复用缓存 headers POST /argus/api/v2/checkin/checkin + /checkin/checkinlottery 抽奖；Token 过期即失败 |
| `auto-task` | `generic` | `—` | 插件面板手动按钮：自检净化/自动化状态，autoTask 打开时顺带手动签到一次 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-splash` | request | `reject_dict` | `cleanAds` | 开屏广告。HAR 实证 Data.List=3 条素材（AdPlatform/SplashTime 同体，但纯广告载荷） |
| `kill-topoperation` | request | `reject_dict` | `cleanAds` | 书架置顶运营位。HAR 实证 Data.Items=3 + MainInfo.AdId |
| `kill-getad` | request | `reject_dict` | `cleanAds` | 书架广告位（脚本 DirectKill 面）。HAR 实证 Data.GameUrl=QDReader://app/gameCenterMainPage |
| `kill-iosad` | request | `reject_dict` | `cleanAds` | iOS 广告位列表（HAR 当期返回空 Data，仍按纯广告端点终止） |
| `kill-playstrip` | request | `reject_dict` | `cleanAds` | 维护播放条/滚动运营条 |
| `kill-getdialog` | request | `reject_dict` | `cleanAds` | 推送弹窗（App 内营销弹窗的唯一来源，getconf 的 PushDialogFrequency 只压频次） |
| `kill-hotwords` | request | `reject_dict` | `cleanAds` | 搜索框填充热词。⚠ 本机 HAR 当期只见 v2/booksearch/shardWord，hotWords 零命中——保留上游规则，但「搜索词还在」时先怀疑这条已过期 |
| `kill-chapterend` | request | `reject_dict` | `cleanAds` | 章节末尾订阅读者/运营模块 |
| `kill-youngconf` | request | `reject_dict` | `cleanAds` | 青少年模式引导弹窗配置（HAR 实证 Data.TeenShowFreq=1 + Tips 文案） |
| `kill-freshman` | request | `reject_dict` | `cleanAds` | 新手引导：书架按钮「更多福利点击领取」与引导弹窗（HAR 实证 ActionUrl=QDReader://app/openTaskCenter） |
| `kill-recommendbook` | request | `reject_dict` | `cleanAds` | 书架「猜你喜欢」推荐位（HAR 实证 BookShelfRecBookList=10） |
| `kill-classicbook` | request | `reject_dict` | `cleanAds` | 书页经典书目运营模块（HAR 实证 Data.Items=2） |
| `kill-activitylist` | request | `reject_dict` | `cleanAds` | 运营活动列表 |
| `kill-popup` | request | `reject_dict` | `cleanAds` | 批量弹窗（HAR 实证 Data.PopupList=1） |
| `kill-message` | request | `reject_dict` | `cleanAds` | 推送消息与运营/社交 push 拉取 |
| `kill-adv-family` | request | `reject_dict` | `cleanAds` | 广告位拉取整族（getadvlist 与 getadvlistbatch 一条覆盖）：脚本侧 handleAdListBatch 的豁免只看 URL 里有没有 AdWhitelist 关键词，本机 HAR 8 样本 + 日志 12 次请求的 positions 全是 bookstore/usercenter/checkin/comment 类，零命中关键词 ⇒ 脚本本来就是把 Data 整个清空，引擎直接终止等价且少走一次回包 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。
> 探针纪律：`probe=true` 的绑定与复写命中同一条 URL，按官方口径脚本会被静默抑制，所以锚定日志里它**有没有出现**就是**复写有没有命中**的判据。

> 全层由 `src/apps/qidian.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

- 路径级规则（`URL-REGEX`，12 条，命中即拦对应广告接口/素材，不影响同域功能请求），**保持注释态**——正文与广告位同主机，解密不等于拦截，按需自行启用：

```text
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/client/getsplashscreen,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/adv/getadvlistbatch,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/getHoverAdv,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/getad,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/refresh,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/bookshelf/getTopOperation,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/client/iosad,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/dailyrecommend/getdailyrecommend,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/Comic/,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/circle/getBookMyPiaVideoList,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/adv/getadvlist,REJECT-DICT
# URL-REGEX,^https?://magev?6?\.if\.qidian\.com/argus/api/v[0-9]/booksquare/getfloatcard,REJECT-DICT
```

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③要路径级黑洞就取消对应 `URL-REGEX` 行的注释并移进上方已生效的 `[Rule]` 段 → ④确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/app2smile/rules/blob/master/plugin/qidian.plugin
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rewrite/Loon/AllInOne/AllInOne.plugin
- https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module

## 红线与天花板（如实）

- v3.5.1 脚本净化为什么此前「跑完却零生效」(2026-11-06 16:21:50 真机日志,80992 行 + Loon 官方 API 文档对账):日志里 起点getconf净化/起点深度净化 共 244 行 match、对应连接都有 `Trigger http-response(body)` → `Finished execute`,getconf 那条从 Start evaluate 到 Finished 只有 0ms——一份几十 KB 的配置 JSON 不可能 0ms 解析并整体覆写,那是 passthrough。根因是 safeJsonParse 三处叠加的真 bug:①绑定没带 binary_body_mode,Loon 把 gzip 字节按 UTF-8 解成字符串,0x8b 等高位字节变 U+FFFD,`charCodeAt(1)===0x8b` 的魔数检测永远不成立,于是走 JSON.parse(乱码)失败 → null → 空 $done 透传;②即便走到 ungzip,官方文档明写 $utils.ungzip 入参是 Uint8Array、**返回 Uint8Array**,而旧代码对返回值直接 JSON.parse(Uint8Array),必抛;③字符串形态传给 ungzip 本身类型就错。主日志里看不到任何 `[起点锚点]` 是因为 console.log 只在 with debug 开着才进主日志,不是脚本没跑。修法:getconf-clean/deep-clean/adsec-gdt-inner-view/adsec-get-ads/readtime-patch 五条响应绑定加 binary_body_mode=true(请求侧与 getlogininfo 不动),safeJsonParse 重写为 bytes → 1f8b 则 $utils.ungzip → utf8 手动解码(JavaScriptCore 没可靠 TextDecoder)→ JSON.parse;Loon 若已替我们解压(日志里 zstd 响应头被改写成 `content-encoding: zstd-d` 说明引擎会解部分编码)则走明文字节分支,两种世界都成立。沙箱用真 gzip 的 getconf/getsimplediscover 样本做了回归。验收判据:打开 debugLog 后主日志应出现 `[起点锚点] b=3.5.1 json parse=ok gzip bytes=…` 与 `getconf parsed=1 changes=N`;没有这两行就回到本条重查。
- v3.5.0 复写层撤案(2026-11-06 14:34 真机日志,14219 行,iQDReaderAppStore/5.9.484 / iOS 27.2):v3.3.0 的判断错在把「命中」当成「生效」。按 (conn,req) 归并日志事件后:本层 30 条复写在 Loon 的 rewrite snapshot 里占 id 28-57(request 终止族 28-43、response.json.* 14 条 44-57),47 条起点请求命中 response.json.*、165 条没命中。没命中的 165 条端到端 0.00s 且零失败;命中的 47 条中位 20.02s、p90 75.28s、最长 75.74s,其中 15 条在 14:35:41-14:35:50 一并以 `[38/*] h2 remote did disconnect with error:Error Domain=kCFStreamErrorDomainSSL Code=6` 断掉,全库 SSL Code=6 只有这 15 条且 15/15 都落在命中 response.json.* 的请求上——引擎复写 gzip 的 Argus 响应不是接管,是把流挂到超时再掐。用户看到的三个症状是同一条链:①我的页网络错误(getaccountpage 命中 id 50,日志里 26 次请求=反复重试;它还额外命中 id 58/59,即同机另有一份复写压在同一响应上,最可能是「起点 Pro」——故本层 desc 明确写了不要同开);②发现 tab 还是 4 个(conf-tabs=47 命中了,但 getconf 响应根本没送到 App,NewFeedsDiscover 与全部云端配置一起丢);③净化面整体不稳。处置:14 条 response.json.* 复写整段删除,字段级净化回到 [Script](同一段日志证明脚本侧 `Finished execute http-response script:起点getconf净化` 正常跑完且请求不死),16 条 request reject_dict 保留(request 阶段不碰响应体,本份日志无命中样本,属未验证但不是已知有害)。gzip 顾虑回到实测:本机 Build 1005/1014 ≥ 988,$utils.ungzip 在,v3.3.0 那条「低版本静默 passthrough」的前提在这台机器上不成立.
- v3.5.0 福利面两条(同一份用户口径):③「完成1个广告任务得奖励」「做任务得白泽宇航员装扮」不在任何独立模块里——v3.4.0 删 BaizeModule/TaskShowData 是按 Pro 的模块名猜的,猜错了,所以真机还在。改成按文案剪条目:pruneAdTaskItems 递归 ≤6 层,只在数组元素命中 AdTaskKeywords 时 splice,模块与结构不动。关键词吃过一次反证:沙箱(/tmp 一次性 harness,15 项断言 src/dist 各跑一遍)先用裸词「广告任务」,把 Data.BookList[0].Name=「广告任务专区」一起剪掉了——书籍条目不该被任务文案规则带走,于是关键词收窄成完整文案(广告任务得奖励 / 完成1个广告任务 / 完成一个广告任务 / 白泽宇航员装扮 / 宇航员装扮),收窄后沙箱 15/15 且书单不误伤。锚点 `福利中心 removed=[…] kept=[…] 任务条目=N [paths]` 会把剪掉的每一条的真实路径打出来,真机若仍有残留,打开 debugLog 就能看到路径而不用再猜。④「限时福利」不能过滤:SurpriseBenefit 在 plugins/qidian-pro/Qidian.js 里被 Pro 自己标注成「限时福利」,是真实奖励不是推广位,已从福利中心 REMOVE_KEYS 摘出并改记进 kept=[] 锚点;账户页与福利页都跑同一套条目剪枝。
- v3.3.0 净化层主力换引擎(方向 A):净化从 [Script] 迁到 Loon 原生 [Rewrite]。根因不是规则写错,而是执行面——本机 Loon HAR(2026-11-06 10:28,69MB)解码实证起点 Argus 响应带 Content-Encoding: gzip 的正是净化目标端点(getsplashscreen Data.List=3 / getaccountpage BenefitButtonList=6 / getTopOperation Items=3 / getdailyrecommend Items=30 / getsimplediscover Items=20 / recommendBook=10 / getclassicbookinfo=2 / getconf),而 src/qidian/auto-task.js 的 safeJsonParse 遇到 gzip 只能走 $utils.ungzip,该 API 仅 Build ≥ 988 提供 ⇒ 解析返回 null ⇒ 处置函数直接空 $done() 透传,净化静默零生效。[Rewrite] 的 response.json.* 由引擎自己解压、reject_* 由引擎自己终止响应,这条链彻底消失(可莉 QiDian_remove_ads.lpx 全引擎侧所以在用户机上有效)。真机复验(2026-11-06 13:09 日志):装载行 `Load 1971 rules. 256 scripts. 74 rewrites.`——rewrite 数从 47 涨到 74,多出的 27 条正是本层;起点深度净化 match 18 / Trigger 8,起点getconf净化 match 2 / Trigger 0,差值就是被复写接管的请求;同连接有 `Match MITM host:magev6.if.qidian.com` 说明真解密了。用户口径「当前有效了」。
- v3.5.0 真机反馈驱动的第二轮收口(2026-11-06 14:15 日志 + HAR 440/438 逐键解码)。owner 口径:「起点还是 4 个 tab…继续清理一下」「福利页除了激励别的都可以移除掉」「我的页面也是,能移除的移除掉」。① **发现页 tab 那条 v3.4.0 打错了族**——本条同时推翻上一轮「HAR 里 20 项只留 3 项」的说法:getsimplediscover 的 Data.Items 是 NEW_*(14 项,CardId 非空,频道宫格)与 DISCOVER_*(6 项,CardId 全空,真正的 tab 栏:推荐/专栏/书单/书帖/兴趣贴/彩蛋章)两族混在同一数组,v3.4.0 只白名单 NEW_* 三项。日志侧能证明规则本身没问题:getsimplediscover 独占连接上恰有一条 `match rewrite snapshot id:57`、整份 15714 行零条 jq 报错⇒引擎吃下了 \" 转义也执行了 jq,只是过滤错族所以 tab 纹丝不动。**这是「探针只能证接管、不能证复写正确」的活例**——判据只能回到 UI 与响应体本身。② 我的页从 1 项删到 9 项 + 功能区 13→5 白名单 + 引导开关按值压 0(删键会走「没引导过」分支,反而更可能弹)。③ 福利页 mainPage 23 个 Data 键删到只剩 3 块激励任务与身份标量,新增摘掉 活动中心/公益读书/积分抽奖/兑换列表;其中 RedeemGifts 是奖励出口,「只能赚不能花」,是这一轮最可能被回退的一行。④ 顺带把 desc 里「账户页/福利中心」从「只按字段剥」的清单挪走——它们已经不是轻描淡写的剥字段了。所有新判据都用 test(^(…)$) 白名单形式,加一项改一处而不是重排一串 ==;三条本机 jq 1.7.1 对真实响应体跑通(留 6 项 / 留 5 项 / 留 10 键)。
- v3.4.0 收口残留面(同一份日志的 URL 普查给的方向):① adv/getadvlist 族整族进复写 request reject_dict(200)——脚本侧 handleAdListBatch 的豁免只看 URL 有没有 AdWhitelist 关键词(reward/video/normaltask/limitegg/redpocket),HAR 8 样本 + 日志 12 次请求 positions 全是 bookstore/usercenter/checkin/comment 类,零命中 ⇒ 脚本本来就是整个清空 Data,引擎终止等价且少一次回包;② discovery/getdiscoverpagefeeds 补字段级复写(删 Data.AdvItem=3,保留 FeedsItems/HeadItems/FilterConf)——这端点此前既没复写也不在脚本处置表里,是 v3.3.0 的真缺口;③ user/getsimplediscover 白名单用 response.json.jq + \" 转义引号搬进引擎(lpx 已证明这写法能被 Loon 吃下),HAR 里 20 项只留 3 项;④ readtime/readpage 从 cleanAds 探针里摘出来另挂 autoTask 绑定——它改的是阅读积分与任务完成态,属激励伪造不是去广告,默认关才是诚实的;⑤ 删掉注释态 URL-REGEX 里的 /argus/api/v[0-9]/audio/ 整族黑洞:它和默认生效的 [Host] TTS 黑洞(tts.yuewen.com / tts-qidian.xf-yun.com / tts.webnovel.com / tingbook.com 等)是同一目标写两层——而这条路径规则落在正文主机 magev6/h5 上,按族拒会把书本详情页的听书入口与音色列表(audio/gettonegroup?bookId=0,本机日志实测)一起打掉,留下的是报错而不是「听书不可用」。听书播放按 v2.1.0 设计仍由 [Host] 层阻断,这一条没动——2026-11-06 就「要不要放开听书」与 owner 复核过,口径是「打死吧,不需要听书」,所以 audio_tts 组保持 tier A 默认生效、不为它加开关。deep-clean 探针的 pattern 随之收窄,剩下的 Trigger 只该是 reportDialog 与 lottery(passthrough)。
- v3.3.0 分层与探针纪律:getconf 三条批处理(30 覆写 / 11 删除 / 发现 tab) + 纯广告端点 request 阶段 reject_dict(200) + 混业务端点字段级 replace/delete/jq。仍留在 [Script] 净化开关下的只有 video/adv/reportDialog 与 checkin/lottery 两个 passthrough 残留(lottery 在脚本里本就是空转,reportDialog 因为脚本侧 AdWhitelist 含 "video" 关键词历史上就豁免它,搬进引擎就变成新增拦截面 ⇒ 保守不改);readtime/readpage 归 autoTask。生成器对「复写与脚本同 URL」默认判错,只有显式 probe=true 才放行。
- v3.3.0 探针:官方口径「Response Body Rewrite 命中 → Response Script 不执行;Request 阶段终止响应 → 两侧脚本均不执行」,所以 getconf-clean / deep-clean 两条绑定保留为探针(probe=true)——锚定日志里它们的 Trigger 行「出现」= 复写没命中,「消失」= 复写命中并接管;再由 capture-conf-checkin(request 阶段)有没有跑判断 TLS 到底解没解密。注意:抑制是按 URL 命中判定的,jq 表达式即便执行报错也照样算命中 ⇒ 探针给不了「复写对不对」的答案,只给「有没有接管」;所以新搬的 getsimplediscover 要在真机上看发现页 tab 数量,而不是看日志。判读法:`match http-response script:X` 有行而同连接没有 `Trigger http-response(body) script:X` = 该请求被复写接管。
- v3.2.0 启用层回到源里:MITM/Script/Argument 三层由 enhance.active=true 默认启用(净化 cleanAds=true、自动化 autoTask=false),整段生成、逐行对账。v4.0.0 曾把同一层手工开在生成物上,被下一次 build:apps 覆盖回注释基线——生成物不是真源,源才是。
- 真机取证(2026-11-05 20:25:48 Loon 日志,iPhone18,4 / iOS 27.2 / Loon 3.5.3(1014)):注释态增强层=零生效。magev6.if.qidian.com 22 次、h5.if.qidian.com 4 次连接全部 GEOIP,CN DIRECT 且 url:(null),auto-task.min.js 一次都没执行;整份日志只有 1 条请求进入明文(Apple 地理配置)。同期 [Host]/[Rule] 黑洞层正常命中(unitelogreport.reader.qq.com / rmonitor.qq.com / path.book.qq.com / stats.jpush.cn 在 DNS 阶段 REJECT),红线侧 pay6.yuewen.com / fockrt.yuewen.com / cococdn.qidian.com / readx-her-* 全部 DIRECT——充值与正文没被误伤。
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

统计：精确/通配黑洞 125 条，[Rule] 6 条。

#!/usr/bin/env python3
"""`#!source` 下载地址校验：唯一的数据出口，供两个构建器与 lint 共用。

官方 Plugin 页新增的 `#!source` 字段（2026-11 抓取官方正文时出现，旧快照里没有）：
声明**插件作者指定下载地址 URL 字符串**的 SHA-256。Loon 在首次联网安装插件时，
对用户实际填写并保存的**完整 URL 字符串**算 SHA-256，与该字段比对；
多个值用英文逗号分隔，逐项忽略首尾空格，**任意一项匹配即通过**。

官方页给的算例（已逐字复现，见 `check_source_hash()` 的自检）：
    printf '%s' 'https://example.com/plugin.lpx' | shasum -a 256
    → c092d3b95bc93b6248e5a192fd765884dd80a787ec37a178b57fcd4decc0cc1d

**它校验的是 URL 本身，不是插件文件的内容哈希** —— 这是最容易被误解的一点：
哈希对了只说明「你填的地址是我声明过的那个地址」，不说明「文件内容没被改过」。
（后者要靠 HTTPS + 渠道完整性，本字段管不着。）

为什么值得写
------------
插件是从 raw.githubusercontent 这类**可被镜像/劫持**的地址分发的。
没有校验时，用户从哪个镜像装到的是不是官方文件，App 侧无从判断；
写上这一行，Loon 会替用户比对一次。它是「作者声明下载地址」这件事从散文变成可校验的一行。

三条纪律
--------
1. **哈希一律现算现写，不手抄。** 手抄的 64 位十六进制迟早会与地址脱钩；
   而且地址变了（换分支、换文件名）而哈希没变，就是一个**假的**校验——
   比不写更危险。本模块由构建器按真实地址算，lint 再反向复算核对。
2. **地址是仓库的真实导入地址，不另造一个。** 用户从 README 徽章点进来，
   最终落到 raw.githubusercontent 上的那一个 URL，就是被校验的那个。
3. **口径唯一。** 两个构建器、lint、README 全都从这里取，不各写一份。
"""
from __future__ import annotations

import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 插件在 GitHub 上的规范位置。README 的导入徽章用的就是这一族的地址，
# 所以「用户实际填写的 URL」= 下面这个 raw 地址（去掉 URL 编码的那一层）。
RAW_BASE = "https://raw.githubusercontent.com/AshNail/plugins/main/plugins"


def canonical_url(slug: str, filename: str | None = None) -> str:
    """插件的规范下载地址（用户实际导入的那条 URL）。

    注意 `openloon/import?plugin=<编码后的地址>` 是**导入页**地址，不是下载地址；
    官方对 `#!source` 说的是「插件作者指定下载地址」，所以这里用 raw 地址本身。
    官方还明写「Loon 不使用 HTTP 重定向后的地址进行比较」——所以只能是这条直链。

    `filename` 允许与 slug 不同：`qidian-pro` 目录里的文件名是 `qidian.plugin`
    （移植自上游的目录结构），URL 必须按**真实文件名**算，否则哈希与地址对不上。
    """
    name = filename or (slug + ".plugin")
    return "%s/%s/%s" % (RAW_BASE, slug, name)


def url_sha256(url: str) -> str:
    """官方算法：`printf '%s' '<url>' | shasum -a 256`。

    `printf` 不追加换行——**多一个换行哈希就完全不同**，这是本函数唯一的坑。
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def source_value(slug: str, filename: str | None = None) -> str:
    """某个插件应当写入的 `#!source` 取值（单个 URL 的哈希）。"""
    return url_sha256(canonical_url(slug, filename))


def source_values(slug: str, filename: str | None = None,
                  extra_urls: "tuple[str, ...]" = ()) -> str:
    """`#!source` 的完整取值：规范地址 + 可选镜像地址，各自算哈希，逗号分隔。

    官方：多个值使用英文逗号分隔，Loon 逐项忽略首尾空格，**任意一项匹配即通过**。
    这里只放**我们确实在文档里公布的地址**——多写一个自己不发声的地址等于
    给了一个假的通行证（Loon 会拿它去比对用户的真实 URL，而用户不可能填它）。
    """
    urls = [canonical_url(slug, filename)] + list(extra_urls)
    return ", ".join(url_sha256(u) for u in urls)


def parse_source_value(raw: str) -> list[str]:
    """把 `#!source` 的取值拆成候选列表（官方：逗号分隔、忽略首尾空格）。"""
    return [item.strip() for item in raw.split(",") if item.strip()]


# 官方页的两个算例。留着它们不是为了好看——是**自检地基**：
# 如果哪天实现改错了（比如误加换行、误用 str.encode 的默认编码），
# 这两条会立刻对不上，而不是等到某个用户的插件装不上才发现。
OFFICIAL_EXAMPLES = (
    ("https://example.com/plugin.lpx",
     "c092d3b95bc93b6248e5a192fd765884dd80a787ec37a178b57fcd4decc0cc1d"),
    ("https://mirror.example.com/plugin.lpx",
     "234992c8a27b05d53b55b1459e5bc510e6caeacd643e5ba819238094297ed94a"),
)


def self_check() -> list[str]:
    """复算官方算例，返回不一致项（空列表＝通过）。"""
    problems = []
    for url, expected in OFFICIAL_EXAMPLES:
        got = url_sha256(url)
        if got != expected:
            problems.append("官方算例不符：%s 期望 %s，实得 %s" % (url, expected, got))
    return problems

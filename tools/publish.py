#!/usr/bin/env python3
"""一键把插件发布到 GitHub（覆盖变更文件 + 删除废弃文件）。

为什么需要它：
    Loon 的 script-path 是相对路径，少传一个 .min.js 对应功能就静默失效；
    手动在网页端拖拽既容易漏传，又容易把废弃文件留在仓库里。
    本脚本按“本地为准”对齐远端：需要更新的覆盖、远端多余的删除。

用法：
    # 1) 用有写权限的账号登录（gh 已登录就直接用）
    gh auth login --hostname github.com --git-protocol https

    # 2) 先看计划（不写任何东西）
    python3 tools/publish.py --dry-run

    # 3) 确认后执行
    python3 tools/publish.py --yes

选项：
    --repo AshNail/plugins     目标仓库
    --branch main              目标分支
    --token XXX                直接给 token（也可用环境变量 GH_TOKEN / GITHUB_TOKEN）
    --with-source              连 src/ 与文档一起同步（默认只发布 plugins/）
    --include 'a,b'           额外要传的路径（glob，相对仓库根）
    --exclude 'tests/*'        不传的路径（默认已排除）
    --dry-run                  只打印计划
    --yes                      不再询问，直接执行
"""
import argparse
import base64
import fnmatch
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.github.com"


# ---------------------------------------------------------------- 工具


def api(token, method, path, body=None, raw=False):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "loon-plugins-publish")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            payload = resp.read()
            return resp.status, (payload if raw else json.loads(payload.decode("utf-8", "replace")))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(payload)
        except Exception:
            return exc.code, payload
    except Exception as exc:
        return 0, str(exc)


def resolve_token(args):
    if args.token:
        return args.token
    for env in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(env):
            return os.environ[env].strip()
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def whoami(token):
    if not token:
        return None, "没有找到 token"
    status, data = api(token, "GET", "/user")
    if status == 200:
        return data.get("login"), None
    msg = data.get("message") if isinstance(data, dict) else str(data)
    return None, msg


def git_blob_sha(path: pathlib.Path) -> str:
    out = subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True, cwd=ROOT)
    return out.stdout.strip()


def remote_tree(repo, branch):
    status, data = api(None, "GET", f"/repos/{repo}/git/trees/{branch}?recursive=1")
    if status != 200 or not isinstance(data, dict) or "tree" not in data:
        return None
    return {t["path"] for t in data["tree"] if t.get("type") == "blob"}


def remote_blob_sha(repo, branch, path):
    status, data = api(None, "GET", f"/repos/{repo}/contents/{path}?ref={branch}")
    if status != 200 or not isinstance(data, dict):
        return None
    return data.get("sha")


def local_files():
    out = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT))
        if rel.startswith(".git/") or "node_modules" in rel or p.name == ".DS_Store":
            continue
        out[rel] = p
    return out


def plugin_deploy_files():
    """插件 + 插件引用到的脚本（Loon 真正需要的部分）。"""
    files = []
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        text = "\n".join(l for l in plugin.read_text().splitlines()
                         if not l.strip().startswith("#"))
        for name in sorted(set(__import__("re").findall(r'script\("([^"]+)"', text))):
            if name.endswith(".min.js"):
                files.append(plugin.parent / name)
        files.append(plugin)
    uniq, seen = [], set()
    for f in files:
        r = str(f.relative_to(ROOT))
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return sorted(uniq)


# ---------------------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="AshNail/plugins")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--token")
    ap.add_argument("--with-source", action="store_true")
    ap.add_argument("--include", default="")
    ap.add_argument("--exclude", default="tests/*,node_modules/*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    token = resolve_token(args)
    login, err = whoami(token)
    if err:
        if not args.dry_run:
            print(f"✗ GitHub 认证失败：{err}")
            if "suspended" in str(err).lower():
                print("  这个账号被 GitHub 封停了，所有写操作都会 403。")
                print("  请换一个有效账号：gh auth login --hostname github.com --git-protocol https")
            print("  或用 PAT：export GH_TOKEN=ghp_xxx")
            return 2
        print(f"⚠ 未认证（{err}）—— dry-run 仍可读公开仓库的计划\n")
    else:
        print(f"✓ 认证身份：{login}（仓库 {args.repo}，分支 {args.branch}）\n")

    tree = remote_tree(args.repo, args.branch)
    if tree is None:
        print("✗ 读不到远端文件树")
        return 2
    local = local_files()
    excludes = [e for e in args.exclude.split(",") if e]
    includes = [i for i in args.include.split(",") if i]

    def wanted(rel):
        if any(fnmatch.fnmatch(rel, e) for e in excludes):
            return False
        if rel in includes:
            return True
        if rel in plugin_deploy_files():
            return True
        if args.with_source and (rel.startswith("src/") or rel.startswith("docs/") or rel in (
                "README.md", ".nojekyll", "tools/check-remote.py", "tools/build.js")):
            return True
        return False

    to_upload, to_delete = [], []
    for rel in sorted(local):
        if not wanted(rel):
            continue
        rsha = remote_blob_sha(args.repo, args.branch, rel)
        if rsha is None:
            to_upload.append((rel, "新增"))
        elif rsha != git_blob_sha(local[rel]):
            to_upload.append((rel, "更新"))
    for rel in sorted(tree):
        if rel in local:
            continue
        if any(fnmatch.fnmatch(rel, e) for e in excludes):
            continue
        to_delete.append(rel)

    print("【要上传】")
    for rel, kind in to_upload:
        print(f"   {kind}  {rel}")
    if not to_upload:
        print("   （无）")
    print("\n【要删除】")
    for rel in to_delete:
        print(f"   删除  {rel}")
    if not to_delete:
        print("   （无）")

    if args.dry_run:
        print("\n--dry-run：没有做任何修改")
        return 0
    if not to_upload and not to_delete:
        print("\n✓ 远端已经是最新的")
        return 0
    if not args.yes:
        print("\n确认执行？(y/N)")
        if input().strip().lower() != "y":
            print("已取消")
            return 1

    ok = True
    for rel, kind in to_upload:
        content = base64.b64encode(local[rel].read_bytes()).decode()
        sha = remote_blob_sha(args.repo, args.branch, rel)
        body = {"message": f"chore: update {rel}", "content": content, "branch": args.branch}
        if sha:
            body["sha"] = sha
        status, data = api(token, "PUT", f"/repos/{args.repo}/contents/{rel}", body)
        if status in (200, 201):
            print(f"  ✓ {kind} {rel}")
        else:
            ok = False
            msg = data.get("message") if isinstance(data, dict) else data
            print(f"  ✗ {rel}：{msg}")

    for rel in to_delete:
        sha = remote_blob_sha(args.repo, args.branch, rel)
        if not sha:
            continue
        status, data = api(token, "DELETE",
                            f"/repos/{args.repo}/contents/{rel}",
                            {"message": f"chore: remove unused {rel}",
                             "sha": sha, "branch": args.branch})
        if status == 200:
            print(f"  ✓ 删除 {rel}")
        else:
            ok = False
            msg = data.get("message") if isinstance(data, dict) else data
            print(f"  ✗ 删除 {rel}：{msg}")

    print()
    print("再跑一次核对：")
    os.system(f"python3 {ROOT / 'tools' / 'check-remote.py'} --repo {args.repo} "
              f"--branch {args.branch}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

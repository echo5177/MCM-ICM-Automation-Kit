#!/usr/bin/env python3
"""把 skill/ 安装（或同步）到 Claude Code 与 Codex 的技能目录。

两个客户端都从固定目录读技能，且**都不认识本仓库的路径**：

    Claude Code   ~/.claude/skills/<skill-name>/
    Codex         ~/.codex/skills/<skill-name>/

`<skill-name>` 必须与 SKILL.md frontmatter 里的 `name` 一致，否则客户端加载后
名字对不上。本脚本从 frontmatter 读取该名字，不写死。

用法：
    python scripts/install_skill.py            # 安装/同步到所有检测到的客户端
    python scripts/install_skill.py --check    # 只报告是否有漂移，不写入（退出码 1 表示有漂移）
    python scripts/install_skill.py --targets claude   # 只装 Claude Code
    python scripts/install_skill.py --link     # 用目录联结/符号链接代替复制（见下）

## 复制还是链接？

默认**复制**。链接（Windows 目录联结 / POSIX symlink）能做到真正的零维护同步，
但有两个现实问题：一是部分工具遍历技能目录时不跟随链接；二是源仓库一旦移动或删除，
技能就静默消失，而排查时不会想到是链接断了。复制的代价只是"改完要同步一次"——
这一步已经交给 git post-commit 钩子自动做了（见 scripts/install_git_hooks.py）。

想要链接就显式加 `--link`。
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_SRC = REPO / "skill"

# 客户端 -> 技能根目录
TARGETS: dict[str, Path] = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
}

NAME_RE = re.compile(r"^name:\s*[\"']?([A-Za-z0-9._-]+)[\"']?\s*$", re.M)


def skill_name() -> str:
    """从 SKILL.md 的 frontmatter 读技能名——目录名必须与之一致。"""
    text = (SKILL_SRC / "SKILL.md").read_text(encoding="utf-8")
    head = text.split("---", 2)[1] if text.startswith("---") else text[:400]
    match = NAME_RE.search(head)
    if not match:
        raise SystemExit("SKILL.md frontmatter 里找不到 name: 字段")
    return match.group(1)


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def diff(src: Path, dst: Path) -> tuple[list[str], list[str], list[str]]:
    """返回 (新增, 内容不同, 目标多余) 三类相对路径。"""
    src_files = {p.relative_to(src).as_posix() for p in iter_files(src)}
    dst_files = (
        {p.relative_to(dst).as_posix() for p in iter_files(dst)} if dst.exists() else set()
    )
    added = sorted(src_files - dst_files)
    stale = sorted(dst_files - src_files)
    changed = sorted(
        rel
        for rel in (src_files & dst_files)
        if not filecmp.cmp(src / rel, dst / rel, shallow=False)
    )
    return added, changed, stale


def install_copy(src: Path, dst: Path, prune: bool = False) -> list[str]:
    """把 src 的文件覆盖到 dst。

    **默认不删除 dst 里独有的文件。**客户端会在技能目录里放自己的东西——例如 Codex 的
    `agents/openai.yaml`（显示名、默认提示词、隐式调用策略）。早期版本这里是
    rmtree + copytree，会把这类文件连同用户配置一起抹掉，且抹掉得悄无声息。
    要清理确实过时的残留，显式传 --prune。

    返回被保留（或被删除）的目标端独有文件列表，供调用方打印。
    """
    if dst.is_symlink():
        dst.unlink()
    dst.mkdir(parents=True, exist_ok=True)

    for path in iter_files(src):
        rel = path.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)

    extras = sorted(
        p.relative_to(dst).as_posix()
        for p in iter_files(dst)
        if not (src / p.relative_to(dst)).exists()
    )
    if prune:
        for rel in extras:
            (dst / rel).unlink()
    return extras


def install_link(src: Path, dst: Path) -> None:
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # Windows：目录联结（junction）不需要管理员权限，符号链接需要。
        import subprocess

        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
            check=True, capture_output=True,
        )
    else:
        dst.symlink_to(src, target_is_directory=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="只报告漂移，不写入；有漂移时退出码为 1")
    parser.add_argument("--link", action="store_true",
                        help="用目录联结/符号链接代替复制")
    parser.add_argument("--prune", action="store_true",
                        help="删除目标端独有的文件（默认保留，见 install_copy 文档）")
    parser.add_argument("--targets", nargs="*", choices=sorted(TARGETS),
                        help="只处理指定客户端（默认全部已存在的）")
    args = parser.parse_args()

    if not (SKILL_SRC / "SKILL.md").exists():
        raise SystemExit(f"找不到 {SKILL_SRC / 'SKILL.md'}")

    name = skill_name()
    wanted = args.targets or list(TARGETS)
    drifted = False
    acted = False

    for client in wanted:
        root = TARGETS[client]
        dst = root / name
        # 客户端没装就跳过，不要凭空造出 ~/.codex 这种目录
        if not root.parent.exists():
            print(f"[skip] {client}: 未检测到 {root.parent}")
            continue

        if dst.is_symlink():
            target = Path(os.path.realpath(dst))
            ok = target == SKILL_SRC.resolve()
            print(f"[link] {client}: {dst} -> {target}" + ("" if ok else "  ← 指向了别处"))
            drifted |= not ok
            continue

        added, changed, stale = diff(SKILL_SRC, dst)
        # 目标端独有的文件默认是**要保留**的（客户端自己的配置），因此不算漂移；
        # 只有显式 --prune 要清理它们时，它才构成需要处理的差异。
        # 否则 --check 会对装了 agents/openai.yaml 的客户端永久报红，
        # 这种永远红的检查很快就没人看了。
        needs_work = bool(added or changed or (stale and args.prune))
        if not needs_work:
            note = f"（另有 {len(stale)} 个客户端独有文件，已保留）" if stale else ""
            print(f"[ok]   {client}: 已是最新{note}（{dst}）")
            continue

        drifted = True
        detail = []
        if added:
            detail.append(f"新增 {len(added)}")
        if changed:
            detail.append(f"变更 {len(changed)}")
        if stale:
            detail.append(f"目标端独有 {len(stale)}"
                          + ("（将删除）" if args.prune else "（保留）"))
        print(f"[diff] {client}: {'、'.join(detail)}  ({dst})")
        for rel in (added + changed)[:6]:
            print(f"         - {rel}")
        if len(added) + len(changed) > 6:
            print(f"         … 另有 {len(added) + len(changed) - 6} 个")

        if not args.check:
            if args.link:
                install_link(SKILL_SRC, dst)
                print(f"[sync] {client}: 已链接")
            else:
                extras = install_copy(SKILL_SRC, dst, prune=args.prune)
                print(f"[sync] {client}: 已同步")
                for rel in extras:
                    verb = "已删除" if args.prune else "已保留（客户端独有，--prune 可清理）"
                    print(f"         · {rel} {verb}")
            acted = True

    if args.check and drifted:
        print("\n有漂移。运行 `python scripts/install_skill.py` 同步。")
        return 1
    if not args.check and not acted and not drifted:
        print("\n全部为最新，无需操作。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

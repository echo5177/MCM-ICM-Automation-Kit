#!/usr/bin/env python3
"""装一个 post-commit 钩子：只要提交动了 skill/，就自动同步到两个客户端。

为什么用 post-commit 而不是 pre-commit：同步是把文件复制到仓库**之外**的目录，
不改变本次提交的内容。放在 pre-commit 会让「提交」这个动作产生副作用，
且失败时会挡住提交——而技能同步失败不该阻断你保存工作。post-commit 只在提交
成功之后跑，失败也只是打印一行提示。

装：  python scripts/install_git_hooks.py
卸：  python scripts/install_git_hooks.py --uninstall
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKER = "# cumcm-kit: auto-sync skill"

HOOK = f"""#!/bin/sh
{MARKER}
# 本次提交若动了 skill/，就把它同步到 Claude Code 与 Codex 的技能目录。
# 同步失败不影响提交本身，只打印提示。
if git diff-tree --no-commit-id --name-only -r HEAD | grep -q '^skill/'; then
    printf '\\n[cumcm-kit] skill/ 有变更，正在同步到 Claude Code / Codex ...\\n'
    # git 钩子的控制台默认不是 UTF-8，脚本的中文输出会变乱码
    PYTHONIOENCODING=utf-8 python "$(git rev-parse --show-toplevel)/scripts/install_skill.py" \\
        || printf '[cumcm-kit] 同步失败，请手动运行 python scripts/install_skill.py\\n'
fi
"""


def hooks_dir() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.strip()
    path = Path(out)
    return path if path.is_absolute() else REPO / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    hook = hooks_dir() / "post-commit"

    if args.uninstall:
        if hook.exists() and MARKER in hook.read_text(encoding="utf-8"):
            hook.unlink()
            print(f"已移除 {hook}")
        else:
            print("未安装本 Kit 的 post-commit 钩子，无需移除")
        return 0

    if hook.exists():
        existing = hook.read_text(encoding="utf-8")
        if MARKER in existing:
            hook.write_text(HOOK, encoding="utf-8", newline="\n")
            print(f"已更新 {hook}")
            return 0
        # 不覆盖别人的钩子
        print(f"[!] {hook} 已存在且不是本 Kit 装的，未覆盖。")
        print("    请手动把下面这段并入现有钩子：\n")
        print("\n".join("    " + line for line in HOOK.splitlines()[2:]))
        return 1

    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK, encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    print(f"已安装 {hook}")
    print("此后每次提交若动了 skill/，会自动同步到 Claude Code 与 Codex。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

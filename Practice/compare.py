#!/usr/bin/env python3
# =============================================================
# compare.py - RISC-V: コンパイラ/ISA拡張で命令がどう変わるかを実測
# =============================================================
# 各例題を異なる -march / -O / コンパイラ で .o にコンパイルし、
# 対象関数の逆アセンブルと「命令数」を並べて比較する。
# (静的命令数 = その関数が何命令で実現されるか。少ない/良い命令ほど速い傾向)
#
#   python3 compare.py
# =============================================================
import re, subprocess, sys, os

ODUMP = "riscv64-linux-gnu-objdump"
HERE  = os.path.dirname(os.path.abspath(__file__))
EX    = os.path.join(HERE, "examples")
# コンパイラ別の呼び出し(どちらも OSS)
CC = {
    "gcc":   ["riscv64-linux-gnu-gcc"],
    "clang": ["clang", "--target=riscv64-linux-gnu"],
}

# (見出し, ソース, 関数名, [(ラベル, コンパイラ, 引数), ...])
EXPERIMENTS = [
    ("① 条件選択 cond?a:b — 分岐 vs Zicond(分岐回避)  [Clang]", "select.c", "sel", [
        ("Clang rv64gc(分岐)",        "clang", ["-O2", "-march=rv64gc"]),
        ("Clang rv64gc_zicond(回避)", "clang", ["-O2", "-march=rv64gc_zicond"]),
    ]),
    ("② popcount — 汎用 vs Zbb(cpop 命令)  [GCC]", "popcount.c", "pc", [
        ("GCC rv64gc",     "gcc", ["-O2", "-march=rv64gc"]),
        ("GCC rv64gc_zbb", "gcc", ["-O2", "-march=rv64gc_zbb"]),
    ]),
    ("③ 配列総和 — 最適化レベル -O0 vs -O2  [GCC]", "sumloop.c", "sum", [
        ("GCC -O0", "gcc", ["-O0", "-march=rv64gc"]),
        ("GCC -O2", "gcc", ["-O2", "-march=rv64gc"]),
    ]),
    ("④ 同じコード・同じISA(zicond)でもコンパイラで違う  [GCC vs Clang]", "select.c", "sel", [
        ("GCC  rv64gc_zicond", "gcc",   ["-O2", "-march=rv64gc_zicond"]),
        ("Clang rv64gc_zicond", "clang", ["-O2", "-march=rv64gc_zicond"]),
    ]),
]


def disasm_func(src, cc, args, func):
    """src を cc(gcc/clang)+args でコンパイルし、func の命令行リストを返す。"""
    obj = "/tmp/_cmp.o"
    r = subprocess.run([*CC[cc], *args, "-c", os.path.join(EX, src), "-o", obj],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()
    d = subprocess.run([ODUMP, "-d", "--no-show-raw-insn", obj],
                       capture_output=True, text=True).stdout
    # <func>: から「次の“本物の関数”見出し」まで集める。
    # 内部の <.L..>: 見出しや空行はまたいで継続(objdump はラベル前に空行を入れる)。
    lines, inside = [], False
    for ln in d.splitlines():
        hdr = re.match(r'^[0-9a-f]+ <([^>]+)>:', ln)
        if hdr:
            name = hdr.group(1)
            if name == func:
                inside = True; continue
            if inside and not name.startswith('.L'):
                break                                  # 次の本物の関数 = 終わり
            continue                                   # .L ラベル等は読み飛ばす
        if inside:
            if ln.strip() == "":
                continue                               # 空行はまたぐ
            m = re.match(r'^\s+[0-9a-f]+:\s+(.*)$', ln)
            if m:
                lines.append(m.group(1).strip())
    return lines, None


def main():
    summary = []
    for title, src, func, configs in EXPERIMENTS:
        print("\n" + "=" * 70)
        print("  " + title)
        print("=" * 70)
        counts = []
        for label, cc, args in configs:
            insns, err = disasm_func(src, cc, args, func)
            if insns is None:
                print(f"\n[{label}] コンパイル失敗: {err}")
                counts.append((label, None)); continue
            print(f"\n[{label}]  {func}: {len(insns)} 命令")
            for i in insns:
                print(f"    {i}")
            counts.append((label, len(insns)))
        summary.append((title, counts))

    print("\n" + "#" * 70)
    print("  まとめ(関数あたり静的命令数 / 少ないほど良い傾向)")
    print("#" * 70)
    for title, counts in summary:
        base = next((c for _, c in counts if c), None)
        print(f"\n{title}")
        for label, c in counts:
            tag = ""
            if c and base and c != base:
                tag = f"  ({100*(c-base)//base:+d}%)"
            print(f"  {label:<22} {('%d 命令' % c) if c else '失敗':>10}{tag}")


if __name__ == "__main__":
    main()

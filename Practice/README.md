# Practice — RISC-V コンパイラ/ISA 実験(手を動かす)

図つき版(ブラウザ): **[practice.html](https://mstk13.github.io/MANABI/Practice/practice.html)**

「**コンパイラの最適化や ISA 拡張で、命令がどう減る/速くなるか**」を**実際にコンパイルして確かめる**環境。
docker と docker compose だけあれば、コマンド一発で動く。**使うツールは全部オープンソース**(GCC=GPL / binutils=GPL / QEMU=GPL / Clang・LLVM=Apache-2.0)。プロプライエタリなものは無し=権利問題なし。

## 使い方
```bash
cd Practice
make build      # OSS RISC-V ツールチェーン入りイメージをビルド(初回)
make compare    # 4つの実験:命令がどう変わるかを実測・比較
make run        # -O0 と -O2 の実行時間を QEMU で比較
make shell      # コンテナ内で自由に試す(riscv64-linux-gnu-gcc / clang / qemu-riscv64)
```

## できる実験(`make compare` の中身)
| # | 題材 | 比較 | 何が分かるか |
|---|---|---|---|
| ① | 条件選択 `cond?a:b` | Clang: rv64gc vs **rv64gc_zicond** | **分岐回避**: `czero` で分岐の無い選択に(予測ミスが起きない) |
| ② | popcount | GCC: rv64gc vs **rv64gc_zbb** | **ISA拡張**: `cpop` 命令で **8命令→2命令(-75%)** |
| ③ | 配列総和 | GCC: **-O0 vs -O2** | **コンパイラ最適化**: 31命令→12命令 |
| ④ | `cond?a:b` | **GCC vs Clang**(両方 zicond) | **同じコード・同じISAでもコンパイラで違う**(GCCは分岐, Clangはczero) |

### 実測の抜粋(このマシンで確認済み)
```
② popcount:  GCC rv64gc = 8命令(ライブラリ呼び出し)
             GCC rv64gc_zbb = 2命令  →  cpop a0,a0 / ret   (-75%)

① 条件選択:  Clang rv64gc       = beqz / mv / mv / ret     (分岐)
             Clang rv64gc_zicond = czero.eqz / czero.nez / or / ret  (分岐なし)

④ 同じコード: GCC  rv64gc_zicond = 分岐(czero を使わない)
             Clang rv64gc_zicond = czero(分岐回避)        ← コンパイラ差
```
※ ① は命令数は同じでも **branchless = パイプラインのフラッシュが起きない**のが利点(命令数だけでなく“分岐の有無”が効く)。詳細は [ISA編](../riscv-isa/isa_notes.md) / [パイプライン編](../cpu-pipeline/pipeline_notes.md)。

## 構成
| パス | 役割 |
|---|---|
| `docker/Dockerfile` | OSS ツールチェーン(gcc-riscv64-linux-gnu / clang / binutils / qemu-user) |
| `docker-compose.yml`, `Makefile` | ローカル構築不要のラッパー |
| `examples/*.c` | 題材(select / popcount / sumloop / driver) |
| `compare.py` | 各設定でコンパイル→逆アセンブル→命令数を比較 |

## 自分で試す(`make shell` 後)
```bash
# 好きな C を書いて、march/最適化/コンパイラを変えて逆アセンブル
riscv64-linux-gnu-gcc -O2 -march=rv64gc_zbb -c my.c -o my.o
riscv64-linux-gnu-objdump -d my.o
# 実行(静的リンクして qemu で)
riscv64-linux-gnu-gcc -O2 -static my.c -o my && qemu-riscv64 ./my
```

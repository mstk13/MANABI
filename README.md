# MANABI — 学びノート

**Claude(AI)と一緒に学んだことを、自分用にまとめて蓄積していく場所。**
半導体・コンピュータアーキテクチャ等のトピックを、セッションごとに `.md`(+図 `.html`)で残す。

- **ノート(.md)**: GitHub 上でそのまま整形表示される。
- **図(.html)**: GitHub Pages でインタラクティブに開ける → **https://mstk13.github.io/MANABI/**(public + Pages 有効)。

> 関連: 設計プロジェクト本体は [mstk13/SHISAKU](https://github.com/mstk13/SHISAKU)(作る場所)。
> こちら **MANABI は「学びの蓄積」**(理解のまとめ)。役割を分けて運用する。

## 目次
| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| CPU パイプライン(基礎〜段数の決め方〜分岐予測ミス) | [cpu-pipeline/pipeline_notes.md](cpu-pipeline/pipeline_notes.md) | [入門](https://mstk13.github.io/MANABI/cpu-pipeline/pipeline_basics.html) / [3つの力](https://mstk13.github.io/MANABI/cpu-pipeline/pipeline_depth.html) |
| RISC-V で学ぶ ISA(命令セット・分岐回避・性能) | [riscv-isa/isa_notes.md](riscv-isa/isa_notes.md) | [ISA図解](https://mstk13.github.io/MANABI/riscv-isa/isa.html) |
| コンパイラとは → 最適化(ループ展開/インライン化 等) | [compiler/compiler_notes.md](compiler/compiler_notes.md) | [コンパイラ図解](https://mstk13.github.io/MANABI/compiler/compiler.html) |
| **Practice(手を動かす)**: RISC-V を実際にコンパイルして命令の速さを実験(Docker, OSS) | [Practice/README.md](Practice/README.md) | [実験の図解](https://mstk13.github.io/MANABI/Practice/practice.html) |
| **AIアクセラレータ開発ロードマップ**: AIの中身→設計手法→世の中の事例→未経験から現場ジョインの学習プログラム | [ai-accelerator/ai_accel_notes.md](ai-accelerator/ai_accel_notes.md) | [図解+ロードマップ](https://mstk13.github.io/MANABI/ai-accelerator/ai_accel.html) |
| **HW/RTL設計の要点**: NoC・検証(UVM)・PPA(多コア+NoC型アクセラレータ向け) | [hw-rtl/hw_rtl_notes.md](hw-rtl/hw_rtl_notes.md) | [図解](https://mstk13.github.io/MANABI/hw-rtl/hw_rtl.html) |
| **コアレッシング/MSHR/ライトバック**: アクセスを束ねてメモリ回数を減らす3技術 → IOMMU(PTW)応用と落とし穴 | [coalescing-mshr/coalescing_mshr_notes.md](coalescing-mshr/coalescing_mshr_notes.md) | [図解](https://mstk13.github.io/MANABI/coalescing-mshr/coalescing_mshr_writeback.html) |

## 追加のしかた
1. `トピック名/note.md` を作って書く(図が要れば同じフォルダに `.html`)。
2. この README の目次に1行足す。
3. `git add . && git commit -m "..." && git push` → GitHub 表示・Pages が自動更新。

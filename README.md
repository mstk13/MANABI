# MANABI — 学びノート

**Claude(AI)と一緒に学んだことを、自分用にまとめて蓄積していく場所。**
半導体・コンピュータアーキテクチャ等のトピックを、セッションごとに `.md`(+図 `.html`)で残す。

- **ノート(.md)**: GitHub 上でそのまま整形表示される。
- **図(.html)**: GitHub Pages でインタラクティブに開ける → **https://mstk13.github.io/MANABI/**(public + Pages 有効)。
- **[復習クイズ](https://mstk13.github.io/MANABI/review.html)**: 全トピックのフラッシュカード形式復習アプリ。

> 関連: 設計プロジェクト本体は [mstk13/SHISAKU](https://github.com/mstk13/SHISAKU)(作る場所)。
> こちら **MANABI は「学びの蓄積」**(理解のまとめ)。役割を分けて運用する。

---

## 目次

### AI・ニューラルネット基礎

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| 近年のAIは何をしているか — Transformer端から端(トークン化→Attention+FFN→自己回帰)。学習vs推論・AIの家系 | — | [図解](https://mstk13.github.io/MANABI/modern-ai/modern_ai.html) |
| ニューラルネットの学習(勾配降下) — 学習ループ+山下りを操作。学習率で発散も体感 | — | [図解(山下り操作)](https://mstk13.github.io/MANABI/training/training.html) |

### Llama デコーダの理解

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| Llama decoder 1層のGEMM分解 — 重みGEMM7本+Attnコア2本、演算の8〜9割がGEMM | [notes](llama-decoder/llama_decoder_notes.md) | [GEMM分解](https://mstk13.github.io/MANABI/llama-decoder/llama_decoder_gemm.html) / [モデルの動き](https://mstk13.github.io/MANABI/llama-decoder/model_flow.html) |
| なぜ「タイル」が単位か — 行列積の2Dデータ再利用構造。C出力タイルをクリックでA帯/B帯が光る | — | [図解(クリック)](https://mstk13.github.io/MANABI/why-tile/why_tile.html) |

### Tenstorrent / Tensix（← Llama がここで動く）

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| TT スタックをハード無しで動かす(ttsim) — TT-NN→Metalium→LLK→ttsim の縦構造 + 11 op 実験 | [notes](tt-stack/tt_stack_notes.md) | [図解(レイヤ+再生)](https://mstk13.github.io/MANABI/tt-stack/tt_stack.html) |
| Tensix コア内部(ブロック解説+FW深掘り) — 5 RISC-V / Unpacker / FPU / SFPU / Packer / L1 + 起動フロー | [notes](tensix-core/tensix_core_notes.md) | [図解(起動アニメ)](https://mstk13.github.io/MANABI/tensix-core/tensix_core.html) |
| Tensix 計算エンジン(LLK) — Unpack→FPU(MVMUL)/SFPU(活性)→Pack を実LLKコードで | — | [図解(クリック+再生)](https://mstk13.github.io/MANABI/tensix-compute/tensix_compute.html) |
| **Tensix アーキテクチャ深掘り** — tt-metalソースから読み解いた 5 RISC-V の役割分担 + CB + 同期 + Metalium→Tensix マッピング(matmul例) | [notes](tensix-architecture/tensix_architecture_notes.md) | — |
| Llama 1層 x Tensix コア対応 — 各opがTensixのどのユニット(FPU/SFPU/DM+NoC)で動くか | — | [図解(フロー+断面)](https://mstk13.github.io/MANABI/llama-on-tensix/llama_on_tensix.html) |
| 統合マップ: Llama⇄SW⇄HW — 1処理をクリックで ttnn→LLK→Tensix HWが3列同時に光る | — | [図解(3列連動)](https://mstk13.github.io/MANABI/tt-integration/tt_integration.html) |

### AIアクセラレータ設計（← 自作で理解を深める）

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| AIアクセラレータ開発ロードマップ — AIの中身→設計手法→事例→学習プログラム | [notes](ai-accelerator/ai_accel_notes.md) | [図解+ロードマップ](https://mstk13.github.io/MANABI/ai-accelerator/ai_accel.html) |
| シストリックアレイ(weight-stationary) — 活性→・部分和↓を流しながら積和。3x3アニメ | [notes](systolic-array/systolic_array_notes.md) | [図解(再生可)](https://mstk13.github.io/MANABI/systolic-array/systolic_array.html) |

### RISC-V + LLVM バックエンド自作

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| LLVM バックエンド自作 — 読む前に押さえる前提知識(IR/SSA/TableGen/DAG/ELF/テスト, 全8章対応) | [notes](llvm-backend-prep/prep_notes.md) | — |

### CPU・ISA・パイプライン

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| CPU パイプライン(基礎〜段数の決め方〜分岐予測ミス) | [notes](cpu-pipeline/pipeline_notes.md) | [入門](https://mstk13.github.io/MANABI/cpu-pipeline/pipeline_basics.html) / [3つの力](https://mstk13.github.io/MANABI/cpu-pipeline/pipeline_depth.html) |
| RISC-V で学ぶ ISA(命令セット・分岐回避・性能) | [notes](riscv-isa/isa_notes.md) | [ISA図解](https://mstk13.github.io/MANABI/riscv-isa/isa.html) |
| コンパイラとは → 最適化(ループ展開/インライン化等) | [notes](compiler/compiler_notes.md) | [コンパイラ図解](https://mstk13.github.io/MANABI/compiler/compiler.html) |
| Practice(手を動かす) — RISC-V を実際にコンパイルして命令の速さを実験(Docker, OSS) | [notes](Practice/README.md) | [実験の図解](https://mstk13.github.io/MANABI/Practice/practice.html) |

### メモリ・キャッシュ・インターコネクト

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| キャッシュコヒーレンス(MSI→MOESI) — 状態遷移をボタンで体験 | [notes](cache-coherence/cache_coherence_notes.md) | [図解(クリック遷移)](https://mstk13.github.io/MANABI/cache-coherence/coherence_fsm.html) |
| AMBA CHI(コヒーレント相互接続) — 構造・AXIとの比較・ReadUniqueアニメ | [notes](chi-interconnect/chi_interconnect_notes.md) | [図解(AXI↔CHI再生)](https://mstk13.github.io/MANABI/chi-interconnect/chi_interconnect.html) |
| コアレッシング/MSHR/ライトバック — アクセスを束ねてメモリ回数を減らす3技術 | [notes](coalescing-mshr/coalescing_mshr_notes.md) | [図解](https://mstk13.github.io/MANABI/coalescing-mshr/coalescing_mshr_writeback.html) |
| ECC設計の落とし穴 — メモリのビット化けを直すECCの注意点 | [notes](ecc-design/ecc_design_notes.md) | [図解](https://mstk13.github.io/MANABI/ecc-design/ecc_design.html) |

### HW/RTL設計・物理設計

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| HW/RTL設計の要点 — NoC・検証(UVM)・PPA | [notes](hw-rtl/hw_rtl_notes.md) | [図解](https://mstk13.github.io/MANABI/hw-rtl/hw_rtl.html) |
| 物理設計(論理合成のあと) — フロアプラン→配置→CTS→配線→GDS | [notes](physical-design/pd_notes.md) | [図解](https://mstk13.github.io/MANABI/physical-design/pd.html) |

### English Training

英語学習コンテンツは [English_study](https://github.com/mstk13/English_study) リポジトリに移動しました。

### その他

| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| HWレイヤ全体像 — アプリ→OS→ISA→マイクロアーキ→ゲート→物理 | — | [図解](https://mstk13.github.io/MANABI/hw-layers/hw_layers.html) |

---

## 学習ジャーニー(全体の流れ)
物理設計 → AIアクセラレータ → Llama理解 → CHI → コヒーレンス実装 → 0からのCHI実装 → Tenstorrent実スタック、を各工程クリックで:
**[journey/journey.html](https://mstk13.github.io/MANABI/journey/journey.html)**

---

## 追加のしかた
1. `トピック名/note.md` を作って書く(図が要れば同じフォルダに `.html`)。
2. この README の目次に1行足す。
3. `git add . && git commit -m "..." && git push` → GitHub 表示・Pages が自動更新。

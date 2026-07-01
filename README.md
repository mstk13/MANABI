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
| **ECC設計の落とし穴**: メモリのビット化けを直すECCを実際に作るときの注意点（制御CPU用/AIアクセラレータ用のレビュー指摘を平易に） | [ecc-design/ecc_design_notes.md](ecc-design/ecc_design_notes.md) | [図解](https://mstk13.github.io/MANABI/ecc-design/ecc_design.html) |
| **物理設計(論理合成のあと)**: フロアプラン→配置→CTS→配線→署名/GDS。各段で slack がどう動くかを ORFS gcd 実測で追う | [physical-design/pd_notes.md](physical-design/pd_notes.md) | [図解](https://mstk13.github.io/MANABI/physical-design/pd.html) |
| **シストリックアレイ(weight-stationary)**: AIアクセラの心臓。活性→・部分和↓を流しながら積和を貯める仕組みを3×3でアニメ。段数↔STA↔配置に接続 | [systolic-array/systolic_array_notes.md](systolic-array/systolic_array_notes.md) | [図解(再生可)](https://mstk13.github.io/MANABI/systolic-array/systolic_array.html) |
| **なぜ「タイル」が単位か**: AIの計算=行列積の2Dデータ再利用構造から。C出力タイルをクリックで必要なA帯/B帯が光る。要素ごと vs タイルのメモリ比較 | [why-tile/why_tile.html(図)](https://mstk13.github.io/MANABI/why-tile/why_tile.html) | [図解(クリック)](https://mstk13.github.io/MANABI/why-tile/why_tile.html) |
| **★統合マップ: Llama1層⇄SW⇄HW**: 1処理をクリックすると ttnn→LLKカーネル→Tensix HWユニット が3列同時に光る。TTの全体を1枚で紐付け | [tt-integration/tt_integration.html(図)](https://mstk13.github.io/MANABI/tt-integration/tt_integration.html) | [図解(3列連動)](https://mstk13.github.io/MANABI/tt-integration/tt_integration.html) |
| **Llama 1層 × Tensix コア対応**: RMSNorm/射影/RoPE/QKᵀ/softmax/SiLU/残差 が Tensix のどのユニット(FPU/SFPU/REDUCE/DM+NoC)で動くかをフロー+コア断面で。クリックで該当ユニットが光る | [llama-on-tensix/llama_on_tensix.html(図)](https://mstk13.github.io/MANABI/llama-on-tensix/llama_on_tensix.html) | [図解(フロー+断面)](https://mstk13.github.io/MANABI/llama-on-tensix/llama_on_tensix.html) |
| **Tensix 計算エンジン(LLK)**: Unpack→FPU(MVMUL)/SFPU(活性)→Pack を実LLKコードで。自作アレイ↔Tensix(MVMUL/Dst/fidelity/throttle/reuse/SFPU)対応。matmul→活性を再生 | [tensix-compute/tensix_compute.html(図)](https://mstk13.github.io/MANABI/tensix-compute/tensix_compute.html) | [図解(クリック+再生)](https://mstk13.github.io/MANABI/tensix-compute/tensix_compute.html) |
| **Tenstorrentスタックをハード無しで動かす(ttsim)**: TT-NN→Metalium→LLK→ttsim の縦を実機無しで。ttnn.add が流れる様子を再生+11 op実験結果 | [tt-stack/tt_stack_notes.md](tt-stack/tt_stack_notes.md) | [図解(レイヤ+再生)](https://mstk13.github.io/MANABI/tt-stack/tt_stack.html) |
| **キャッシュコヒーレンス状態機械(MSI→MOESI)**: 1ラインの I/S/E/M/O 遷移をボタンで体験。E=read-then-writeのバス削減/O=書戻し削減。実装はSHISAKUの動くPython | [cache-coherence/cache_coherence_notes.md](cache-coherence/cache_coherence_notes.md) | [図解(クリック遷移)](https://mstk13.github.io/MANABI/cache-coherence/coherence_fsm.html) |
| **AMBA CHI(コヒーレント相互接続)**: 構造(層/ノード/4チャネル)・AXIとの比較・ReadUniqueの動きをアニメ。AXI↔CHI切替で「スヌープの有無」を体感。NoCのVC/credit/デッドロック回避に接続 | [chi-interconnect/chi_interconnect_notes.md](chi-interconnect/chi_interconnect_notes.md) | [図解(AXI↔CHI再生)](https://mstk13.github.io/MANABI/chi-interconnect/chi_interconnect.html) |
| **近年のAIは何をしているか**: Transformerの端から端(トークン化→埋め込み→Attention+FFN×N→次トークン予測→自己回帰)。学習vs推論・AIの家系(LLM/ViT/拡散/MoE) | [modern-ai/modern_ai.html(図)](https://mstk13.github.io/MANABI/modern-ai/modern_ai.html) | [図解(クリック)](https://mstk13.github.io/MANABI/modern-ai/modern_ai.html) |
| **Llama decoder 1層のGEMM分解**: 推論ターゲットの1層を分解→重みGEMM7本+Attnコア2本、演算の8〜9割がGEMM。各ステップの形/役割をクリックで | [llama-decoder/llama_decoder_notes.md](llama-decoder/llama_decoder_notes.md) | [GEMM分解(クリック)](https://mstk13.github.io/MANABI/llama-decoder/llama_decoder_gemm.html) / [モデルの動き(再生)](https://mstk13.github.io/MANABI/llama-decoder/model_flow.html) |

## 🗺 学習ジャーニー(全体の流れ)
物理設計 → AIアクセラレータ → Llama理解 → CHI → コヒーレンス実装 → 0からのCHI実装 → Tenstorrent実スタック、を各工程クリックで:
**[journey/journey.html](https://mstk13.github.io/MANABI/journey/journey.html)**

## 追加のしかた
1. `トピック名/note.md` を作って書く(図が要れば同じフォルダに `.html`)。
2. この README の目次に1行足す。
3. `git add . && git commit -m "..." && git push` → GitHub 表示・Pages が自動更新。

# AIアクセラレータ 開発ロードマップ(未経験 → 設計現場にジョイン)

図つき版(ブラウザ): **[ai_accel.html](https://mstk13.github.io/MANABI/ai-accelerator/ai_accel.html)**

将来 Tenstorrent で AI アクセラレータを開発するために、**AIそのもの → 設計手法 → 世の中の事例 → 学習プログラム**を一気にまとめたノート。
既存の手元資産(SHISAKU=作る / DENNO/Accel=自作アクセラ / Practice=コンパイラ実験 / SW/TT_study=Tenstorrent ハードフリー)を各段に組み込む。

---

# A. まず「AIそのもの」— 設計者が知るべき中身

## A-1. なぜ専用ハードが要るか
AIの計算は **同じ単純演算(積和)を超大量に**行う。汎用CPUは制御が得意だが積和の物量で非効率。
→ **積和(MAC)を空間的に大量に並べる**専用ハード=AIアクセラレータが効く。

## A-2. ニューラルネットの本質 = 行列積(GEMM)
- ニューロン1層 = `y = activation(W·x + b)`。**W·x が行列×ベクトル/行列(GEMM)**。
- **CNN(畳み込み)** も im2col で GEMM に変換できる。
- **Transformer/Attention(今の主流・LLM)** も中身は GEMM の塊(QKV射影・スコア・FFN)。
- 結論:**演算の8〜9割は GEMM**。だからアクセラレータの主役は積和アレイ。

## A-3. 学習(training)と推論(inference)
- **学習**:大量データで重みを最適化(順伝播+逆伝播/勾配)。計算・メモリが重い。**地上/データセンタ**。
- **推論**:学習済みモデルで答えを出す(順伝播のみ)。**エッジ/軌道上/製品**で動かす本番。
- 自作アクセラレータはまず**推論**が現実的(学習は後段)。

## A-4. 数値表現と量子化(超重要)
- FP32 → FP16/**BF16** → **INT8 / INT4**。低精度ほど面積・電力・帯域が得。
- **量子化**=低精度に落として速く小さく。推論では精度をほぼ保てる → HPC推論の必須技術。
- アクセラレータは INT8/INT4 MAC + スケール(dequant)で作るのが定石。

## A-5. メモリとデータ移動(memory wall)
- **計算よりデータ移動の方が高コスト**(電力も時間も)。
- 鍵は**再利用**:一度読んだ重み/活性化をできるだけ使い回す → **データフロー設計**。
- **arithmetic intensity(演算/バイト)** と **ルーフライン**で「計算律速か帯域律速か」を見る。

---

# B. AIアクセラレータの設計

## B-1. 心臓:MAC アレイ / シストリックアレイ
- 1個の MAC(積和)→ PE(重み保持)→ **N×N シストリックアレイ**(行列積を空間展開)。
- 手元に最小実装あり:[`SHISAKU/DENNO/Accel/rtl/mac.sv`](https://github.com/mstk13/SHISAKU/blob/main/DENNO/Accel/rtl/mac.sv)。

## B-2. データフロー(再利用の戦略, Eyeriss/Sze)
- **weight-stationary**:重みを止めて活性化を流す(GEMM向き, TPU型)。
- **output-stationary**:出力を止めて積和を貯める。
- **row-stationary**(Eyeriss):エネルギー最小化。
- 「どれを止めるか」で再利用とエネルギーが変わる。

## B-3. メモリ階層
- 外部 DRAM/HBM ←(DMA)→ オンチップ **スクラッチパッド SRAM** ← アレイ。
- **ダブルバッファ**で転送と計算をオーバラップ(アレイを遊ばせない)。
- memory wall 対策=量子化(帯域削減)+ 再利用 + 近接メモリ。

## B-4. 付随ユニット
- 非GEMMの **softmax / 正規化(RMSNorm/LayerNorm) / 活性化(SiLU等) / RoPE** を小さなベクタ/特殊関数ユニットで。

## B-5. SW スタック(ハードだけでは動かない)
- モデル(PyTorch等)→ **コンパイラ/グラフ最適化** → **カーネル** → **ランタイム** → アクセラレータ。
- ハードと同じくらい SW が重要(命令/カーネルの境界、データ配置、量子化)。

## B-6. 設計の流れ
**ワークロード分析 → アーキ設計 → RTL → 検証(numpy golden/PCC)→ PD(面積/電力/性能)**。
手元で一周できる:設計=[`DENNO/Accel`](https://github.com/mstk13/SHISAKU/tree/main/DENNO/Accel)、検証=SHISAKUコンテナ(Verilator/cocotb)、PD=[`physical_design_flow`](https://github.com/mstk13/SHISAKU/blob/main/docs/physical_design_flow.md)。

---

# C. 世の中の事例・アプローチ(memory wall をどう殴るか)

| 会社/製品 | アプローチ | 特徴 |
|---|---|---|
| **Google TPU** | 大型 weight-stationary **systolic array** + 大SRAM | 教科書的。あなたの基本路線 |
| **NVIDIA**(Tensor Core) | SIMT + 行列積命令(MMA)+ HBM | 汎用GPUの王者、CUDAエコシステム |
| **Tenstorrent**(Tensix) | 多数の **Tensix コア + NoC**、**RISC-V** 制御、dataflow、チップレット(OCA) | ★あなたのターゲット。SWは Metalium/TT-NN(→ [`SW/TT_study`](https://github.com/mstk13/SHISAKU/tree/main/SW/TT_study)) |
| **Cerebras** | ウェハスケール、巨大オンチップSRAM | 重みをオンチップに載せる極端解 |
| **Groq**(LPU) | 完全決定論・コンパイラスケジュール | 帯域不確定性を排除 |
| **SambaNova**(RDU) | 再構成可能データフロー | 柔軟性 |
| **Graphcore**(IPU) | MIMD + 大量オンチップメモリ | 並列モデルの別形 |
| **Etched**(Sohu) | Transformer 専用 ASIC | 究極の特化 |

→ Tenstorrent は「**RISC-V + 多コア + dataflow + チップレット**」。あなたの RISC-V/自作IP路線と地続き。

---

# D. 学習プログラム(0 → 設計現場にジョイン)

未経験から効率よく、AIアクセラレータ設計チームで戦力になるための段階。各段に**到達点・成果物・教材**。

| Phase | 学ぶこと | 到達/成果物 | 手元資産・教材 |
|---|---|---|---|
| **0 前提** | デジタル設計(RTL/検証)、CPUアーキ、線形代数/行列積 | Verilator/cocotbでRTLを回せる | SHISAKUコンテナ、MANABI(pipeline/isa/compiler) |
| **1 AI基礎** | NN/CNN/Transformerの計算、学習vs推論、量子化(INT8) | numpyで forward + 量子化を実装 | Sze "Efficient Processing of DNNs", d2l.ai |
| **2 心臓を作る** | MAC→PE→N×Nシストリックアレイ | 自作アレイ + numpy golden(PCC) | DENNO/Accel(mac.sv が起点) |
| **3 データフロー&メモリ** | weight/output stationary、スクラッチパッド+DMA、ルーフライン | タイル化GEMM、帯域律速の理解 | Eyeriss論文、Gemmini |
| **4 量子化&1層** | INT8 GEMM+dequant、Transformer 1層 | 1層を流して golden と一致 | FlashAttention、各モデルの論文 |
| **5 SWスタック&実機文化** | コンパイラ/カーネル/ランタイム、本物の設計フロー | **Tenstorrent を実機なしで体験** | SW/TT_study(ttsim ハードフリー)、tt-metal docs |
| **6 統合&PPA** | 面積/タイミング/電力で評価、ポートフォリオ化 | 自作アクセラのGDS+PPA、公開 | OpenROAD(physical_design_flow), Practice |

## 現場で効くスキル(チームが求める“T字”)
- **縦**(深く1つ):RTL設計+検証 / マイクロアーキ / データフロー / 量子化 / SWスタック のどれか。
- **横**(全体俯瞰):AIの計算→アーキ→RTL→検証→PPA の一周を**自分で通した経験**。
- 最短ルート=「**小さくても end-to-end の自作アクセラレータ**」+「**本物のスタック(Tenstorrent)をハードなしで触った経験**」。これが面接・現場で一番効く。

## 一次情報・教材
- 概論: Sze et al. "Efficient Processing of Deep Neural Networks"(arXiv 1703.09039)
- 系譜: TPU(arXiv 1704.04760)/ Gemmini(arXiv 1911.09925)/ Eyeriss(eyeriss.mit.edu)
- モデル: Attention(1706.03762)/ FlashAttention(2205.14135)/ 各Llama
- AI基礎: d2l.ai(Dive into Deep Learning, 無料)
- Tenstorrent: tt-metal(github.com/tenstorrent/tt-metal)、[`SW/TT_study`](https://github.com/mstk13/SHISAKU/tree/main/SW/TT_study)
- 既存まとめ: [DENNO/references](https://github.com/mstk13/SHISAKU/blob/main/DENNO/references.md)

## 関連(MANABI内)
- [パイプライン](../cpu-pipeline/pipeline_notes.md) / [ISA](../riscv-isa/isa_notes.md) / [コンパイラ](../compiler/compiler_notes.md) / [Practice](../Practice/README.md)

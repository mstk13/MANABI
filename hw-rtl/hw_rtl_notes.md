# HW/RTL 設計の要点 — NoC・検証(UVM)・PPA

図つき版(ブラウザ): **[hw_rtl.html](https://mstk13.github.io/MANABI/hw-rtl/hw_rtl.html)**

AIアクセラレータ(多コア+NoC型)の HW/RTL 設計で“現場ですぐ効く”一般技術のまとめ。

## 1. 設計の流れ
仕様/アーキ → **マイクロアーキ**(段数/FIFO深さ/調停)→ RTL(SystemVerilog)→ **検証**(UVM/cocotb, CRV+カバレッジ)→ 合成+STA → P&R/電力(PPA)。
新人がまず頼られるのは**検証**。RTLを“書く”より「**大きな既存環境を読んで直す/検証する**」力が効く。

## 2. NoC(Network-on-Chip)
各タイル(コア)をルータでつなぎ、データ(パケット)をホップで運ぶ(共有バスでなく格子=dataflow)。
ルータの中身=**調停(アービタ)/フロー制御(valid-ready, credit)/バッファ(FIFO)/ルーティング(XY等)/デッドロック回避(VC)**。
→ あなたの AXI調停・APLIC優先度・ECCハンドシェイク・Task2のバッファ解析が起点。デッドロック回避とルーティングが新規・要学習。

## 3. 検証(UVM)
UVM = SystemVerilog の検証フレームワーク。役割: **Sequence/Sequencer(刺激生成)→ Driver(印加)→ DUT → Monitor(観測)→ Scoreboard(golden比較)→ Coverage(網羅度)**。
cocotb で同じ構造を作れるので、まず cocotb で型を体得 → UVM へ。3点セット=**制約付きランダム(CRV)/scoreboard/カバレッジ**。
「動いた」でなく「**網羅して壊れないと示せる**」のが価値。

## 4. PPA / タイミング
STA(クリティカルパス・スラック)/面積/電力(クロックゲーティング等)。
あなたは OpenROAD(`run_flow.sh`)で fmax/面積/電力を実測できる(MAC で実証済)→ NoC ルータも同様に評価。

## 5. 手元での練習
- **NoC**: 2入力アービタ → ルータ → 2×2 mesh を SHISAKU で自作 + cocotb 検証。
- **検証**: cocotb で driver/monitor/scoreboard/coverage を組む → UVM教材へ。
- **性能モデル**: NoC のレイテンシ/スループット/詰まりを Python でモデル(Task2 の手法)。
- **PPA**: 作ったルータを OpenROAD で評価。

## 関連
[パイプライン](../cpu-pipeline/pipeline_notes.md) / [ISA](../riscv-isa/isa_notes.md) / [コンパイラ](../compiler/compiler_notes.md) / [AIアクセラレータ](../ai-accelerator/ai_accel_notes.md) / [Practice](../Practice/README.md)

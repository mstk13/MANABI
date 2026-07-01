# Tensix コア内部 — ブロックごと解説（Tenstorrent）

> Tenstorrent AIアクセラレータ（Grayskull / Wormhole / Blackhole）の演算コア「Tensix」の中身。
> **図（ブラウザ）**: https://mstk13.github.io/MANABI/tensix-core/tensix_core.html
> 関連: [AIアクセラレータ ロードマップ](../ai-accelerator/ai_accel_notes.md) / [シストリックアレイ](../systolic-array/systolic_array_notes.md)

## 一言で
Tensix は「**5個の小さな RISC-V（指揮者）**」＋「**行列/ベクトル演算エンジン（奏者）**」の組。
RISC-V は計算せず **命令を撃つだけ**。データ本体は RISC-V を通らず、**Unpacker / Packer が L1 を直接叩く**（＝コアがボトルネックにならない）。
制御は **Tensix ISA**（RISC-V 命令とは別物）で、unpack / math / pack の 3 スレッドが並列パイプラインを回す。

## 全体データフロー（タイル単位）
```
        L1 SRAM (1.5 MB / コア)  ※明示管理・キャッシュではない
   ┌──────────┬──────────────────────┬───────────┐
   │ 入力CB   │ kernel/scratch/semaph │ 出力CB    │
   └────┬─────┴──────────────────────┴─────▲─────┘
        │ (Unpacker が読む)               │ (Packer が書く)
        ▼                                  │
  ┌───────────┐   ┌──────────┐   ┌────────┴───┐
  │ Unpacker0 │──▶│  SrcA    │   │  Packer    │
  │ Unpacker1 │──▶│  SrcB    │   └────▲───────┘
  └───────────┘   └────┬─────┘        │
                       ▼              │
                 ┌───────────┐        │
                 │ FPU(行列) │───────▶ Dst レジスタ (32bit, 4〜16タイル)
                 └───────────┘        ▲
                 ┌───────────┐        │
                 │ SFPU(ベク)│◀──────▶┘  (LReg 経由で読み書き)
                 └───────────┘
```

## ① 5つの Baby RISC-V コア（制御プレーン）
小さなインオーダー RISC-V ×5。**演算はせず、命令発行とデータ移動の指揮に徹する**。
1本の compute kernel を書くと、コンパイラが **3バイナリ（TRISC0/1/2）** に分割し、別コアで並列に走らせる。

| コア | 別名 | 役割 |
|---|---|---|
| **BRISC** | Data Movement 0 | NoC経由のデータ移動・ボード設定。主に**書き出し**側 |
| **NCRISC** | Data Movement 1 | NoC経由のデータ移動。主に**読み込み**側 |
| **TRISC0** | UNPACK | 2つの Unpacker を制御 |
| **TRISC1** | MATH | FPU・SFPU へ演算命令を発行 |
| **TRISC2** | PACK | Packer を制御 |

例え：RISC-V は**指揮者**、FPU/SFPU は**奏者**。指揮者は音を出さず、タクトを振る（Tensix命令を撃つ）だけ。

## ② Unpacker（アンパッカ）× 2
L1 のタイルを読み、**HW でフォーマット変換**して SrcA/SrcB/Dst に置く DMA エンジン。変換は「**gasket**」で行い、ソフトのデコードを不要にする。
- **Unpacker 0** → SrcA と Dst に接続
- **Unpacker 1** → SrcB に接続

役割は、DRAM/L1 の**フラットなテンソル配置**と、コプロセッサが期待する **tilize 済み内部配置**の橋渡し。BFP8 / FP16 / FP32 の形式差もここで吸収。

## ③ SrcA / SrcB レジスタ（行列エンジンの入力）
- **ダブルバッファ**：各々2バンク、1バンク＝1タイル。計算中に次タイルを裏で充填 → パイプラインを止めない。
- **精度**：現行世代で**最大19bit**（Dstより低精度）。1タイル＝1024要素相当。

## ④ FPU（行列エンジン / Matrix Engine）
**乗算器＋加算器を組み合わせた「FPUセル」の行列**。SrcA・SrcB を読み、結果を Dst へ**蓄積**。各セルが実行できるのは：
1. 累積ドット積（matmul 本体）
2. 累積 要素ごと加算
3. 累積 要素ごと乗算
4. 要素ごと加算

密行列積・畳み込み・プーリング担当。使う前に `mm_init()` 等の初期化が要る。
**Math Fidelity**：データ形式に応じ完全精度には**最大4回の乗算フェーズ** — 精度と速度のトレードオフ。

## ⑤ SFPU（ベクトルエンジン / SIMD FP Unit）
活性化・超越関数・要素ごと演算など**行列積以外**を担う SIMD。FPU と決定的に違う点：
- **ロード/ストア型**：Dst を直接は演算できず、内部 **LReg**（Wormhole で 32要素×32bit）へロード→計算→Dst へ書き戻す。
- **32bit 入力**で計算可。sigmoid, exp, reciprocal 等を**ソフト的に組める**（LLK で実装）。チェーン可。

> **ttsim / LLK テストとの接点**：~/tt-metal のシミュレータで叩く LLK テストの多くはこの **SFPU** 層。

## ⑥ Dst レジスタ（destination / 共有ワークスペース）
compute API から**唯一直接見えるレジスタセット**。カーネルの主戦場。
- **FPU の出力先**であり **SFPU の入力兼出力**。
- **32bit 要素**（Src より高精度）。
- 容量は構成依存で**4〜16タイル**（16bit＋DB無効=16 / 有効=8 / 32bit は半分）。
- タイル内部は **face 単位**：`dst_reg[0:3]`=1枚目の face…。32×32タイル＝16×16 の face F0〜F3（row-major）。

## ⑦ Packer（パッカ）
Dst の結果を **gasket 変換**して L1 へ書き戻す DMA エンジン。**別コア（TRISC2）で並行動作**するので、math が次タイルを計算中に前の結果を書き出せる。

## ⑧ L1 SRAM（1.5 MB / コア）
スクラッチパッド（**キャッシュではない**、明示管理）。中身は入力/出力の **Circular Buffer(CB)**、5コア分のカーネルコード、scratch、セマフォ。
CB は生産側 `cb_reserve_back → cb_push_back`、消費側 `cb_wait_front → cb_pop_front` で同期。

## パイプライン同期の実際
```
Dst獲得 → unpack(L1→Src/Dst) → compute(FPU/SFPU) → commit
        → 入力pop / 出力reserve → packer待ち → pack(Dst→L1) → Dst解放
```
これで**通信（unpack/pack）と計算（math）が重なり**、3コアが常に動き続ける。

## RTL設計視点のまとめ
| 観点 | 要点 |
|---|---|
| データパスの主役 | Unpacker/Packer の gasket、SrcA/B↔FPU↔Dst の配線、Dst↔LReg↔SFPU |
| 制御プレーン | TRISC0/1/2 が発行する Tensix ISA（RISC-V ISAと別）を single-issue in-order で3スレッド並行 |
| 精度の設計判断 | Src=19bit / Dst=32bit / Math Fidelity のフェーズ数 — 面積・電力・精度のトレードオフが RTL に直結 |

## 出典
- [Compute Engines and Data Flow within Tensix — TT-Metalium docs](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/advanced_topics/compute_engines_and_dataflow_within_tensix.html)
- [Getting started with Tensix Core and Low-level Kernels — tt-llk](https://github.com/tenstorrent/tt-llk/blob/main/docs/llk/l2/top_level_overview.md)
- [tt-metal METALIUM_GUIDE.md](https://github.com/tenstorrent/tt-metal/blob/main/METALIUM_GUIDE.md)
- [Tenstorrent Blackhole architecture guide (anuraagw.me)](https://anuraagw.me/blog/blackhole-architecture)
- [Tensix Core アーキテクチャ解説 — Tenstorrent Japan](https://speakerdeck.com/tenstorrent_japan/tensix-core-akitekutiyajie-shuo)

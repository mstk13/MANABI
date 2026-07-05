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
| **BRISC** | Data Movement 0 (RISCV_0) | **Reader** — DRAM/L1→CBへ読み込み(NOC0) + マスター制御(他コアへGO/DONE管理) |
| **NCRISC** | Data Movement 1 (RISCV_1) | **Writer** — CB→DRAM/L1へ書き出し(NOC1) + CB設定ロード補助 |
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

---

## ⑨ ファームウェア深掘り — tt-metal ソースから読み解く制御の実態

> 以下は `~/tt-metal` のソースコード（主に Wormhole 向け）を直接読んで得た知見。
> ドキュメントに書かれていない内部プロトコルや設計判断を含む。

### 9-1. 2フェーズ起動プロトコル（LOAD → GO）

BRISC は subordinate を一斉に GO させるのではなく、**2段階**で起動する。

```
Host dispatch → BRISC mailbox に launch message 着信
  ↓
BRISC: NCRISC に LOAD 信号 → NCRISC が CB を pre-populate (NoC DMA)
  ↓
BRISC: NCRISC LOAD 完了を待つ
  ↓
BRISC: NCRISC に GO + TRISC0/1/2 に GO を同時発行
  ↓
全 subordinate が kernel 実行 → 各自 DONE を返す
  ↓
BRISC: 全 DONE を確認 → 次の launch message を待つ
```

**なぜ 2 フェーズか**: compute kernel が CB から読む前にデータが L1 に無いと空読みになる。
NCRISC に先行して CB をロードさせることで、TRISC が走り始めた瞬間からデータが揃っている。
これは**プリフェッチ付きダブルバッファリング**の一種。

**同期構造体** (`core_config.h:21-29`):
```c
struct subordinate_map_t {
    volatile uint8_t dm1;     // NCRISC
    volatile uint8_t trisc0;
    volatile uint8_t trisc1;
    volatile uint8_t trisc2;
};
```
各フィールドに書き込む値で状態遷移:
| 値 | 定数名 | 意味 |
|---|---|---|
| 0x00 | `RUN_SYNC_MSG_DONE` | subordinate 完了 |
| 0x01 | `RUN_SYNC_MSG_LOAD` | NCRISC に CB ロード指示 |
| 0x40 | `RUN_SYNC_MSG_INIT` | 初期化待ち |
| 0x80 | `RUN_SYNC_MSG_GO` | kernel 実行開始 |

**ポーリングベース**（ハードウェア割込みなし）: 各 subordinate は `invalidate_l1_cache()` してから sync byte を再読みする busy-wait ループ。
割込みを使わない理由は、起動レイテンシの予測可能性とシンプルさ。RISC-V 割込みコントローラの面積を節約しつつ、数十サイクルの同期で十分な粒度。

**ソースファイル**:
- `tt_metal/hw/firmware/src/tt-1xx/brisc.cc` (354-425: main loop, 440-444: LOAD→GO)
- `tt_metal/hw/firmware/src/tt-1xx/ncrisc.cc` (77-93: wait loop)
- `tt_metal/hw/firmware/src/tt-1xx/trisc.cc` (135-149: wait loop)
- `tt_metal/hw/inc/hostdev/dev_msgs.h` (98-109: sync 定数)

### 9-2. NCRISC の独自 IRAM（16KB）

5つの RISC-V の中で **NCRISC だけが独立した命令メモリ (IRAM)** を持つ。

| リソース | BRISC | NCRISC | TRISC0/1/2 |
|---------|-------|--------|------------|
| FW サイズ | 6KB+256B | 2KB | 各1.5KB |
| Kernel サイズ | — | **16KB (IRAM)** | 各1432KB (L1共有) |
| ローカルメモリ | 4KB | 4KB | 各2KB |
| 命令メモリ配置 | L1 共有 | **0xFFC00000 (専用)** | L1 共有 |

**なぜ NCRISC だけ独自 IRAM か**: NCRISC の datamovement kernel は L1 を大量に読み書きする。
命令フェッチと DMA データが同じ L1 を競合すると**バンクコンフリクト**が発生し帯域が半減する。
専用 IRAM に命令を置くことで、L1 帯域を 100% データ転送に使える。
BRISC は制御のみ（帯域不要）、TRISC は演算命令を FPU/SFPU に撃つだけ（命令密度低い）なので L1 共有で問題ない。

**ロード手順**: BRISC が kernel launch 時に NCRISC のカーネルコードを L1 → IRAM へコピーする (`brisc.cc:141`)。

### 9-3. TT-NN op → Metalium kernel の具体的なマッピング

Python の `ttnn.matmul()` がハードウェアに届くまでの実際のコードパス:

```
ttnn.matmul(A, B)                    # ① Python API
  ↓
ttnn/operations/matmul.py            # ② ProgramConfig 選択
  ↓                                     (MultiCoreReuse / MultiCoreReuseMultiCast / ...)
MatmulDeviceOperation::execute()     # ③ C++ Device Operation
  ↓
create_program()                     # ④ Program Factory
  ↓                                     CB作成 + kernel登録
  ├─ CreateKernel(dm_in0_sender.cpp, RISCV_0, NOC_0)   # Reader → NCRISC
  ├─ CreateKernel(dm_in1_sender.cpp, RISCV_1, NOC_1)   # Reader → BRISC
  └─ CreateKernel(compute.cpp, ComputeConfig{...})       # Compute → TRISC0/1/2
```

**Program Factory の中身** (`minimal_matmul_program_factory.cpp`):
1. **CB 作成** (306-322行): 入力 CB0/CB1 + 出力 CB16 のサイズ・フォーマットを設定
2. **Compile-time args** (446-469行): ブロック寸法 (M_block, K_block, N_block)、サブブロック寸法、タイルサイズ
3. **Kernel 登録** (478-638行): DataMovement / Compute の各カーネルを CreateKernel で登録
4. **Runtime args** (640+行): テンソルアドレス、形状パラメータ

**設計上の着目点**:
- **DataMovement kernel は RISCV_0 / RISCV_1 に割り当てられる** — これは BRISC と NCRISC に対応。
  どちらの NoC (NOC_0 / NOC_1) を使うかも指定する。2本の独立 NoC で読み/書きの帯域を分離。
- **Compute kernel は自動的に TRISC0/1/2 に 3分割される** — UNPACK/MATH/PACK マクロで条件コンパイル。
  1つのソースから 3バイナリが生まれるのは、プログラマの負担を減らしつつ HW の3スレッド並列を活かすため。

### 9-4. Compute Kernel 内部 — 命令発行のパターン

Compute kernel は `UNPACK()` / `MATH()` / `PACK()` マクロで 3 スレッドに命令を振り分ける:

```cpp
// eltwise_binary.cpp の実際のパターン
tile_regs_acquire();                       // Dst レジスタを確保
UNPACK(llk_unpack_AB(cb0, cb1, i, i));     // → TRISC0: L1→SrcA/SrcBへ展開
MATH(llk_math_eltwise_binary(i));          // → TRISC1: FPU で SrcA OP SrcB → Dst
tile_regs_commit();                        // Dst を packer に渡す準備完了
PACK(llk_pack(i, cb_out));                 // → TRISC2: Dst → L1 出力CBへ書き戻し
```

**matmul の場合の MOP (Math Operation) 設定** (`llk_math_matmul.h:37-77`):
- FPU の **アドレス修飾ユニット** を設定し、SrcA/SrcB/Dst のポインタを自動インクリメント
- 32×32 タイルの内部を **8行チャンク**単位で処理（8行 × 16列 = 128要素を1サイクルで）
- **Math Fidelity** に応じて乗算フェーズを 1〜4 回繰り返す（精度↑ = スループット↓）

### 9-5. メモリマップ（Wormhole / L1 レイアウト）

```
L1 SRAM (1464 KB) — アドレス空間:
0x0000_0000  ┌─ Application data (CB, テンソル)
             │
0x0001_0000  ├─ Mailbox region (12.6 KB)
             │   +0x04: NCRISC halt stack
             │   +0x08: subordinate_sync (4 bytes)
0x0001_6000  ├─ BRISC FW (6.3 KB)
0x0001_8600  ├─ NCRISC FW (2 KB)
0x0001_8E00  ├─ TRISC0 FW (1.5 KB)
0x0001_9600  ├─ TRISC1 FW (1.5 KB)
0x0001_9E00  ├─ TRISC2 FW (1.5 KB)
0x0001_A600  └─ System reserved
             
ローカルメモリ (各 RISC-V private):
0xFFB0_0000  BRISC/NCRISC 各4KB, TRISC各2KB

NCRISC IRAM (命令専用):
0xFFC0_0000  16KB (NCRISC のみ)

HW レジスタ:
0xFFB1_1000  TDMA (Tensor DMA)
0xFFE4_0000  Instruction Buffer
0xFFE8_0000  PC Buffer
0xFFEF_0000  Tensix Config
0xFFB8_0000  MOP Config (Math Operations)
```

### 9-6. 自作アクセラレータとの対比 — 設計判断の考察

| 設計判断 | Tensix のやり方 | 自作 DENNO での対応 | 考察 |
|---------|---------------|-------------------|------|
| 制御と演算の分離 | 5 RISC-V は命令を撃つだけ、データは Unpacker/Packer が直接 L1 を叩く | CPU(RV32IM) が CSR でキック、systolic array が自律実行 | 同じ思想。制御プレーンをデータパスから分離するのがアクセラレータの基本 |
| データ移動と演算の並行 | NCRISC(DMA) と TRISC(compute) が独立に走る。CB で同期 | DMA + ダブルバッファ + 演算を重ねる設計（仕様書 REQ-ACC-004） | Tensix は 5コアで実現、DENNO は FSM + DMA で実現。本質は同じ |
| 同期方式 | ポーリング（busy-wait on shared memory）。割込みなし | APLIC 割込みで完了通知 | Tensix はコア間レイテンシが数十 ns なのでポーリングが合理的。DENNO は CPU↔Accel 間がバス越しなので割込みが合理的 |
| 命令メモリ分離 | NCRISC だけ独自 IRAM（L1 帯域を DMA に全振り） | 未検討 | DMA コントローラに独立 IRAM は有効。自作でも DMA FSM の制御 ROM を分離する価値あり |
| タイル単位処理 | 32×32 固定タイル。Unpacker/Packer が format 変換 | タイルサイズは可変（4×4 アレイ ↔ 入力行列のブロッキング） | 固定タイルは HW 簡素化に有利。可変は柔軟だが制御が複雑。**自作では最初は固定が現実的** |
| 精度トレードオフ | Math Fidelity（乗算フェーズ 1-4 回）で速度↔精度を選択 | INT8×INT8→INT32 固定（量子化前提） | Tensix は多精度対応で汎用的。DENNO は INT8 推論特化で面積効率を優先。**用途が絞れるなら特化が正しい** |

---

## 出典
- [Compute Engines and Data Flow within Tensix — TT-Metalium docs](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/advanced_topics/compute_engines_and_dataflow_within_tensix.html)
- [Getting started with Tensix Core and Low-level Kernels — tt-llk](https://github.com/tenstorrent/tt-llk/blob/main/docs/llk/l2/top_level_overview.md)
- [tt-metal METALIUM_GUIDE.md](https://github.com/tenstorrent/tt-metal/blob/main/METALIUM_GUIDE.md)
- [Tenstorrent Blackhole architecture guide (anuraagw.me)](https://anuraagw.me/blog/blackhole-architecture)
- [Tensix Core アーキテクチャ解説 — Tenstorrent Japan](https://speakerdeck.com/tenstorrent_japan/tensix-core-akitekutiyajie-shuo)
- tt-metal ソースコード直接読解 (2026-07): `hw/firmware/src/tt-1xx/brisc.cc`, `ncrisc.cc`, `trisc.cc`, `hw/inc/internal/tt-1xx/wormhole/dev_mem_map.h`, `core_config.h`, `hostdev/dev_msgs.h`, `impl/dispatch/kernels/cq_dispatch.cpp`, `kernels/compute/eltwise_binary.cpp`, `ttnn/cpp/ttnn/operations/experimental/minimal_matmul/`

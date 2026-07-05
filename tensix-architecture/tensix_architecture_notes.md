# Tensix アーキテクチャ深掘り — 5 RISC-V の役割 + Metalium マッピング

> **tt-metal ソースコード**（firmware, kernel, ProgramFactory）を実際に読んで整理した、
> Tensix コア内部の動作フロー。
>
> 前提知識: [Tensix コア概要](../tensix-core/tensix_core_notes.md) / [Tensix 計算エンジン(LLK)](../tensix-compute/tensix_compute.html) / [TT スタック全体像](../tt-stack/tt_stack_notes.md)

---

## 1. Tensix コア内の 5 RISC-V — 役割一覧

| コア | HW Thread | カテゴリ | 役割 | NOC |
|------|-----------|---------|------|-----|
| **BRISC** | 0 | Data Movement | **Reader** — DRAM/L1 → CB への読み込み + マスター制御 | NOC 0 |
| **NCRISC** | 1 | Data Movement | **Writer** — CB → DRAM/L1 への書き出し + CB設定補助 | NOC 1 |
| **TRISC0** | 2 | Compute | **Unpack** — CB からタイルを解凍し SrcA/SrcB レジスタへ | — |
| **TRISC1** | 3 | Compute | **Math** — FPU(行列積) / SFPU(活性関数等) で演算 | — |
| **TRISC2** | 4 | Compute | **Pack** — DEST レジスタから結果をフォーマット変換し CB へ | — |

> **ソース**: `tt_metal/hw/inc/internal/hw_thread.h` (thread index),
> `tt_metal/api/tt-metalium/kernel_types.hpp:22-24` (RISCV_0=BRISC, RISCV_1=NCRISC)

### なぜ Data Movement が 2 コア必要か

```
DRAM ──NOC0──> [BRISC: read tiles] ──> CB_IN ──> TRISC(compute) ──> CB_OUT ──> [NCRISC: write tiles] ──NOC1──> DRAM
```

- **NOC が物理的に 2 本**ある → 読み書きを別 NOC で同時に流して**帯域を倍**にできる
- **パイプライン並列** — BRISC が次のタイルを読み込んでいる間に、NCRISC が前のタイルを書き出す
- **BRISC の追加責務** — firmware レベルでの初期化・同期管理（他コアへの GO 送信、完了待ち）

---

## 2. Circular Buffer (CB) — コア内スレッド間のデータ受け渡し

CB は Tensix コアの **L1 SRAM 上に確保される、タイル単位のリングバッファ**。
同一コア内の 5 つの RISC-V スレッド間でデータを安全に受け渡す。

```
BRISC (reader)                  TRISC0/1/2 (compute)            NCRISC (writer)
     |                               |                               |
     |-- noc_async_read -->  +------------------+                    |
     |                       |   CB_IN (L1)     |-> Unpack->Math->Pack ->
     |                       |  wr_ptr -------> |                    |
     |                       |  <------- rd_ptr |                    |
     |                       +------------------+                    |
     |                                            +------------------+
     |                                            |   CB_OUT (L1)    | -> noc_async_write
     |                                            |  wr_ptr -------> |    |
     |                                            |  <------- rd_ptr |    |
     |                                            +------------------+
```

### Producer-Consumer プロトコル

**Producer 側（BRISC が CB_IN に書く例）**:

```cpp
buff_in.reserve_back(1);      // wr_ptr の空きスロットを確保（満杯なら待つ）
noc.async_read(..., buff_in); // DRAM -> CB に DMA 転送
buff_in.push_back(1);         // wr_ptr を進める → "タイル1個書いたよ"
```

**Consumer 側（TRISC0 が CB_IN から読む例）**:

```cpp
buff_in.wait_front(1);        // rd_ptr にタイルが来るまで待つ
// ... unpack 処理 ...
buff_in.pop_front(1);         // rd_ptr を進める → "タイル1個消費したよ"
```

### ポイント

| 特性 | 説明 |
|------|------|
| **タイル単位** | 32x32 要素を 1 単位として rd_ptr / wr_ptr を管理 |
| **バックプレッシャー** | バッファ満杯なら producer が待ち、空なら consumer が待つ |
| **ダブルバッファリング** | CB を 2 タイル分確保すれば read と compute をオーバーラップ可能 |
| **ハードウェアカウンタ** | タイル数をHWが自動追跡し、暗黙的な同期を実現 |

> **ソース**: `tt_metal/hw/inc/internal/circular_buffer_interface.h` (LocalCBInterface),
> `tt_metal/kernels/dataflow/reader_unary.cpp`, `writer_unary.cpp`

---

## 3. 同期メカニズム — Subordinate Sync Map

5 コアの起動・完了は、L1 上の **mailbox 構造体**で管理される。

```
Host --> GO signal
           |
       +---v---+
       | BRISC |  (1) CB初期化
       +---+---+  (2) subordinate_sync->dm1 = RUN_SYNC_MSG_LOAD  --> NCRISC
           |      (3) subordinate_sync->trisc[0,1,2] = RUN_SYNC_MSG_GO  --> TRISCs
           |      (4) 自身の reader kernel 実行
           |      (5) 全コアの DONE 待ち
           |
   +-------+-------+-------+
   v       v       v       v
 NCRISC  TRISC0  TRISC1  TRISC2
  (CB設定  (Unpack) (Math)  (Pack)
   ロード)
   |       |       |       |
   +-- RUN_SYNC_MSG_DONE --+  --> BRISC が検知
```

### 同期シグナル定数

| 定数 | 値 | 意味 |
|------|----|------|
| `RUN_SYNC_MSG_INIT` | 0x40 | 初期化状態 |
| `RUN_SYNC_MSG_GO` | 0x80 | 実行開始 |
| `RUN_SYNC_MSG_DONE` | 0 | 完了 |
| `RUN_SYNC_MSG_LOAD` | 0x1 | CB設定ロード指示（NCRISC向け） |

> **ソース**: `tt_metal/hw/inc/hostdev/dev_msgs.h:98-109` (シグナル定数),
> `tt_metal/hw/firmware/src/tt-1xx/brisc.cc:354-597` (BRISC メインループ),
> `tt_metal/hw/firmware/src/tt-1xx/ncrisc.cc:77-91` (NCRISC 待機),
> `tt_metal/hw/firmware/src/tt-1xx/trisc.cc:73-75` (TRISC 待機)

---

## 4. TRISC の「1ソース → 3バイナリ」コンパイル方式

同じ compute kernel ソース（例: `bmm.cpp`）を**3回コンパイル**し、
条件マクロで各 TRISC に必要な部分だけを有効化する:

```cpp
// compute_kernel_api.h

#ifdef TRISC_UNPACK          // TRISC0 のみ有効
  #include "llk_unpack_common_api.h"
  #define UNPACK(...) __VA_ARGS__
#else
  #define UNPACK(...)
#endif

#ifdef TRISC_MATH             // TRISC1 のみ有効
  #include "llk_math_matmul_api.h"
  #define MATH(...) __VA_ARGS__
#else
  #define MATH(...)
#endif

#ifdef TRISC_PACK             // TRISC2 のみ有効
  #include "llk_io_pack.h"
  #define PACK(...) __VA_ARGS__
#else
  #define PACK(...)
#endif
```

つまり kernel 作者は `UNPACK(...)`, `MATH(...)`, `PACK(...)` マクロの中に処理を書くだけで、
コンパイラが自動的に 3 つの RISC-V バイナリに分離してくれる。

---

## 5. Metalium マッピング — `ttnn.matmul(A, B)` の全体像

TT-NN の 1 つの op がどうやって Tensix 上のカーネルになるかを、
matmul を例に tt-metal ソースから追跡した結果:

### レイヤー構成

```
+------------------------------------------------------------------------+
| Python: C = ttnn.matmul(A, B)                                          |
+------------------------------------+-----------------------------------+
                                     |
                                     v
+------------------------------------------------------------------------+
| TT-NN C++ layer (ttnn/operations/matmul/)                              |
| - テンソル形状からタイル分割、コア割り当てを決定                             |
| - ProgramFactory を呼び出し Program (= kernel群 + CB群) を生成            |
+------------------------------------+-----------------------------------+
                                     |
                                     v
+------------------------------------------------------------------------+
| TT-Metalium Program  (matmul_multicore_program_factory.cpp)            |
|                                                                        |
| CB定義:                                                                 |
|   CB_IN0 (2タイル, in0用)                                               |
|   CB_IN1 (2タイル, in1用)                                               |
|   CB_OUT=c_16 (2タイル, 出力用)                                          |
|                                                                        |
| Kernel 1 (Reader):                                                     |
|   reader_bmm_8bank_output_tiles_partitioned.cpp                        |
|   config = ReaderConfigDescriptor  --> BRISC (RISCV_0, NOC0)           |
|                                                                        |
| Kernel 2 (Writer):                                                     |
|   writer_unary_interleaved_start_id.cpp                                |
|   config = WriterConfigDescriptor  --> NCRISC (RISCV_1, NOC1)          |
|                                                                        |
| Kernel 3 (Compute):                                                    |
|   bmm.cpp                                                              |
|   config = ComputeConfigDescriptor --> TRISC0/1/2 (3回コンパイル)       |
+------------------------------------+-----------------------------------+
                                     | dispatch (各Tensixコアに配布)
                                     v
+------------------------------------------------------------------------+
|                      1つの Tensix コア                                   |
|                                                                        |
|  BRISC (reader)             NCRISC (writer)                            |
|  +----------------+         +----------------+                         |
|  | for each tile  |         | for each tile  |                         |
|  |  DRAM -> CB_IN0|         |  CB_OUT -> DRAM|                         |
|  |  DRAM -> CB_IN1|         |                |                         |
|  +-------+--------+         +--------^-------+                         |
|          | push_back                  | pop_front                      |
|          v                            |                                |
|  +------------------------------------------+                         |
|  |         CB_IN0 / CB_IN1 (L1)             |                         |
|  +--------------------+---------------------+                         |
|          wait_front    |                                               |
|                        v                                               |
|  TRISC0 (Unpack)    TRISC1 (Math)        TRISC2 (Pack)                |
|  +------------+     +-------------+      +-------------+              |
|  |CB->SrcA/B  | --> | 8x16 x 16x16| --> |DEST->CB_OUT |              |
|  |(decompress)|     | FPU matmul  |     | (reformat)  |              |
|  +------------+     +-------------+      +------+------+              |
|                                                  | push_back          |
|                                                  v                    |
|                                          +-------------+              |
|                                          |  CB_OUT (L1) |              |
|                                          +-------------+              |
+------------------------------------------------------------------------+
```

### Config → コア配置の対応

| Config | 配置先 | NOC | 典型カーネル |
|--------|--------|-----|------------|
| `ReaderConfigDescriptor` | BRISC (RISCV_0) | NOC 0 | `reader_bmm_*.cpp` |
| `WriterConfigDescriptor` | NCRISC (RISCV_1) | NOC 1 | `writer_unary_*.cpp` |
| `ComputeConfigDescriptor` | TRISC0/1/2 | — | `bmm.cpp`, `eltwise_binary.cpp` |

### ProgramFactory の中身（抜粋）

`matmul_multicore_program_factory.cpp` では以下を生成:

1. **CB 3 本を定義**（各 2 タイル = ダブルバッファリング）
2. **Reader kernel** を `ReaderConfigDescriptor` で登録 → 自動的に BRISC へ
3. **Writer kernel** を `WriterConfigDescriptor` で登録 → 自動的に NCRISC へ
4. **Compute kernel** (`bmm.cpp`) を `ComputeConfigDescriptor` で登録 → TRISC0/1/2 へ
5. コアごとの **runtime args**（担当タイル範囲）をセット

> **ソース**: `ttnn/cpp/ttnn/operations/matmul/device/factory/matmul_multicore_program_factory.cpp`

---

## 6. Matrix Engine のスペック

Tensix の FPU（行列エンジン）の 1 サイクルあたりの処理量:

| 演算 | 1サイクルの処理サイズ | @1GHz スループット |
|------|----------------------|-------------------|
| **matmul** | 8x16 * 16x16 = 8x16 | 4 TFLOPS (LoFi) |
| **reduction** (max/avg/sum) | 16x16 | 0.512 TFLOPS |
| **eltwise** (add/sub/mul) | 8x16 | 0.128 TFLOPS |

Math Fidelity で精度とスループットのトレードオフ:
- **LoFi** = 1 パス（最速）, **HiFi4** = 4 パス（最高精度、1/4 速度）

> **ソース**: `tech_reports/matrix_engine/matrix_engine.md`

---

## 7. 主要ソースファイル一覧

| コンポーネント | パス | 内容 |
|--------------|------|------|
| BRISC firmware | `hw/firmware/src/tt-1xx/brisc.cc` | メインループ、同期管理 |
| NCRISC firmware | `hw/firmware/src/tt-1xx/ncrisc.cc` | GO待ち、CB設定ロード |
| TRISC firmware | `hw/firmware/src/tt-1xx/trisc.cc` | GO待ち、kernel_main()実行 |
| 同期シグナル | `hw/inc/hostdev/dev_msgs.h` | mailbox構造体、sync定数 |
| CB interface | `hw/inc/internal/circular_buffer_interface.h` | LocalCBInterface |
| thread mapping | `hw/inc/internal/hw_thread.h` | HW thread index |
| kernel types | `api/tt-metalium/kernel_types.hpp` | DataMovementProcessor enum |
| compute API | `hw/inc/api/compute/compute_kernel_api.h` | UNPACK/MATH/PACK マクロ |
| matmul ProgramFactory | `ttnn/.../matmul/device/factory/matmul_multicore_program_factory.cpp` | 3 kernel + 3 CB 生成 |
| reader kernel例 | `tt_metal/kernels/dataflow/reader_unary.cpp` | NOC read + CB push |
| writer kernel例 | `tt_metal/kernels/dataflow/writer_unary.cpp` | CB pop + NOC write |

---

## 関連ノート

- [Tensix コア概要（ブロック図）](../tensix-core/tensix_core_notes.md) — 各ブロックの概要と起動フロー
- [Tensix 計算エンジン(LLK)](../tensix-compute/tensix_compute.html) — Unpack/FPU/SFPU/Pack の詳細
- [TT スタック全体像(ttsim)](../tt-stack/tt_stack_notes.md) — TT-NN→Metalium→LLK→ttsim の縦構造
- [統合マップ: Llama⇄SW⇄HW](../tt-integration/tt_integration.html) — op→kernel→HWユニットの3列連動図
- [Llama 1層 x Tensix](../llama-on-tensix/llama_on_tensix.html) — 各 op が Tensix のどのユニットで動くか

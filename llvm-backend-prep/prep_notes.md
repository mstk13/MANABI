# RISC-V + LLVM バックエンド自作 — 読む前に押さえる前提知識

この本は「LLVM バックエンドを自分で書いて、C コードを RISC-V 機械語に変換できるようにする」本。
各章をスムーズに読み・実装するために、章ごとに **"これを先に理解しておくと詰まらない"** ポイントをまとめる。

> 既習: [ISA基礎](../riscv-isa/isa_notes.md) / [コンパイラ基礎](../compiler/compiler_notes.md) / [パイプライン](../cpu-pipeline/pipeline_notes.md)
> 実験環境: [Practice](../Practice/README.md)（GCC/Clang で RISC-V をコンパイル・比較済み）

---

## 全体の地図 — この本で何を作るのか

```
C ソース
  ↓  Clang (フロントエンド)
LLVM IR  ← 言語に依存しない中間表現
  ↓  ★ ここを自作する ★  (llc = LLVM バックエンド)
  ↓  命令選択 → レジスタ割当 → 命令スケジューリング → アセンブリ出力
RISC-V アセンブリ (.s)
  ↓  アセンブラ (llvm-mc)
オブジェクトファイル (.o / ELF)
```

**自作するのは「LLVM IR → RISC-V マシンコード」の変換パイプライン全体**。
本書では `MYRISCVX` という独自ターゲット名で LLVM に追加していく。

---

## 第1章: コンピュータアーキテクチャと ISA の基礎知識

### この章で話されること
- コンピュータの全体構成（CPU, メモリ, I/O）
- ISA の役割と分類（CISC vs RISC）
- CPU 高速化技法（パイプライン、スーパースカラ、アウトオブオーダ、キャッシュ）

### 前提知識（押さえておくこと）

#### 1-1. フォン・ノイマン・アーキテクチャ

```
┌─────────────────────────────────┐
│            CPU                  │
│  ┌──────┐  ┌──────────────────┐ │
│  │  PC  │  │  レジスタファイル │ │
│  └──┬───┘  │  x0〜x31 (32本)  │ │
│     │      └──────────────────┘ │
│  ┌──▼───┐  ┌──────────────────┐ │
│  │Fetch │→│ Decode → Execute  │ │
│  └──────┘  └──────────────────┘ │
└────────┬────────────────────────┘
         │ ロード/ストア
    ┌────▼────┐
    │ メモリ   │  命令もデータも同じメモリに置く
    │(DRAM等) │  ← これがフォン・ノイマン方式
    └─────────┘
```

- **プログラムカウンタ(PC)**: 次に実行する命令のアドレスを保持
- **フェッチ→デコード→実行**: この繰り返しが CPU の動作の本質
- **ストアドプログラム方式**: 命令自体もメモリ上のデータ。これにより「プログラムを書き換え可能」

#### 1-2. CISC vs RISC — なぜ RISC-V か

| 観点 | CISC (x86) | RISC (RISC-V, ARM) |
|------|-----------|-------------------|
| 命令長 | 可変長 (1〜15バイト) | 固定長 (32bit) |
| 命令の複雑さ | 1命令で複雑な処理 | 1命令は単純な処理 |
| メモリアクセス | 演算命令が直接メモリ操作可 | ロード/ストア分離 |
| デコード | 複雑(→トランジスタ大) | 単純(→パイプライン化容易) |
| レジスタ数 | 少ない(x86: 16本) | 多い(RISC-V: 32本) |

**コンパイラバックエンド視点での重要ポイント**:
- RISC は命令が単純・規則的 → **命令選択(ISel)の規則を書きやすい**
- 固定長命令 → **エンコーディング処理が定型的**
- ロード/ストア分離 → **メモリオペランドの扱いが明快**

#### 1-3. パイプラインと高速化（実装時に効く知識）

パイプラインの各段:
```
IF(命令フェッチ) → ID(デコード) → EX(実行) → MEM(メモリ) → WB(書き戻し)
```

**バックエンド開発で意識が必要になる場面**:
- **データハザード**: レジスタの依存関係 → 命令スケジューリングで回避（第4章以降）
- **分岐ペナルティ**: 条件分岐の予測ミス → branchless 変換（第6章）
- **命令レイテンシ**: 乗算は加算より遅い → スケジューリングの優先度（発展）

> 既に [pipeline_notes](../cpu-pipeline/pipeline_notes.md) で学習済み。復習として、
> 「なぜ命令の順番を変える（スケジューリング）と速くなるか」を説明できればOK。

---

## 第2章: RISC-V の基礎知識

### この章で話されること
- RV32I 命令セットの全貌
- 各命令フォーマット（R/I/S/B/U/J型）の詳細
- RISC-V シミュレータでの実行体験

### 前提知識（押さえておくこと）

#### 2-1. RV32I 命令一覧 — バックエンド実装で使うもの

第5〜6章で自分のバックエンドに実装する命令を先に把握しておくと見通しが良い:

**算術・論理（R型）**:
```
add  rd, rs1, rs2    # rd = rs1 + rs2
sub  rd, rs1, rs2    # rd = rs1 - rs2
and  rd, rs1, rs2    # ビットAND
or   rd, rs1, rs2    # ビットOR
xor  rd, rs1, rs2    # ビットXOR
sll  rd, rs1, rs2    # 左シフト
srl  rd, rs1, rs2    # 論理右シフト
sra  rd, rs1, rs2    # 算術右シフト
slt  rd, rs1, rs2    # rs1 < rs2 なら 1（符号付き比較）
sltu rd, rs1, rs2    # 同上（符号なし）
```

**即値演算（I型）**:
```
addi  rd, rs1, imm   # rd = rs1 + imm (12bit符号拡張)
andi  rd, rs1, imm
ori   rd, rs1, imm
xori  rd, rs1, imm
slti  rd, rs1, imm
sltiu rd, rs1, imm
```

**メモリアクセス（I型/S型）**:
```
lw   rd, offset(rs1)  # Load Word: rd = M[rs1 + offset]
sw   rs2, offset(rs1) # Store Word: M[rs1 + offset] = rs2
lb/lh/lbu/lhu         # バイト/ハーフワードのロード
sb/sh                 # バイト/ハーフワードのストア
```

**分岐（B型）**:
```
beq  rs1, rs2, label  # rs1 == rs2 なら分岐
bne  rs1, rs2, label  # rs1 != rs2 なら分岐
blt/bge/bltu/bgeu     # 大小比較分岐
```

**ジャンプ（J型/I型）**:
```
jal   rd, label       # PC相対ジャンプ、rd に戻りアドレス保存
jalr  rd, rs1, imm    # レジスタ間接ジャンプ（関数呼び出し/戻り）
```

**上位即値（U型）**:
```
lui   rd, imm         # rd = imm << 12 (上位20bitセット)
auipc rd, imm         # rd = PC + (imm << 12)
```

#### 2-2. 命令フォーマットのビット配置（エンコーディング実装の鍵）

バックエンド開発では **命令をビット列にエンコード** する必要がある。
各フォーマットのビット配置を覚えておくこと:

```
R型: [funct7(7)] [rs2(5)] [rs1(5)] [funct3(3)] [rd(5)]  [opcode(7)]
I型: [    imm[11:0](12)  ] [rs1(5)] [funct3(3)] [rd(5)]  [opcode(7)]
S型: [imm[11:5](7)][rs2(5)] [rs1(5)] [funct3(3)] [imm[4:0](5)] [opcode(7)]
B型: [imm分割(7)] [rs2(5)] [rs1(5)] [funct3(3)] [imm分割(5)] [opcode(7)]
U型: [         imm[31:12](20)                  ] [rd(5)]  [opcode(7)]
J型: [         imm分割(20)                     ] [rd(5)]  [opcode(7)]
```

**実装上の注意**:
- B型/J型は即値ビットが**シャッフル**されている（配線を揃えるため）
- S型の即値は rd の位置と funct7 の位置に**分割格納**される
- これらは第4章で TableGen(td ファイル)に記述する

#### 2-3. レジスタの ABI 名と用途（呼び出し規約の基礎）

第5章「関数の仕組み」で必須になる知識:

| レジスタ | ABI名 | 用途 | Caller/Callee保存 |
|---------|-------|------|-------------------|
| x0 | zero | 常にゼロ | — |
| x1 | ra | 戻りアドレス | Caller |
| x2 | sp | スタックポインタ | Callee |
| x3 | gp | グローバルポインタ | — |
| x8 | s0/fp | フレームポインタ/保存レジスタ | Callee |
| x10-x11 | a0-a1 | 引数/戻り値 | Caller |
| x12-x17 | a2-a7 | 引数 | Caller |
| x8-x9, x18-x27 | s0-s11 | 保存レジスタ | Callee |
| x5-x7, x28-x31 | t0-t6 | 一時レジスタ | Caller |

**Caller保存 vs Callee保存**:
- **Caller保存**: 関数を呼ぶ側が「呼ぶ前に退避」。呼ばれた側は自由に壊せる
- **Callee保存**: 呼ばれた側が「使う前に退避、戻る前に復元」する義務
- バックエンド実装では **プロローグ/エピローグ** でこの退避・復元コードを生成する

#### 2-4. シミュレータ環境セットアップ

本書で使う可能性があるツール:
```bash
# QEMU (ユーザモード) — Practice環境で導入済み
qemu-riscv32 ./a.out

# Spike (RISC-V公式シミュレータ) + pk (proxy kernel)
spike pk ./a.out
```

> Practice 環境に qemu-user は導入済み。Spike が必要になったらその時に入れる。

---

## 第3章: LLVM の基礎知識

### この章で話されること
- LLVM の全体アーキテクチャ
- LLVM IR の文法と意味
- clang / llc / opt などのツールチェーン体験

### 前提知識（押さえておくこと）

#### 3-1. LLVM の3層アーキテクチャ（最重要）

```
┌──────────────────────────────────────────────────┐
│  フロントエンド (Clang, rustc, etc.)              │
│  C/C++/Rust → LLVM IR に変換                     │
└──────────────────┬───────────────────────────────┘
                   ↓
┌──────────────────▼───────────────────────────────┐
│  ミドルエンド (opt)                               │
│  LLVM IR → LLVM IR の最適化パス群                 │
│  (定数畳み込み, ループ展開, インライン化 ...)       │
└──────────────────┬───────────────────────────────┘
                   ↓
┌──────────────────▼───────────────────────────────┐
│  バックエンド (llc)   ← ★ ここを自作 ★           │
│  LLVM IR → ターゲット固有のマシンコード            │
│                                                   │
│  SelectionDAG(命令選択) → MachineInstr             │
│  → レジスタ割当 → 命令スケジューリング             │
│  → AsmPrinter(アセンブリ出力)                     │
│  → MCLayer(オブジェクトファイル出力)               │
└──────────────────────────────────────────────────┘
```

**ポイント**: フロントエンドとミドルエンドは既存のものをそのまま使う。
自作するのはバックエンド部分のみ。これが LLVM の「モジュラー設計」の強み。

#### 3-2. LLVM IR — バックエンドへの「入力」を理解する

LLVM IR は **SSA (Static Single Assignment)** 形式の中間表現。
バックエンドの入力なので、これを読めないと何も始まらない。

**SSA とは**: 各変数は **一度だけ代入** される。更新の代わりに新しい変数を作る。

```llvm
; C: int add(int a, int b) { return a + b; }

define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b       ; %result は一度だけ定義
  ret i32 %result
}
```

**IR の基本要素**:

| 要素 | 説明 | 例 |
|------|------|-----|
| `i32`, `i64` | 整数型 (ビット幅指定) | `i32 %x` |
| `%name` | ローカル変数 (SSA値) | `%result = add i32 %a, %b` |
| `@name` | グローバル (関数/変数) | `@global_var = global i32 0` |
| `define` | 関数定義 | `define i32 @func(i32 %a)` |
| `entry:` | 基本ブロックのラベル | `entry:`, `if.then:` |
| `add`, `sub`, `mul` | 算術命令 | `%c = add i32 %a, %b` |
| `load`, `store` | メモリアクセス | `%v = load i32, ptr %p` |
| `br` | 分岐 | `br i1 %cond, label %T, label %F` |
| `ret` | 関数リターン | `ret i32 %result` |
| `icmp` | 整数比較 | `%c = icmp eq i32 %a, %b` |
| `phi` | SSA の合流点 | `%x = phi i32 [%a, %bb1], [%b, %bb2]` |
| `getelementptr` (GEP) | アドレス計算 | 配列/構造体のオフセット |
| `call` | 関数呼び出し | `%r = call i32 @func(i32 %a)` |
| `alloca` | スタック確保 | `%p = alloca i32` |

**phi ノード（重要）**:
```llvm
; C: x = cond ? a : b;
if.end:
  %x = phi i32 [ %a, %if.then ], [ %b, %if.else ]
  ; → %if.then から来たら %a、%if.else から来たら %b を選ぶ
```
SSA では変数を再代入できないため、分岐の合流点で「どちらの値を使うか」を phi で表現する。
バックエンド（命令選択）で phi は **レジスタコピー + 分岐** に変換される。

#### 3-3. LLVM ツールチェーン — 実際のコマンド

```bash
# C → LLVM IR (人間が読める形式)
clang -S -emit-llvm -O0 test.c -o test.ll

# LLVM IR → アセンブリ (バックエンド = llc)
llc -march=riscv32 test.ll -o test.s

# LLVM IR → 最適化 LLVM IR
opt -O2 test.ll -S -o test_opt.ll

# LLVM IR のビットコード形式 (バイナリ)
clang -c -emit-llvm test.c -o test.bc
llvm-dis test.bc -o test.ll    # bc → ll (逆変換)

# アセンブリ → オブジェクトファイル
llvm-mc -filetype=obj -triple=riscv32 test.s -o test.o

# オブジェクトファイルの中身を見る
llvm-objdump -d test.o
llvm-readelf -a test.o
```

**覚えておくべき llc のオプション**:
```bash
llc -march=myriscvx      # ターゲット指定 (自作ターゲット名)
llc -view-isel-dags       # 命令選択前の DAG を可視化
llc -view-sched-dags      # スケジューリング後の DAG を可視化
llc -debug                # デバッグ出力 (何が起きてるか全部見える)
llc -print-after-all      # 各パスの結果を表示
```

#### 3-4. C++ の前提知識（LLVM 開発に必要な最小限）

LLVM は C++ で書かれている。以下の機能を使えること:

```cpp
// 1. 継承とオーバーライド (LLVM のクラス階層は深い)
class MYRISCVXInstrInfo : public TargetInstrInfo {
  void copyPhysReg(...) override;  // 仮想関数のオーバーライド
};

// 2. テンプレート (LLVM は多用する)
template <typename T>
class SmallVector;  // llvm::SmallVector<int, 8> のように使う

// 3. RTTI の代替 — LLVM 独自のキャスト
if (auto *CI = dyn_cast<ConstantInt>(V)) { ... }
// dyn_cast: 型チェック + キャスト (失敗で nullptr)
// isa<T>(V): 型チェックだけ (bool)
// cast<T>(V): 確実にその型のときだけ使う (失敗で abort)

// 4. StringRef, ArrayRef — 所有権を持たない参照
void foo(StringRef Name);  // const std::string& の軽量版

// 5. スマートポインタ
std::unique_ptr<Module> M;
```

**LLVM 固有のイディオム**:
- `llvm::errs()` — stderr への出力 (デバッグ用)
- `llvm_unreachable("msg")` — 到達不能コードのマーク
- `LLVM_DEBUG(dbgs() << "info\n")` — `-debug` 時のみ出力
- `cl::opt<bool>` — コマンドラインオプション定義

#### 3-5. CMake の基礎（LLVM のビルドシステム）

```cmake
# LLVM のビルド
cmake -G Ninja \
  -DLLVM_TARGETS_TO_BUILD="X86;RISCV;MYRISCVX" \  # 自作ターゲットを追加
  -DCMAKE_BUILD_TYPE=Debug \                        # デバッグビルド
  -DLLVM_ENABLE_PROJECTS="clang" \
  ../llvm

ninja llc    # llc だけビルド (全体ビルドより速い)
ninja clang  # clang もビルド
```

**重要**: LLVM のフルビルドは **数十分〜数時間** かかる。
- `Debug` ビルドは遅いが GDB/LLDB でデバッグ可能
- `Release` は速いがデバッグ困難
- **`ninja llc` で llc だけビルドする** のが開発時の常套手段

---

## 第4章: LLVM バックエンドの仕組み

### この章で話されること
- バックエンド開発で作るファイル群の全体像
- TableGen (td ファイル) によるターゲット記述
- C++ クラス群の実装
- LLVM のマルチターゲット機構

### 前提知識（押さえておくこと）

#### 4-1. バックエンドの処理フロー（全体像）

```
LLVM IR
  ↓  (1) DAG の構築
SelectionDAG  ← IR の各命令をノードに変換した有向非巡回グラフ
  ↓  (2) 命令選択 (ISel) ← ★核心: IR ノード → ターゲット命令に変換
MachineDAG    ← ターゲット固有の命令ノード
  ↓  (3) スケジューリング + レジスタ割当
MachineInstr  ← 最終的な命令列
  ↓  (4) AsmPrinter / MCLayer
アセンブリ (.s) or オブジェクト (.o)
```

#### 4-2. SelectionDAG と命令選択（ISel）

**SelectionDAG** は LLVM IR を **DAG（有向非巡回グラフ）** に変換したもの。

```
例: a = b + c
          
    [ADD]
    /   \
  [b]   [c]     ← これが SelectionDAG のノード
```

**命令選択 (ISel)** は「この DAG パターンをどの RISC-V 命令に対応させるか」を決める:
```
ISD::ADD  →  MYRISCVX::ADD  (add rd, rs1, rs2)
```

これを **TableGen の td ファイル** に **パターンマッチ** として書く:
```tablegen
def ADD : Instruction<(outs GPR:$rd), (ins GPR:$rs1, GPR:$rs2),
                       "add $rd, $rs1, $rs2",
                       [(set GPR:$rd, (add GPR:$rs1, GPR:$rs2))]>;
// [(set ...)] の部分がパターン。
// ISD::add ノードを見つけたら、この命令を生成する。
```

#### 4-3. TableGen (td ファイル) — LLVM 独自の DSL

**TableGen** は LLVM 独自の記述言語で、以下を宣言的に定義する:
- 命令の定義（オペコード、オペランド、アセンブリ表記、エンコーディング）
- レジスタの定義（名前、番号、クラス）
- 命令選択パターン
- 呼び出し規約

```tablegen
// クラス定義 (テンプレートのようなもの)
class RVInst<dag outs, dag ins, string asmstr, list<dag> pattern>
  : Instruction {
  let OutOperandList = outs;
  let InOperandList = ins;
  let AsmString = asmstr;
  let Pattern = pattern;
}

// レコード定義 (インスタンス)
def ADD : RVInst<(outs GPR:$rd), (ins GPR:$rs1, GPR:$rs2),
                  "add\t$rd, $rs1, $rs2",
                  [(set GPR:$rd, (add GPR:$rs1, GPR:$rs2))]>;
```

**TableGen の出力**: `llvm-tblgen` コマンドで C++ のヘッダ/ソースに変換される。
ビルド時に自動実行されるが、手動で確認もできる:
```bash
llvm-tblgen -gen-instr-info MYRISCVX.td    # 命令情報
llvm-tblgen -gen-register-info MYRISCVX.td  # レジスタ情報
llvm-tblgen -gen-dag-isel MYRISCVX.td       # ISel パターンマッチャ
```

#### 4-4. 作成するファイル群（ディレクトリ構成）

```
llvm/lib/Target/MYRISCVX/
├── CMakeLists.txt              # ビルド設定
├── MYRISCVX.td                 # メイン td (他をinclude)
├── MYRISCVXRegisterInfo.td     # レジスタ定義
├── MYRISCVXInstrInfo.td        # 命令定義 + ISelパターン
├── MYRISCVXInstrFormats.td     # 命令フォーマット (R型/I型...)
├── MYRISCVXCallingConv.td      # 呼び出し規約
├── MYRISCVXSchedule.td         # スケジューリング情報
│
├── MYRISCVXTargetMachine.cpp/h # ターゲットマシン (エントリポイント)
├── MYRISCVXSubtarget.cpp/h     # サブターゲット (CPU機能フラグ)
├── MYRISCVXInstrInfo.cpp/h     # 命令操作 (copyPhysReg等)
├── MYRISCVXRegisterInfo.cpp/h  # レジスタ操作 (eliminateFrameIndex等)
├── MYRISCVXISelDAGToDAG.cpp    # DAGベース命令選択
├── MYRISCVXISelLowering.cpp/h  # IR→DAG の変換規則
├── MYRISCVXFrameLowering.cpp/h # スタックフレーム管理
├── MYRISCVXAsmPrinter.cpp      # MachineInstr → アセンブリ文字列
├── MYRISCVXMCInstLower.cpp/h   # MachineInstr → MCInst 変換
└── MCTargetDesc/               # MC層 (エンコーディング等)
    ├── MYRISCVXMCTargetDesc.cpp
    ├── MYRISCVXMCAsmInfo.cpp
    └── MYRISCVXInstPrinter.cpp
```

#### 4-5. LLVM のマルチターゲット登録メカニズム

```cpp
// ターゲットの登録 (MYRISCVXTargetMachine.cpp)
extern "C" void LLVMInitializeMYRISCVXTarget() {
  RegisterTargetMachine<MYRISCVXTargetMachine> X(getTheMYRISCVXTarget());
}

// Target.td でターゲット定義
def MYRISCVX : Target {
  let InstructionSet = MYRISCVXInstrInfo;
}
```

**ポイント**: LLVM は `Target` をプラグイン的に登録する仕組み。
`llc -march=myriscvx` で呼ばれると、登録された `MYRISCVXTargetMachine` が使われる。

---

## 第5章: 簡単な関数や演算のサポート

### この章で話されること
- 関数呼び出し規約 (Calling Convention)
- シンプルな関数のコンパイル
- 戻り値の実装
- プロローグ/エピローグの実装

### 前提知識（押さえておくこと）

#### 5-1. スタックフレームの構造（最重要）

関数呼び出し時のメモリレイアウト:

```
高アドレス
┌─────────────────────┐
│  呼び出し元のフレーム  │
├─────────────────────┤ ← 関数呼び出し前の sp
│  引数 (a0-a7超過分)   │  ← 引数がレジスタに入り切らない分
├─────────────────────┤
│  戻りアドレス (ra)    │  ← callee保存: プロローグで退避
├─────────────────────┤
│  保存レジスタ (s0-s11)│  ← callee保存: 使うものだけ退避
├─────────────────────┤
│  ローカル変数          │  ← alloca / 自動変数
├─────────────────────┤ ← sp (スタックポインタ)
│  (次の呼び出し用)     │
低アドレス
```

#### 5-2. プロローグとエピローグ

**プロローグ** (関数の先頭で自動生成):
```asm
  addi sp, sp, -16      # スタックを確保 (16バイト分)
  sw   ra, 12(sp)       # 戻りアドレスを退避
  sw   s0, 8(sp)        # フレームポインタを退避
  addi s0, sp, 16       # 新しいフレームポインタ設定
```

**エピローグ** (関数の末尾で自動生成):
```asm
  lw   s0, 8(sp)        # フレームポインタを復元
  lw   ra, 12(sp)       # 戻りアドレスを復元
  addi sp, sp, 16       # スタックを解放
  jalr zero, ra, 0      # リターン (= ret)
```

バックエンドでは `MYRISCVXFrameLowering::emitPrologue/emitEpilogue` に実装する。

#### 5-3. 呼び出し規約の実装 (TableGen)

```tablegen
// 戻り値: a0 (i32), a0+a1 (i64)
def RetCC_MYRISCVX : CallingConv<[
  CCIfType<[i32], CCAssignToReg<[A0, A1]>>
]>;

// 引数: a0-a7 の8本、溢れたらスタック
def CC_MYRISCVX : CallingConv<[
  CCIfType<[i32], CCAssignToReg<[A0, A1, A2, A3, A4, A5, A6, A7]>>,
  CCIfType<[i32], CCAssignToStack<4, 4>>  // 4バイト, 4バイトアラインメント
]>;
```

#### 5-4. DAG で関数呼び出しを表す

LLVM IR の `call` が SelectionDAG でどう表現されるか:

```
MYRISCVXISD::CALL  ← カスタムSDノード
  → 引数をレジスタ/スタックに配置 (CopyToReg)
  → JAL/JALR 命令を発行
  → 戻り値を取得 (CopyFromReg a0)
```

`ISelLowering.cpp` の `LowerCall`, `LowerReturn`, `LowerFormalArguments` で実装。

---

## 第6章: 算術演算・グローバル変数・ポインタ・制御構文のサポート

### この章で話されること
- 算術・論理・比較命令の追加
- グローバル変数アクセス
- ポインタ/配列/構造体
- 条件分岐・ループ
- 関数呼び出し
- 画像パターンマッチング/ソートの実装演習

### 前提知識（押さえておくこと）

#### 6-1. 即値の扱い — 32bit 定数をどう作るか

RISC-V の即値フィールドは 12bit (I型) または 20bit (U型)。
32bit の定数をレジスタにロードするには **2命令必要**:

```asm
# 0x12345678 をレジスタに入れたい
lui  t0, 0x12345        # 上位20bit: t0 = 0x12345000
addi t0, t0, 0x678      # 下位12bit: t0 = 0x12345678
```

**注意: 符号拡張の罠**:
`addi` は即値を**符号拡張**する。下位12bitの最上位が1の場合、`lui` の値を +1 補正する必要がある:
```asm
# 0x12345800 をロードしたい (下位12bit = 0x800, 最上位ビット=1)
lui  t0, 0x12346        # +1 補正! (0x12345 + 1)
addi t0, t0, -2048      # 0x800 は符号拡張で -2048
# 0x12346000 + (-2048) = 0x12345800 ✓
```

バックエンドでは `MYRISCVXISelLowering` でこの変換を実装する。

#### 6-2. グローバル変数のアドレッシング

グローバル変数のアドレスは **リンク時** に決まる。コンパイル時には分からない。

**対処法: lui + addi で2段階ロード**:
```asm
# int g = 42; の g にアクセス
lui  t0, %hi(g)         # g のアドレス上位20bit
addi t0, t0, %lo(g)     # g のアドレス下位12bit
lw   a0, 0(t0)          # メモリから値をロード
```

`%hi()`, `%lo()` は **リロケーション** — リンカが実アドレスに置き換える。
バックエンドでは `LowerGlobalAddress` で `MYRISCVXISD::Hi` / `MYRISCVXISD::Lo` ノードを生成。

#### 6-3. GEP (GetElementPtr) — 配列/構造体のアドレス計算

```c
int arr[10];
int x = arr[3];  // → arr のベースアドレス + 3 * 4(sizeof(int))
```

LLVM IR:
```llvm
%ptr = getelementptr [10 x i32], ptr @arr, i32 0, i32 3
%x = load i32, ptr %ptr
```

GEP は **アドレス計算だけ** で、メモリアクセスはしない。
バックエンドでは `add` + `slli`（シフト = ×4）+ `lw` に変換される。

構造体の場合:
```c
struct S { int a; int b; };  // b のオフセット = 4
struct S s;
int y = s.b;  // → &s + 4
```

#### 6-4. 条件分岐の SelectionDAG 表現

```c
if (a > b) { x = 1; } else { x = 2; }
```

```
          [BR_CC]  ← 条件分岐ノード
         /   |   \
      [GT] [a] [b]  → 条件と比較対象
       |         |
   [BB_then]  [BB_else]  → 分岐先の基本ブロック
```

`ISelLowering` で `BR_CC` → `MYRISCVXISD::BRCOND` に lowering し、
td ファイルで `blt`, `bge`, `beq`, `bne` 等にパターンマッチさせる。

#### 6-5. ループの変換

```c
for (int i = 0; i < n; i++) { ... }
```

LLVM IR では **ループは単なる基本ブロック間の分岐**:
```
entry:           → for.cond へジャンプ
for.cond:        → i < n を比較、真なら for.body、偽なら for.end
for.body:        → 本体実行後 for.inc へ
for.inc:         → i++ して for.cond へ戻る (後方分岐)
for.end:         → ループ後の処理
```

バックエンドから見ると、ループは「後方への条件分岐」に過ぎない。
分岐命令の実装ができていればループは自然に動く。

---

## 第7章: オブジェクトファイル・ELF ファイル出力のサポート

### この章で話されること
- オブジェクトファイル (ELF) の構造
- インラインアセンブリ
- llvm-mc の実装
- N-Queen 問題の実装演習

### 前提知識（押さえておくこと）

#### 7-1. ELF ファイルの構造

```
┌──────────────────┐
│    ELF ヘッダ     │  マジックナンバー, アーキテクチャ, エントリポイント
├──────────────────┤
│ プログラムヘッダ表 │  実行時のセグメント情報 (ローダ用)
├──────────────────┤
│   .text セクション │  ← 機械語命令 (実行可能)
├──────────────────┤
│   .data セクション │  ← 初期化済みグローバル変数
├──────────────────┤
│   .bss セクション  │  ← 未初期化グローバル変数 (ファイル上はサイズ0)
├──────────────────┤
│   .rodata         │  ← 定数データ (文字列リテラル等)
├──────────────────┤
│  .symtab          │  ← シンボルテーブル (関数名→アドレス)
├──────────────────┤
│  .rel.text        │  ← リロケーション情報 (%hi/%lo の解決用)
├──────────────────┤
│ セクションヘッダ表 │  各セクションのメタ情報
└──────────────────┘
```

#### 7-2. リロケーション — なぜ必要か

コンパイル時に分からないアドレス（グローバル変数、外部関数）を、
**リンク時に埋める** 仕組み:

```
コンパイル時: lui t0, 0          ← アドレス未定、0で仮置き
              + リロケーションエントリ: R_RISCV_HI20, symbol="g"

リンク時:     lui t0, 0x12345    ← リンカが実アドレスの上位20bitを埋める
```

RISC-V 固有のリロケーションタイプ:
- `R_RISCV_HI20` — `%hi()` の解決 (lui 用)
- `R_RISCV_LO12_I` — `%lo()` の解決 (addi/load 用, I型)
- `R_RISCV_LO12_S` — `%lo()` の解決 (store 用, S型)
- `R_RISCV_BRANCH` — 分岐オフセット
- `R_RISCV_JAL` — JAL のオフセット

#### 7-3. MC 層 — LLVM のオブジェクトファイル出力

```
MachineInstr (バックエンド内部表現)
  ↓  MYRISCVXMCInstLower
MCInst (MC 層の命令表現 — ターゲット非依存のフレームワーク)
  ↓  MCCodeEmitter (エンコーディング)
バイト列 (機械語)
  ↓  MCObjectStreamer
ELF ファイル
```

**MCInst** は「オペコード + オペランドのリスト」という非常にシンプルな表現。
エンコーディングは td ファイルの `Inst` フィールドから自動生成される部分が多い。

#### 7-4. インラインアセンブリ

```c
int result;
asm volatile("add %0, %1, %2" : "=r"(result) : "r"(a), "r"(b));
//            ↑命令文字列       ↑出力          ↑入力
// =r: レジスタに出力  r: レジスタ入力
```

LLVM での処理:
1. フロントエンド (Clang) が `INLINEASM` ノードを生成
2. バックエンドは制約 (`r`, `m` 等) に従いレジスタ/メモリを割り当て
3. アセンブリ文字列のプレースホルダ (`$0`, `$1`) を実レジスタ名に置換

#### 7-5. readelf / objdump での確認方法

```bash
# ELF ヘッダの確認
llvm-readelf -h test.o

# セクション一覧
llvm-readelf -S test.o

# シンボルテーブル
llvm-readelf -s test.o

# リロケーション
llvm-readelf -r test.o

# 逆アセンブル
llvm-objdump -d test.o

# すべてのセクションの中身 (16進ダンプ)
llvm-readelf -x .text test.o
```

---

## 第8章: LLVM でのテスト記述とリグレッション

### この章で話されること
- `llvm-lit` によるテスト実行
- FileCheck によるパターンマッチテスト
- リグレッションテストの書き方

### 前提知識（押さえておくこと）

#### 8-1. llvm-lit — LLVM のテストフレームワーク

```bash
# テスト実行
llvm-lit test/CodeGen/MYRISCVX/        # ディレクトリ指定
llvm-lit test/CodeGen/MYRISCVX/add.ll  # ファイル指定
llvm-lit -v test/...                   # 詳細出力
```

#### 8-2. FileCheck — 出力のパターンマッチ

テストファイルの書き方:
```llvm
; RUN: llc -march=myriscvx < %s | FileCheck %s

; 単純な加算のテスト
define i32 @test_add(i32 %a, i32 %b) {
  %c = add i32 %a, %b
  ret i32 %c
}

; CHECK-LABEL: test_add:
; CHECK:       add a0, a0, a1
; CHECK-NEXT:  ret
```

**FileCheck のディレクティブ**:

| ディレクティブ | 意味 |
|--------------|------|
| `CHECK:` | この行がどこかに存在する |
| `CHECK-NEXT:` | 直前の CHECK の次の行にある |
| `CHECK-NOT:` | この行が存在しないことを確認 |
| `CHECK-DAG:` | 順序不問で存在する |
| `CHECK-LABEL:` | セクション区切り (ここから新しいマッチ開始) |

**変数キャプチャ**:
```
; CHECK: add [[REG:a[0-9]+]], a0, a1
; CHECK: sw [[REG]], 0(sp)
; → 最初の行で REG にレジスタ名をキャプチャし、次の行で再利用
```

#### 8-3. テストの配置と lit.cfg

```
llvm/test/CodeGen/MYRISCVX/
├── lit.local.cfg     # ターゲットの有効化チェック
├── add.ll            # 加算テスト
├── sub.ll            # 減算テスト
├── branch.ll         # 分岐テスト
├── call.ll           # 関数呼び出しテスト
└── global.ll         # グローバル変数テスト
```

```python
# lit.local.cfg の例
if not 'MYRISCVX' in config.root.targets:
    config.unsupported = True
```

**テスト駆動開発のワークフロー**:
1. 失敗するテスト `.ll` を書く
2. バックエンドを実装
3. `llvm-lit` で通ることを確認
4. 全テストでリグレッションチェック

---

## 実装環境セットアップまとめ

### 必要なもの

```bash
# 1. LLVM ソースの取得 (本書で指定されたバージョンを使う)
git clone https://github.com/llvm/llvm-project.git
cd llvm-project
git checkout llvmorg-XX.X.X  # 本書指定のバージョン

# 2. ビルドツール
sudo apt install cmake ninja-build gcc g++ python3

# 3. ビルド (自作ターゲット込み)
mkdir build && cd build
cmake -G Ninja \
  -DLLVM_TARGETS_TO_BUILD="RISCV" \
  -DLLVM_ENABLE_PROJECTS="clang" \
  -DCMAKE_BUILD_TYPE=Debug \
  -DLLVM_USE_LINKER=lld \
  ../llvm
ninja -j$(nproc)  # 全コア使用

# 4. 確認
./bin/llc --version  # RISC-V が表示されればOK
```

**ディスク容量**: Debug ビルドは **50GB 以上** 必要。SSD 推奨。
**メモリ**: リンク時に大量消費。8GB 以上、できれば 16GB。
**ビルド時間短縮**: `ninja llc` で llc だけビルドする。

### デバッグのコツ

```bash
# 1. llc の詳細ログを見る
llc -debug -march=myriscvx test.ll 2>&1 | less

# 2. 特定のパスだけログを出す
llc -debug-only=isel test.ll            # 命令選択のみ
llc -debug-only=regalloc test.ll        # レジスタ割当のみ

# 3. DAG を可視化 (graphviz 必要)
llc -view-isel-dags test.ll             # ISel 前
llc -view-sched-dags test.ll            # スケジューリング後

# 4. GDB でデバッグ
gdb --args ./bin/llc -march=myriscvx test.ll
(gdb) break MYRISCVXDAGToDAGISel::Select
(gdb) run
```

---

## 章ごとの依存関係マップ

```
第1章 (アーキテクチャ基礎) ──→ 既習 ✓
第2章 (RISC-V 基礎)        ──→ 既習 ✓ (isa_notes + Practice)
第3章 (LLVM 基礎)          ──→ ★ 新規: IR, SSA, ツール
  ↓
第4章 (バックエンド仕組み) ──→ ★ 核心: TableGen, DAG, ISel
  ↓
第5章 (関数サポート)       ──→ スタックフレーム, 呼び出し規約
  ↓
第6章 (算術・変数・制御)   ──→ 即値, リロケーション, GEP, 分岐
  ↓
第7章 (ELF 出力)           ──→ ELF構造, MC層, エンコーディング
  ↓
第8章 (テスト)             ──→ llvm-lit, FileCheck
```

第1〜2章は既習知識でカバーできる。**第3章から本格的に新しい内容**が始まる。
特に **第4章の TableGen + SelectionDAG** が最大の山場 — ここを理解できれば後は応用。

---

## 関連
- ISA基礎: [isa_notes](../riscv-isa/isa_notes.md) / [isa.html](https://mstk13.github.io/MANABI/riscv-isa/isa.html)
- コンパイラ基礎: [compiler_notes](../compiler/compiler_notes.md) / [compiler.html](https://mstk13.github.io/MANABI/compiler/compiler.html)
- パイプライン: [pipeline_notes](../cpu-pipeline/pipeline_notes.md)
- Practice(実験): [Practice/README.md](../Practice/README.md)

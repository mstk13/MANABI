# Llama decoder 1層の GEMM 分解 — アクセラレータは何を計算するか

図つき版(ブラウザ):
- **[llama_decoder_gemm.html](https://mstk13.github.io/MANABI/llama-decoder/llama_decoder_gemm.html)** — 1層のGEMM分解(各ステップの形と役割をクリック/ホバー)
- **[model_flow.html](https://mstk13.github.io/MANABI/llama-decoder/model_flow.html)** — モデルの動き(Attention=混ぜる / FFN=考える を再生で追う)

ターゲット = **Llama 系 dense decoder transformer の推論**(bring-up は 1B 級)。
1層を分解すると、重い計算は **7本の重みGEMM(行列積)+ Attentionコア2本**。
**演算の8〜9割が GEMM** なので、アレイは **GEMM を空間展開すれば効く**(= [シストリックアレイ](../systolic-array/systolic_array_notes.md))。

---

## 1. 1層の流れ(2ブロック)

```
x ─►RMSNorm─►[Q①][K②][V③]─►RoPE─►[QKᵀ④]─►softmax─►[·V⑤]─►[O⑥]─►(+残差)
  ─►RMSNorm─►[gate⑦][up⑧]─►SiLU⊙─►[down⑨]─►(+残差)─► 次層へ
```

- **Self-Attention ブロック**:①②③ で Q/K/V を作り、④⑤ で注意を計算、⑥ で戻す。
- **FFN ブロック(SwiGLU)**:⑦⑧ で中間8192へ拡大、SiLU⊙、⑨ で hidden へ縮小。
- RMSNorm / RoPE / softmax / SiLU / 残差 = **非GEMM(ベクタ/SFU)**。全体の約15%。

## 2. GEMM は2種類

| 種類 | どれ | 形(Llama 3.2 1B, d=2048, FFN=8192, GQA kv=8) |
|---|---|---|
| **重みGEMM**(7本) | ①Q ②K ③V ⑥O ⑦gate ⑧up ⑨down | 活性 × **学習済み重み行列**。例 ⑦ `[S,2048]×[2048,8192]` |
| **Attentionコア GEMM**(2本) | ④QKᵀ ⑤·V | **活性 × 活性**。形が S(列長)で動的。長文ほど S² で重い |

- **FFN(⑦⑧⑨)が最大** — 中間8192なので1層の重みGEMM FLOPsの過半。
- K/V は **GQA** で幅が小さい(8·64=512)→ KVキャッシュ削減。

## 3. なぜ「空間展開」で効くのか

- 演算の **8〜9割が GEMM** = 同じ積和(MAC)の大量繰り返し。
- それを **N×N の MAC アレイに空間展開**して同時に流すのがアクセラレータの速さの源。
- 非GEMM(15%)は小さなベクタ/特殊関数ユニットに任せる(softmax/正規化/活性/RoPE)。

## 4. prefill と decode で律速が変わる(設計を支配)

| 状況 | 何が起きる | 対策 |
|---|---|---|
| **prefill**(プロンプト一括, S大) | 同じ重みを S 本の活性で再利用 → **計算律速** | アレイを埋め切る |
| **decode**(1トークンずつ, S=1) | 行列×ベクトル。重みを1回しか使わない → **メモリ帯域律速(memory wall)** | **量子化(INT8/INT4)** + ダブルバッファ |

→ だから自作アレイの検証ゴールデンは最初から **INT8 量子化 GEMM** で作る
(SHISAKU `DENNO/Accel/model/gemm_golden.py`)。

## 5. 自作との対応

- PE = MAC(`DENNO/Accel/rtl/mac.sv`, INT8×INT8→INT32)を N×N に並べる = この図の GEMM を担う。
- まず ①〜③⑥〜⑨ の**密GEMM**を流せるアレイを作り、④⑤(Attentionコア)は後段。

## 6. ttsim で実際に各ブロックを動かした(実証・2026-07-01)

上の①〜⑨は机上の分解だけでなく、**Tenstorrent の実スタック(TT-NN → Metalium → LLK)を HW無しの ttsim シミュレータ**で流して動作確認した(SHISAKU `SW/TT_study/examples/`)。定数入力＋閉じた式 golden で照合。

| ブロック | スクリプト | 結果 |
|---|---|---|
| **FFN(⑦gate ⑧up ⑨down + SiLU⊙)** | `swiglu_ffn.py` | PASS(`down(SiLU(x@Wg)⊙(x@Wu))` が golden 一致) |
| **Attention(④QKᵀ ⑤·V + softmax)** 自作 | `attention.py` [本体] | PASS(matmul/transpose/softmax/scalar-mul のみで自作) |
| **GQA ルーティング(KV共有)** | `attention.py` [本体] | PASS(4Q/2KV, head0,1→kv0 / head2,3→kv1 に分離) |
| **SDPA ネイティブ op** | `attention.py` [探索] | PASS(`ttnn.transformer.scaled_dot_product_attention`) |
| **RoPE ネイティブ op** | `attention.py` [探索] | PASS(`ttnn.experimental.rotary_embedding{,_llama}`) |
| **RMSNorm** | `tt_experiment2.py` | PASS(`ttnn.rms_norm`。※`layer_norm` は ttsim 未対応でCRASH → **Llama が RMSNorm 採用で好都合**) |
| **1層まるごと連結** | `decoder_layer.py` | RMSNorm→Attn→+残差→RMSNorm→SwiGLU→+残差 を1本で実行 |

**分かったこと(設計に効くメモ):**
- **アテンション系カーネルは ttsim 実装済み**(SDPA も RoPE も動く)。一方 `layer_norm` は未対応 → Llama の RMSNorm 選択は実装カバレッジ的にも有利。
- **RoPE を定数タイルで golden 化するコツ**: `cos=1, sin=0` を渡すと恒等変換 `x·cos + rotate_half(x)·sin = x` になり、任意テンソル(torch/from_numpy 無しの ttsim では作れない)が不要。
- 環境は **torch無し/`from_numpy`無し=任意テンソル生成不可**だが **scalar 倍は可**。softmax は定数タイルで一様 `1/S` になる性質を golden に使える。
- これで **①〜⑨ の各要素と 1層連結が実スタックで動く**ことを確認済み。次は量子化(INT8)版 GEMM を自作アレイ golden と突き合わせる段階([自作対応](#5-自作との対応))。

## 関連
[シストリックアレイ動作](../systolic-array/systolic_array_notes.md) / [AIアクセラレータ](../ai-accelerator/ai_accel_notes.md) / [物理設計](../physical-design/pd_notes.md) / [HW/RTL](../hw-rtl/hw_rtl_notes.md)

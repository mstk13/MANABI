# Tenstorrent スタックを「ハード無し」で動かす(ttsim)

図つき版(ブラウザ): **[tt_stack.html](https://mstk13.github.io/MANABI/tt-stack/tt_stack.html)**
(レイヤをクリックで説明、▶再生で `ttnn.add` がスタックを下って結果が返るまで)

実機(`/dev/tenstorrent`)無しの WSL で `ttnn.add(3,4)=7` が動く仕組みと、ttsim 上で ttnn op を実験した結果のまとめ。

## スタック(上=高レベル / 下=ハード最寄り)

| 層 | 役割 | API例 |
|---|---|---|
| ① Python | 実験コード | `a=ttnn.full(3); c=ttnn.add(a,b)` |
| ② TT-NN(ttnn) | PyTorch風の高レベル演算 | `add/matmul/gelu/silu` |
| ③ TT-Metalium | カーネルをJITビルドしコアへ配布 | device/program/kernel |
| ④ LLK | Tensixコア上のタイル演算(**ハード最寄り**) | tile eltwise/matmul/SFPU |
| ⑤ ttsim | チップを機能的に肩代わり(`libttsim_bh.so`) | ~4–5KHz, 機能のみ |

🚫 実チップ(Tensix多数+NoC)は無し。⑤ が命令を機能実行して結果を返す。

## 1回の `ttnn.add` の流れ
`Python → TT-NN(op決定) → Metalium(JITビルド+配布) → LLK(タイル加算) → ttsim(機能実行 3+4=7) → 結果が ① へ戻る`。
読み戻しは `c.cpu().to_list()`(release イメージは torch 無しで `to_numpy()` が壊れる)。

## 実験結果(11 op が全PASS, 2026-07-01)
`SW/TT_study/examples/tt_experiment.py`:

| op | 結果 | 意味 |
|---|---|---|
| add/sub/mul | 7/6/12 | 要素ごと |
| **matmul** | 32 | **GEMM(AIの主役)** |
| exp/sqrt/reciprocal | 2.72/3/0.25 | SFPU(特殊関数) |
| relu/**gelu/silu** | 0,3 / 0.84 / 0.73 | **Llama FFN の活性(SwiGLU)** |

bf16 精度で誤差あり(exp=2.7188 vs 2.7183)。`matmul`=GEMM・`gelu/silu`=SwiGLU活性 と、[自作アクセラレータ](../ai-accelerator/ai_accel_notes.md)学習に地続き。

## ハマり所(再現用)
- release イメージに **torch 無し / numpy 有り**。tensor の `to_numpy()` は壊れる → **`tensor.cpu().to_list()`**。
- 入力は torch無しなので `ttnn.full`(定数)が簡単(`from_torch`不可)。
- 運用: `cd ~/SHISAKU/SW/TT_study && make run FILE=examples/tt_experiment.py`。

## 関連
[Llama 1層のGEMM分解](../llama-decoder/llama_decoder_notes.md) / [シストリックアレイ](../systolic-array/systolic_array_notes.md) / [AIアクセラレータ](../ai-accelerator/ai_accel_notes.md)

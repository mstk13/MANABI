# キャッシュコヒーレンス状態機械(MSI → MOESI)

図つき版(ブラウザ): **[coherence_fsm.html](https://mstk13.github.io/MANABI/cache-coherence/coherence_fsm.html)**
(ボタンで読む/書く/スヌープを与え、1ラインの状態が I→S→E→M→O とどう遷移するかを体験)

CHI を「仕様で読む」のでなく「**最小の状態機械を作って動かす**」。実装(動く)は SHISAKU:
- MSI: [`coherence_min.py`](https://github.com/mstk13/SHISAKU/blob/main/interconnect/coherence_min/coherence_min.py)
- MOESI: [`moesi.py`](https://github.com/mstk13/SHISAKU/blob/main/interconnect/coherence_min/moesi.py)

---

## 5状態(CHI名)

| 略 | 意味 | CHI | clean/dirty | 共有 |
|---|---|---|---|---|
| **I** | 無効(持たない) | I | — | — |
| **S** | 共有 | SC | clean | 他も持ちうる |
| **E** | 独占clean | UC | clean | 自分だけ |
| **M** | 変更 | UD | dirty | 自分だけ |
| **O** | 共有dirty | SD | dirty | 自分が供給責任 + 他はS |

## RN 状態遷移表

| 現状態 | Load | Store | SnpShared受信 | SnpUnique受信 |
|---|---|---|---|---|
| I | S または **E** | M(ReadUnique) | I | I |
| S | ヒット | M(他を無効化) | S | **I** |
| E | ヒット | **M(silent・バス無し)** | S | I |
| M | ヒット | ヒット | **O(書戻し無し)** | I(データ提供) |
| O | ヒット | M(S群を無効化) | O(供給継続) | I(データ提供) |

## E と O のメリット(MSIに無い旨味)

- **E(Exclusive)**: 読んだ直後に書くとき、自分しか持たないと分かっているので
  **バス無しで E→M に昇格**(silent upgrade)。read-then-write が速い。
  → `moesi.py` シナリオE: `store` のトレースに `[REQ]/[SNP]` が出ない。
- **O(Owned)**: M のラインを他コアが読んだとき、**メモリに書き戻さず O に降格して供給**。
  → `moesi.py` シナリオO: 読んでも `mem` が古いまま(書き戻し省略)、でも読みは正しい最新値。

## 検証

両 .py とも毎操作後に **不変条件を assert**:
① 排他状態(M/E)は他に保持者なし・各1個まで ② I 以外の保持値はすべて最新(古い値を読んだら即失敗)。

## 関連
[CHI(コヒーレント相互接続)](../chi-interconnect/chi_interconnect_notes.md) / [HW/RTL](../hw-rtl/hw_rtl_notes.md)

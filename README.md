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

## 追加のしかた
1. `トピック名/note.md` を作って書く(図が要れば同じフォルダに `.html`)。
2. この README の目次に1行足す。
3. `git add . && git commit -m "..." && git push` → GitHub 表示・Pages が自動更新。

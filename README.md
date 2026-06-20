# MANABI — 学びノート

**Claude(AI)と一緒に学んだことを、自分用にまとめて蓄積していく場所。**
半導体・コンピュータアーキテクチャ等のトピックを、セッションごとに `.md`(+図 `.html`)で残す。

- **ノート(.md)**: GitHub 上でそのまま整形表示される(private でも、ログインすればどの端末のブラウザでもOK)。
- **図(.html)**: ローカルで開く(`<repo>/トピック/xxx.html` をブラウザで)。
  ※ ライブURLで見たい場合は **このリポジトリを public にすれば GitHub Pages が使える**(private+無料プランは Pages 不可)。

> 関連: 設計プロジェクト本体は [mstk13/SHISAKU](https://github.com/mstk13/SHISAKU)(作る場所)。
> こちら **MANABI は「学びの蓄積」**(理解のまとめ)。役割を分けて運用する。

## 目次
| トピック | ノート | 図(ブラウザ) |
|---|---|---|
| CPU パイプライン(基礎〜段数の決め方〜分岐予測ミス) | [cpu-pipeline/pipeline_notes.md](cpu-pipeline/pipeline_notes.md) | `cpu-pipeline/pipeline_basics.html`(入門)/ `pipeline_depth.html`(3つの力)をローカルで開く |

## 追加のしかた
1. `トピック名/note.md` を作って書く(図が要れば同じフォルダに `.html`)。
2. この README の目次に1行足す。
3. `git add . && git commit -m "..." && git push` → GitHub 表示・Pages が自動更新。

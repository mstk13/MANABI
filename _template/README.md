# 自分で作図する — テンプレートと手順

「自分で描きながら理解する」ための最小テンプレート。私(AI)が作る図と同じ形式なので、
コピーして書き換えるだけで、クリックで説明が出る図が作れる。

## 作り方(3ステップ)
1. **コピー**:`_template/` を新トピック名でコピー
   ```bash
   cp -r ~/MANABI/_template ~/MANABI/my-topic
   ```
2. **編集**:`my-topic/figure_template.html` を VS Code で開き、コメントの
   **①タイトル ②ボックス ③説明データ** の3か所だけ書き換える。
   - ボックスを足す = `<div class="box" data-id="x"><div class="t">名前</div></div>` を足し、
     JS の `DATA` に `x: { t:"見出し", b:"説明" }` を足す(id を合わせるのがコツ)。
3. **確認**:ブラウザで開く(ローカルで動く。ネット不要)
   ```bash
   explorer.exe "$(wslpath -w ~/MANABI/my-topic/figure_template.html)"
   ```

## 公開したくなったら(任意)
- ファイル名を分かりやすく(例 `my_topic.html`)にリネーム
- `~/MANABI/README.md` の目次に1行足す
- `git add . && git commit -m "..." && git push` → GitHub Pages に自動反映

## もっと自由に描きたいとき
- **手描き感覚**:[Excalidraw](https://excalidraw.com/)(ブラウザで箱と矢印を描いて .png/.svg 保存)→ トピックフォルダに置いて note.md から貼る
- **フローだけ**:Mermaid(`.md` に ```mermaid` ブロック)。GitHub がそのまま図に描画してくれる
- **凝った操作**:このテンプレの JS を増やす(再生ボタン・状態ハイライト等)。私の既存図(systolic_array.html 等)がサンプル

## 迷ったら
「こういう図を作りたい」と私に言ってくれれば、**テンプレを埋めた叩き台**を作るので、
あなたはそれを編集しながら理解を深める、という進め方もできる。

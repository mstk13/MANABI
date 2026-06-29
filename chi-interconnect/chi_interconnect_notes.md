# AMBA CHI — 構造・AXIとの比較・動き

図つき版(ブラウザ): **[chi_interconnect.html](https://mstk13.github.io/MANABI/chi-interconnect/chi_interconnect.html)**
(同じ「読み出し」を **AXI と CHI で切り替えて再生**。CHI では Home Node がスヌープを飛ばす様子を追える)

CHI(Coherent Hub Interface)= 多数のキャッシュ持ちコアの**一貫性**を、メッシュNoC上でスケーラブルに回すプロトコル。
NoC/コヒーレンシ学習(VC・credit・デッドロック回避)と直結する。

---

## 1. AXI との根本差

| | AXI(AMBA4/5) | CHI(AMBA5 CHI) |
|---|---|---|
| 目的 | 単純なメモリ転送(master→slave) | **多コアのキャッシュ一貫性** |
| 一貫性 | なし(スヌープしない) | **あり**(HWで整合) |
| 伝送 | 信号ベース・5ch(AR/R/AW/W/B) | **パケット(flit)・層構造**・4ch(REQ/RSP/SNP/DAT) |
| 規模 | 少数マスタ | **メッシュに数十〜数百ノード**(Arm CMN) |
| 経路 | アドレス+ID | **TxnID+送信元/宛先ノードID**でルーティング |

系譜:AXI(非コヒーレント)→ **ACE**(AXIにスヌープ信号追加=線が多くスケールせず)→ **CHI**(パケット化・層構造でメッシュにスケール)。

## 2. 3つの層

- **Protocol**:一貫性のルール(状態・スヌープ・完了)
- **Network**:flit を**ノードID**でメッシュ経路選択(=自作NoCのルータ/mesh層)
- **Link**:隣接ノード間の **credit フロー制御**(L-credit)

→ プロトコルと配線が分離しているので大きなメッシュに載る。

## 3. ノードの役者

- **RN**(Request Node):RN-F=キャッシュ持ちコア / RN-I=I/Oブリッジ(AXIマスタ橋渡し)
- **HN**(Home Node)=一貫性の管理人:あるアドレス範囲の **PoC/PoS**(Point of Coherency/Serialization)。
  **ディレクトリ/スヌープフィルタ**を持ち、必要なRN-Fにだけスヌープを送る。★CHIの心臓
- **SN**(Slave Node):メモリ/周辺

## 4. 4チャネル

| ch | 向き | 中身 |
|---|---|---|
| **REQ** | RN→HN | 要求(ReadShared/ReadUnique/WriteBack/CMO) |
| **SNP** | HN→RN-F | スヌープ(問い合わせ/無効化) |
| **DAT** | 双方向 | データ(読/書/吐き出し) |
| **RSP** | 双方向 | データ無し応答(Comp/CompAck/SnpResp) |

## 5. キャッシュ状態(MOESIベース)

I / UC / UD / SC / SD。U=自分だけ・S=共有・C=メモリと一致(clean)・D=自分が最新(dirty=書き戻し責任)。

## 6. ReadUnique の流れ(独占取得=書くため)

```
1. RN-F(A) ─REQ:ReadUnique→ HN-F
2. HN-F ディレクトリ確認 → B が共有(SC)保持と判明
3. HN-F ─SNP:SnpUnique→ RN-F(B)
4. RN-F(B) ─DAT/RSP→ HN-F   (B: SC→I、dirtyならデータも)
5. HN-F ─DAT:CompData→ RN-F(A)   (無ければSNから取得)
6. RN-F(A) ─RSP:CompAck→ HN-F   → A=UD, B=I
```

**HN-F が直列化点**。要求は必ずHNを通り、HNが「誰をスヌープ/いつ完了」を決める。

## 7. デッドロック回避(自作NoCと同じ語彙)

1. **メッセージクラス分離(VC)**:REQ/RSP/SNP/DAT を別チャネルで運ぶ → 詰まった要求が応答を塞がない。**応答は常にsink可能**(プロトコルデッドロック回避)
2. **Retry機構**:HN資源満杯なら `RetryAck`→ **P-Credit**受領後に再送
3. **Link層 credit(L-credit)**:受信バッファの空き分だけ送る(=valid-ready/credit)
4. **XYルーティング**:次元順+VCで循環依存を断つ

→ 自作 **アービタ→ルータ→2×2 mesh(XY)** は CHI の **Network層**に相当。VC・credit・XY は CHI でも共通言語。

## 関連
[HW/RTL(NoC・検証・PPA)](../hw-rtl/hw_rtl_notes.md) / [コアレッシング/MSHR](../coalescing-mshr/coalescing_mshr_notes.md)

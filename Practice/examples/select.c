// 条件選択 cond ? a : b
// rv64gc(分岐)と rv64gc_zicond(分岐回避: czero) で生成命令を比べる。
int sel(int cond, int a, int b) {
    return cond ? a : b;
}

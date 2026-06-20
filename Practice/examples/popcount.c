// 立っているビット数。rv64gc(汎用)と rv64gc_zbb(cpop 命令)で比べる。
int pc(unsigned long x) {
    return __builtin_popcountl(x);
}

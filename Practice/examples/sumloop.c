// 配列の総和。-O0 と -O2 で生成命令数が大きく変わる。
int sum(const int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++) s += a[i];
    return s;
}

// 実行速度を測るためのドライバ(qemu で time する)。
#include <stdio.h>
extern int sum(const int *a, int n);
int main(void) {
    static int a[1000];
    for (int i = 0; i < 1000; i++) a[i] = i;
    long t = 0;
    for (int r = 0; r < 300000; r++) t += sum(a, 1000);
    printf("%ld\n", t);
    return 0;
}

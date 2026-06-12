#include   <stdio.h>
int add(int a, int b) {
    return a + b;
}
int main() {
    int a = 10;
    int b = 20;
    int c = add(a, b);
    for (int i = 0; i < 5; i++) {
        printf("%d ", i);
    }
    if (c > 20) {
        printf("large\n");
    } else printf("small\n");
    return 0;
}

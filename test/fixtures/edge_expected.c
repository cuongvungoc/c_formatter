#ifndef SAMPLE_H
#define SAMPLE_H
#define SCALE(x) \
((x)*2)
typedef int (*handler_t)(int, char *);
static int run(handler_t cb, char **names, int count) {
    /* leading
     block comment */
    if (count == 0) {
    }
    switch (count) {
    case 0:
        return -1;
    case 1:
        break;
    default:
        count = count + 1;
    }
    for (int i = 0; i < count; i++) {
        char *text = "{ not a block }";
        names[i] = text; // keep line comment
    }
    do {
        count--;
    } while (count > 0);
    return cb(count, names[0]);
}
#endif

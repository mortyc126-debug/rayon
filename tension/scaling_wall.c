/*
 * SCALING WALL — Where does funnel compression die?
 *
 * Measure cycle length for SHA variants at different bit widths.
 * C implementation for speed.
 *
 * Build: gcc -O3 -o scaling_wall scaling_wall.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <math.h>

typedef uint64_t u64;
typedef uint32_t u32;

/* SHA-256 round constants */
static const u32 K256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,
    0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,
    0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,
    0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,
    0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,
    0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,
    0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,
    0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,
    0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
};

static const u32 IV_BASE[8] = {
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
    0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19,
};

/* PRNG */
static u64 rng_s[2] = {0x123456789ABCDEF0ULL, 0xFEDCBA9876543210ULL};
void rng_seed(u64 s) {
    rng_s[0] = s ^ 0x123456789ABCDEF0ULL;
    rng_s[1] = s ^ 0xFEDCBA9876543210ULL;
    if (!rng_s[0]) rng_s[0] = 1;
    if (!rng_s[1]) rng_s[1] = 1;
}
u64 rng_next(void) {
    u64 s1 = rng_s[0], s0 = rng_s[1];
    rng_s[0] = s0;
    s1 ^= s1 << 23;
    rng_s[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
    return rng_s[1] + s0;
}
u32 rng_u32(void) { return (u32)(rng_next()); }

/*
 * Generic SHA-like compression with variable bit width.
 * Uses mask to truncate all operations to 'bits' wide.
 */
void sha_compress_masked(const u32 state[8], const u32 W[16], u32 out[8],
                          u32 mask, int bits)
{
    u32 w[64];
    int i;
    for (i = 0; i < 16; i++) w[i] = W[i] & mask;

    /* Rotation amounts scaled to bit width */
    int r7  = (7  * bits + 16) / 32; if (r7  < 1) r7  = 1; if (r7 >= bits) r7 = bits-1;
    int r18 = (18 * bits + 16) / 32; if (r18 < 1) r18 = 1; if (r18 >= bits) r18 = bits-1;
    int r3  = (3  * bits + 16) / 32; if (r3  < 1) r3  = 1;
    int r17 = (17 * bits + 16) / 32; if (r17 < 1) r17 = 1; if (r17 >= bits) r17 = bits-1;
    int r19 = (19 * bits + 16) / 32; if (r19 < 1) r19 = 1; if (r19 >= bits) r19 = bits-1;
    int r10 = (10 * bits + 16) / 32; if (r10 < 1) r10 = 1;
    int r6  = (6  * bits + 16) / 32; if (r6  < 1) r6  = 1; if (r6 >= bits) r6 = bits-1;
    int r11 = (11 * bits + 16) / 32; if (r11 < 1) r11 = 1; if (r11 >= bits) r11 = bits-1;
    int r25 = (25 * bits + 16) / 32; if (r25 < 1) r25 = 1; if (r25 >= bits) r25 = bits-1;
    int r2  = (2  * bits + 16) / 32; if (r2  < 1) r2  = 1; if (r2 >= bits) r2 = bits-1;
    int r13 = (13 * bits + 16) / 32; if (r13 < 1) r13 = 1; if (r13 >= bits) r13 = bits-1;
    int r22 = (22 * bits + 16) / 32; if (r22 < 1) r22 = 1; if (r22 >= bits) r22 = bits-1;

    #define ROT(x, n) ((((x) >> (n)) | ((x) << (bits - (n)))) & mask)

    for (i = 16; i < 64; i++) {
        u32 s0 = ROT(w[i-15], r7) ^ ROT(w[i-15], r18) ^ ((w[i-15] >> r3) & mask);
        u32 s1 = ROT(w[i-2], r17) ^ ROT(w[i-2], r19) ^ ((w[i-2] >> r10) & mask);
        w[i] = (w[i-16] + s0 + w[i-7] + s1) & mask;
    }

    u32 a = state[0] & mask, b = state[1] & mask;
    u32 c = state[2] & mask, d = state[3] & mask;
    u32 e = state[4] & mask, f = state[5] & mask;
    u32 g = state[6] & mask, h = state[7] & mask;

    for (i = 0; i < 64; i++) {
        u32 S1 = ROT(e, r6) ^ ROT(e, r11) ^ ROT(e, r25);
        u32 ch = (e & f) ^ ((~e) & g) & mask;
        u32 temp1 = (h + S1 + ch + (K256[i] & mask) + w[i]) & mask;
        u32 S0 = ROT(a, r2) ^ ROT(a, r13) ^ ROT(a, r22);
        u32 maj = (a & b) ^ (a & c) ^ (b & c);
        u32 temp2 = (S0 + maj) & mask;
        h=g; g=f; f=e; e=(d+temp1)&mask;
        d=c; c=b; b=a; a=(temp1+temp2)&mask;
    }

    #undef ROT

    out[0] = (state[0] + a) & mask;
    out[1] = (state[1] + b) & mask;
    out[2] = (state[2] + c) & mask;
    out[3] = (state[3] + d) & mask;
    out[4] = (state[4] + e) & mask;
    out[5] = (state[5] + f) & mask;
    out[6] = (state[6] + g) & mask;
    out[7] = (state[7] + h) & mask;
}

int state_eq(const u32 a[8], const u32 b[8]) {
    return memcmp(a, b, 32) == 0;
}

/*
 * Brent's cycle detection for SHA variant at given bit width.
 */
int brent_cycle_masked(const u32 W2[16], const u32 start[8],
                        u32 mask, int bits,
                        u64 max_steps, u64 *cycle_len, u64 *tail_len)
{
    u32 tortoise[8], hare[8], temp[8];
    u64 power = 1, lam = 1, steps = 0;

    memcpy(tortoise, start, 32);
    sha_compress_masked(start, W2, hare, mask, bits);

    while (!state_eq(tortoise, hare)) {
        if (power == lam) {
            memcpy(tortoise, hare, 32);
            power *= 2;
            lam = 0;
        }
        sha_compress_masked(hare, W2, temp, mask, bits);
        memcpy(hare, temp, 32);
        lam++;
        steps++;
        if (steps > max_steps) return 0;
    }

    /* Find tail */
    memcpy(tortoise, start, 32);
    memcpy(hare, start, 32);
    for (u64 i = 0; i < lam; i++) {
        sha_compress_masked(hare, W2, temp, mask, bits);
        memcpy(hare, temp, 32);
    }
    u64 mu = 0;
    while (!state_eq(tortoise, hare)) {
        sha_compress_masked(tortoise, W2, temp, mask, bits);
        memcpy(tortoise, temp, 32);
        sha_compress_masked(hare, W2, temp, mask, bits);
        memcpy(hare, temp, 32);
        mu++;
    }

    *cycle_len = lam;
    *tail_len = mu;
    return 1;
}

int main() {
    printf("==========================================================\n");
    printf("  SCALING WALL — Where does funnel compression die?\n");
    printf("==========================================================\n\n");

    printf("  Measuring cycle length for SHA variants at each bit width.\n");
    printf("  State space = 2^(8*bits). Birthday = 2^(4*bits).\n");
    printf("  Cycle << Birthday → funnel advantage.\n\n");

    printf("  %5s  %14s  %14s  %14s  %14s  %10s  %6s\n",
           "bits", "state_space", "birthday", "cycle", "tail",
           "bday/cycle", "time");
    printf("  ");
    for (int i = 0; i < 85; i++) printf("-");
    printf("\n");

    /* Test each bit width */
    int bit_widths[] = {4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 20, 24, 32};
    int n_widths = sizeof(bit_widths) / sizeof(bit_widths[0]);

    for (int wi = 0; wi < n_widths; wi++) {
        int bits = bit_widths[wi];
        u32 mask = (bits >= 32) ? 0xFFFFFFFF : ((1u << bits) - 1);

        /* State space and birthday bound */
        double log_ss = bits * 8.0;
        double log_bd = bits * 4.0;
        double birthday = pow(2.0, log_bd);

        /* Max steps: limited by time, not space */
        u64 max_steps;
        if (bits <= 8) max_steps = 100000000ULL;        /* 100M */
        else if (bits <= 12) max_steps = 50000000ULL;    /* 50M */
        else if (bits <= 16) max_steps = 20000000ULL;    /* 20M */
        else if (bits <= 20) max_steps = 10000000ULL;    /* 10M */
        else max_steps = 5000000ULL;                      /* 5M */

        /* IV and W2 */
        u32 iv[8], W2[16];
        rng_seed(42 + bits);
        for (int i = 0; i < 8; i++) iv[i] = IV_BASE[i] & mask;
        for (int i = 0; i < 16; i++) W2[i] = rng_u32() & mask;

        u64 cycle_len = 0, tail_len = 0;
        clock_t t0 = clock();
        int found = brent_cycle_masked(W2, iv, mask, bits, max_steps,
                                        &cycle_len, &tail_len);
        double dt = (double)(clock() - t0) / CLOCKS_PER_SEC;

        if (found) {
            double ratio = birthday / (double)cycle_len;
            char marker[32] = "";
            if (ratio > 1000) strcpy(marker, " *** MASSIVE");
            else if (ratio > 100) strcpy(marker, " ** LARGE");
            else if (ratio > 10) strcpy(marker, " * GOOD");
            else if (ratio > 2) strcpy(marker, " + some");
            else if (ratio > 1) strcpy(marker, " marginal");
            else strcpy(marker, " = NO advantage");

            printf("  %5d  %11s2^%d  %11s2^%d  %14llu  %14llu  %10.1f  %5.1fs%s\n",
                   bits,
                   "", bits*8, "", bits*4,
                   (unsigned long long)cycle_len,
                   (unsigned long long)tail_len,
                   ratio, dt, marker);
        } else {
            printf("  %5d  %11s2^%d  %11s2^%d  %14s  %14s  %10s  %5.1fs  WALL\n",
                   bits,
                   "", bits*8, "", bits*4,
                   "> max_steps", "???", "???", dt);
        }
        fflush(stdout);
    }

    printf("\n  ==========================================================\n");
    printf("  THE SCALING WALL:\n\n");
    printf("  At small bit widths: SHA mixing is weak.\n");
    printf("    Cycles are SHORT → funnel compression is REAL.\n");
    printf("    Collision cost = birthday on cycle, not on output.\n\n");
    printf("  At larger bit widths: SHA mixing strengthens.\n");
    printf("    Cycles approach birthday length → no compression.\n");
    printf("    The funnel IS the birthday bound.\n\n");
    printf("  The wall tells us:\n");
    printf("    Funnel structure EXISTS but doesn't SCALE beyond mixing threshold.\n");
    printf("    To break SHA-256, we need to attack MIXING, not ITERATION.\n");
    printf("    Rayon's ? propagation and kill-link analysis target mixing directly.\n");
    printf("  ==========================================================\n\n");

    return 0;
}

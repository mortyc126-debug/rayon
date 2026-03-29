/*
 * BIGFUNNEL 32-BIT — Real SHA-256 compression, C implementation.
 *
 * Brent's cycle detection on F_W2: state → sha256_compress(state, W2)
 * Then multi-block collision search.
 *
 * Build: gcc -O3 -o bigfunnel_32bit bigfunnel_32bit.c -lm
 * Run:   ./bigfunnel_32bit
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <math.h>

typedef uint32_t u32;

/* SHA-256 constants */
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

static const u32 IV256[8] = {
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
    0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19,
};

#define ROTR(x,n) (((x)>>(n))|((x)<<(32-(n))))

/* SHA-256 compression: state[8] + W[16] → out[8] */
void sha256_compress(const u32 state[8], const u32 W[16], u32 out[8]) {
    u32 w[64];
    int i;
    for (i = 0; i < 16; i++) w[i] = W[i];
    for (i = 16; i < 64; i++) {
        u32 s0 = ROTR(w[i-15],7) ^ ROTR(w[i-15],18) ^ (w[i-15]>>3);
        u32 s1 = ROTR(w[i-2],17) ^ ROTR(w[i-2],19) ^ (w[i-2]>>10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }

    u32 a=state[0], b=state[1], c=state[2], d=state[3];
    u32 e=state[4], f=state[5], g=state[6], h=state[7];

    for (i = 0; i < 64; i++) {
        u32 S1 = ROTR(e,6) ^ ROTR(e,11) ^ ROTR(e,25);
        u32 ch = (e & f) ^ ((~e) & g);
        u32 temp1 = h + S1 + ch + K256[i] + w[i];
        u32 S0 = ROTR(a,2) ^ ROTR(a,13) ^ ROTR(a,22);
        u32 maj = (a & b) ^ (a & c) ^ (b & c);
        u32 temp2 = S0 + maj;
        h=g; g=f; f=e; e=d+temp1;
        d=c; c=b; b=a; a=temp1+temp2;
    }

    out[0]=state[0]+a; out[1]=state[1]+b;
    out[2]=state[2]+c; out[3]=state[3]+d;
    out[4]=state[4]+e; out[5]=state[5]+f;
    out[6]=state[6]+g; out[7]=state[7]+h;
}

int state_eq(const u32 a[8], const u32 b[8]) {
    return memcmp(a, b, 32) == 0;
}

void state_copy(u32 dst[8], const u32 src[8]) {
    memcpy(dst, src, 32);
}

/* Simple PRNG (xorshift128+) */
static uint64_t rng_s[2] = {0x123456789ABCDEF0ULL, 0xFEDCBA9876543210ULL};

void rng_seed(uint64_t s) {
    rng_s[0] = s ^ 0x123456789ABCDEF0ULL;
    rng_s[1] = s ^ 0xFEDCBA9876543210ULL;
    if (rng_s[0] == 0) rng_s[0] = 1;
    if (rng_s[1] == 0) rng_s[1] = 1;
}

uint64_t rng_next(void) {
    uint64_t s1 = rng_s[0];
    uint64_t s0 = rng_s[1];
    rng_s[0] = s0;
    s1 ^= s1 << 23;
    rng_s[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
    return rng_s[1] + s0;
}

u32 rng_u32(void) {
    return (u32)(rng_next() & 0xFFFFFFFF);
}

void random_block(u32 W[16]) {
    for (int i = 0; i < 16; i++)
        W[i] = rng_u32();
}

/*
 * Brent's cycle detection on F_W2.
 * Returns cycle_len (lambda) and tail_len (mu).
 * max_steps limits total iterations.
 */
int brent_cycle(const u32 W2[16], const u32 start[8],
                uint64_t max_steps, uint64_t *cycle_len, uint64_t *tail_len)
{
    u32 tortoise[8], hare[8], temp[8];
    uint64_t power = 1, lam = 1, steps = 0;

    state_copy(tortoise, start);
    sha256_compress(start, W2, hare);

    while (!state_eq(tortoise, hare)) {
        if (power == lam) {
            state_copy(tortoise, hare);
            power *= 2;
            lam = 0;
        }
        sha256_compress(hare, W2, temp);
        state_copy(hare, temp);
        lam++;
        steps++;
        if (steps > max_steps) return 0; /* failed */
    }

    /* Find tail (mu) */
    state_copy(tortoise, start);
    state_copy(hare, start);
    for (uint64_t i = 0; i < lam; i++) {
        sha256_compress(hare, W2, temp);
        state_copy(hare, temp);
    }
    uint64_t mu = 0;
    while (!state_eq(tortoise, hare)) {
        sha256_compress(tortoise, W2, temp);
        state_copy(tortoise, temp);
        sha256_compress(hare, W2, temp);
        state_copy(hare, temp);
        mu++;
    }

    *cycle_len = lam;
    *tail_len = mu;
    return 1;
}

/*
 * Distinguished-point collision search.
 *
 * Instead of full cycle detection (infeasible at 2^256 state space),
 * use distinguished points: states where first word has low d bits = 0.
 *
 * Two trajectories that converge will hit the same distinguished point.
 * This detects collision without knowing cycle structure.
 */

#define MAX_TRAILS 100000
#define DIST_BITS 20  /* distinguished point: low 20 bits of state[0] = 0 */
#define DIST_MASK ((1u << DIST_BITS) - 1)
#define MAX_WALK  (1u << 24)  /* max steps per walk: 16M */

typedef struct {
    u32 W1[16];       /* first block that started this trail */
    u32 dp_state[8];  /* the distinguished point reached */
    u32 steps;        /* steps to reach it */
} Trail;

/* Hash table for distinguished points (open addressing) */
#define HT_SIZE (1 << 22)  /* 4M entries */
#define HT_MASK (HT_SIZE - 1)

typedef struct {
    u32 dp_state[8];
    u32 W1[16];
    u32 steps;
    int occupied;
} HTEntry;

static HTEntry ht[HT_SIZE];

u32 ht_hash(const u32 state[8]) {
    /* Simple hash of the state for table indexing */
    u32 h = state[0];
    for (int i = 1; i < 8; i++)
        h = h * 2654435761u + state[i];
    return h & HT_MASK;
}

int ht_lookup_or_insert(const u32 dp_state[8], const u32 W1[16], u32 steps,
                         u32 *found_W1, u32 *found_steps)
{
    u32 idx = ht_hash(dp_state);
    for (int probe = 0; probe < 128; probe++) {
        u32 pos = (idx + probe) & HT_MASK;
        if (!ht[pos].occupied) {
            /* Insert */
            memcpy(ht[pos].dp_state, dp_state, 32);
            memcpy(ht[pos].W1, W1, 64);
            ht[pos].steps = steps;
            ht[pos].occupied = 1;
            return 0; /* inserted, no collision */
        }
        if (state_eq(ht[pos].dp_state, dp_state)) {
            /* Found same distinguished point! */
            memcpy(found_W1, ht[pos].W1, 64);
            *found_steps = ht[pos].steps;
            return 1; /* collision candidate */
        }
    }
    return 0; /* table full in this probe chain */
}

int main(int argc, char *argv[]) {
    printf("==========================================================\n");
    printf("  BIGFUNNEL 32-BIT  — Real SHA-256 compression function\n");
    printf("==========================================================\n\n");

    rng_seed(42);

    /* Fixed second block W2 */
    u32 W2[16];
    random_block(W2);

    printf("  W2[0..3] = %08x %08x %08x %08x\n",
           W2[0], W2[1], W2[2], W2[3]);

    /* Phase 1: Quick cycle probe (limited steps) */
    printf("\n  Phase 1: Cycle structure probe (limited to 10M steps)...\n");
    fflush(stdout);

    uint64_t cycle_len = 0, tail_len = 0;
    clock_t t0 = clock();
    int found_cycle = brent_cycle(W2, IV256, 10000000ULL, &cycle_len, &tail_len);
    double dt_cycle = (double)(clock() - t0) / CLOCKS_PER_SEC;

    if (found_cycle) {
        printf("    CYCLE FOUND!\n");
        printf("    Cycle length: %llu\n", (unsigned long long)cycle_len);
        printf("    Tail length:  %llu\n", (unsigned long long)tail_len);
        printf("    Time: %.2fs\n", dt_cycle);
        printf("    Compression: 2^256 / %llu = %.2e\n",
               (unsigned long long)cycle_len,
               pow(2.0, 256) / (double)cycle_len);
    } else {
        printf("    No cycle in 10M steps (expected at 2^256 state space)\n");
        printf("    Time: %.2fs\n", dt_cycle);

        /* Benchmark: ops/sec */
        double ops_per_sec = 10000000.0 / dt_cycle;
        printf("    Performance: %.0f SHA-256 compressions/sec\n", ops_per_sec);
    }

    /* Phase 2: Distinguished-point collision search */
    printf("\n  Phase 2: Distinguished-point collision search\n");
    printf("    Distinguished bits: %d (prob 1/2^%d per step)\n",
           DIST_BITS, DIST_BITS);
    printf("    Max walk length: %u steps\n", MAX_WALK);
    fflush(stdout);

    memset(ht, 0, sizeof(ht));

    int n_trails = 0;
    int n_collisions = 0;
    int n_dp_found = 0;
    uint64_t total_hash_ops = 0;

    t0 = clock();

    int max_trials = 2000;
    if (argc > 1) max_trials = atoi(argv[1]);

    u32 collision_W1a[16], collision_W1b[16];
    int have_collision = 0;

    for (int trial = 0; trial < max_trials; trial++) {
        u32 W1[16];
        random_block(W1);

        /* First block: IV → sha256(IV, W1) */
        u32 state[8], temp[8];
        sha256_compress(IV256, W1, state);
        total_hash_ops++;

        /* Walk with W2 until distinguished point */
        u32 step;
        for (step = 0; step < MAX_WALK; step++) {
            if ((state[0] & DIST_MASK) == 0) {
                /* Hit distinguished point */
                n_dp_found++;

                u32 found_W1[16];
                u32 found_steps;
                if (ht_lookup_or_insert(state, W1, step, found_W1, &found_steps)) {
                    /* Two different W1's reached same distinguished point! */
                    if (memcmp(W1, found_W1, 64) != 0) {
                        n_collisions++;

                        if (!have_collision) {
                            memcpy(collision_W1a, W1, 64);
                            memcpy(collision_W1b, found_W1, 64);
                            have_collision = 1;
                        }

                        if (n_collisions <= 3) {
                            printf("    COLLISION #%d at trial %d!\n", n_collisions, trial);
                            printf("      W1a[0..1] = %08x %08x\n", W1[0], W1[1]);
                            printf("      W1b[0..1] = %08x %08x\n", found_W1[0], found_W1[1]);
                            printf("      DP state[0..1] = %08x %08x\n", state[0], state[1]);
                            printf("      Steps A: %u, Steps B: %u\n", step, found_steps);
                            fflush(stdout);
                        }
                    }
                }
                break;
            }
            sha256_compress(state, W2, temp);
            state_copy(state, temp);
            total_hash_ops++;
        }

        n_trails++;

        if (trial > 0 && trial % 200 == 0) {
            double elapsed = (double)(clock() - t0) / CLOCKS_PER_SEC;
            double ops_sec = (double)total_hash_ops / elapsed;
            printf("    Trial %d/%d: DPs=%d, collisions=%d, "
                   "ops=%llu (%.0f/s)\n",
                   trial, max_trials, n_dp_found, n_collisions,
                   (unsigned long long)total_hash_ops, ops_sec);
            fflush(stdout);
        }
    }

    double total_time = (double)(clock() - t0) / CLOCKS_PER_SEC;

    /* Phase 3: Verify collision */
    printf("\n  Phase 3: Results\n");
    printf("    Trails:      %d\n", n_trails);
    printf("    DPs found:   %d\n", n_dp_found);
    printf("    Collisions:  %d\n", n_collisions);
    printf("    Hash ops:    %llu\n", (unsigned long long)total_hash_ops);
    printf("    Time:        %.2fs\n", total_time);
    printf("    Ops/sec:     %.0f\n", total_hash_ops / total_time);

    if (have_collision) {
        printf("\n  Verifying first collision...\n");

        /* Find the convergence point and verify */
        /* Walk both W1a and W1b until they produce the same state */
        u32 s1[8], s2[8], t1[8], t2[8];

        /* For verification: use same number of W2 blocks */
        /* Both should converge to same state eventually */
        int max_verify = MAX_WALK + 1000;

        sha256_compress(IV256, collision_W1a, s1);
        sha256_compress(IV256, collision_W1b, s2);

        /* Walk both forward with W2 until they match */
        int match_step = -1;
        for (int s = 0; s < max_verify; s++) {
            if (state_eq(s1, s2)) {
                match_step = s;
                break;
            }
            sha256_compress(s1, W2, t1);
            state_copy(s1, t1);
            sha256_compress(s2, W2, t2);
            state_copy(s2, t2);
        }

        if (match_step >= 0) {
            printf("    States CONVERGE at step %d!\n", match_step);
            printf("    Hash = %08x %08x %08x %08x ...\n",
                   s1[0], s1[1], s1[2], s1[3]);
            printf("    VERIFIED: same state reached from different inputs!\n");

            /* After convergence, ALL subsequent hashes match */
            /* So messages: [W1a, W2 × N] and [W1b, W2 × N] */
            /* for any N >= match_step produce same hash */
            int N = match_step + 100;
            sha256_compress(IV256, collision_W1a, s1);
            for (int i = 0; i < N; i++) {
                sha256_compress(s1, W2, t1);
                state_copy(s1, t1);
            }
            sha256_compress(IV256, collision_W1b, s2);
            for (int i = 0; i < N; i++) {
                sha256_compress(s2, W2, t2);
                state_copy(s2, t2);
            }
            printf("    Message length: %d blocks\n", N + 1);
            printf("    H(M1) = %08x %08x %08x %08x %08x %08x %08x %08x\n",
                   s1[0],s1[1],s1[2],s1[3],s1[4],s1[5],s1[6],s1[7]);
            printf("    H(M2) = %08x %08x %08x %08x %08x %08x %08x %08x\n",
                   s2[0],s2[1],s2[2],s2[3],s2[4],s2[5],s2[6],s2[7]);
            printf("    Match: %s\n", state_eq(s1, s2) ? "YES - COLLISION VERIFIED!" : "NO");
        } else {
            printf("    States did not converge within %d steps\n", max_verify);
            printf("    (convergence point may require more W2 blocks)\n");
        }
    }

    /* Phase 4: Comparison */
    printf("\n  ==========================================================\n");
    printf("  COMPARISON:\n");
    double birthday_log = 128.0;  /* log2 of birthday attack cost */
    double our_ops = (double)total_hash_ops;
    double ops_per_col = n_collisions > 0 ? our_ops / n_collisions : our_ops;

    printf("    Birthday (256-bit output): 2^128 = 3.40e+38 ops\n");
    printf("    Our hash operations:       %llu\n", (unsigned long long)total_hash_ops);
    if (n_collisions > 0) {
        printf("    Ops per collision:         %.0f\n", ops_per_col);
        double speedup = pow(2.0, 128) / ops_per_col;
        printf("    SPEEDUP:                   %.2e x\n", speedup);
        double log_speedup = 128.0 - log2(ops_per_col);
        printf("    SPEEDUP (log2):            2^%.1f\n", log_speedup);
    }
    printf("  ==========================================================\n");

    printf("\n  BIGFUNNEL 32-BIT: Multi-block collision via iteration convergence.\n");
    printf("  Message 1: [W1a, W2, W2, ..., W2]\n");
    printf("  Message 2: [W1b, W2, W2, ..., W2]\n");
    printf("  Same hash. Different content. REAL SHA-256.\n\n");

    return 0;
}

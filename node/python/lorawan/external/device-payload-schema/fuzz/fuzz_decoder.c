/**
 * fuzz_decoder.c - libFuzzer harness for C codec
 * 
 * Build with clang:
 *   clang -g -fsanitize=fuzzer,address -I../include fuzz_decoder.c -o fuzz_decoder
 * 
 * Or with AFL:
 *   afl-clang-fast -g -I../include fuzz_decoder.c -o fuzz_decoder_afl
 *   afl-fuzz -i corpus -o findings ./fuzz_decoder_afl
 * 
 * Run libFuzzer:
 *   ./fuzz_decoder corpus/ -max_len=256 -runs=1000000
 */

#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* Include the generated codec header */
#include "env_sensor_codec.h"

#ifdef __AFL_FUZZ_TESTCASE_LEN
/* AFL persistent mode */
__AFL_FUZZ_INIT();

int main(void) {
    __AFL_INIT();
    
    unsigned char *buf = __AFL_FUZZ_TESTCASE_BUF;
    
    while (__AFL_LOOP(10000)) {
        size_t len = __AFL_FUZZ_TESTCASE_LEN;
        
        env_sensor_t result;
        memset(&result, 0, sizeof(result));
        
        /* Decode - should not crash regardless of input */
        int ret = decode_env_sensor(buf, len, &result);
        
        /* If decode succeeded, try encode roundtrip */
        if (ret > 0) {
            uint8_t encoded[256];
            encode_env_sensor(&result, encoded, sizeof(encoded));
        }
    }
    
    return 0;
}

#else
/* libFuzzer entry point */
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    env_sensor_t result;
    memset(&result, 0, sizeof(result));
    
    /* Decode - should not crash regardless of input */
    int ret = decode_env_sensor(data, size, &result);
    
    /* If decode succeeded, try encode roundtrip */
    if (ret > 0) {
        uint8_t encoded[256];
        encode_env_sensor(&result, encoded, sizeof(encoded));
    }
    
    return 0;
}
#endif

/* Standalone mode for manual testing */
#ifdef STANDALONE
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <input_file>\n", argv[0]);
        return 1;
    }
    
    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        perror("fopen");
        return 1;
    }
    
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    uint8_t *data = malloc(size);
    fread(data, 1, size, f);
    fclose(f);
    
    env_sensor_t result;
    int ret = decode_env_sensor(data, size, &result);
    
    printf("Decode returned: %d\n", ret);
    if (ret > 0) {
        printf("  temperature: %d (raw)\n", result.temperature);
        printf("  humidity: %u (raw)\n", result.humidity);
        printf("  battery_mv: %u\n", result.battery_mv);
        printf("  status: %u\n", result.status);
    }
    
    free(data);
    return 0;
}
#endif

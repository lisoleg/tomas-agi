//=============================================================================
// tshield_hal.c — T-Shield Hardware Abstraction Layer Implementation
// T-Shield Cognitive Safety Layer — Zynq-7000 PS (ARM Cortex-A9)
//
// Provides register-level access to T-Shield PL accelerators.
// Supports both bare-metal (Xilinx standalone) and Linux (UIO/mmap).
//=============================================================================

#include "tshield_hal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef __linux__
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#define UIO_DEVICE "/dev/uio0"
#define UIO_MAP_SIZE 0x1000  // 4KB register space
#endif

//=============================================================================
// Internal helpers
//=============================================================================

static inline void reg_write(tshield_handle_t *h, uint32_t offset, uint32_t value) {
    volatile uint32_t *reg = (volatile uint32_t *)((uint8_t *)h->mmap_base + offset);
    *reg = value;
}

static inline uint32_t reg_read(tshield_handle_t *h, uint32_t offset) {
    volatile uint32_t *reg = (volatile uint32_t *)((uint8_t *)h->mmap_base + offset);
    return *reg;
}

// Convert float [0.0, 1.0] to Q8.8 fixed-point
static inline uint32_t float_to_q88(float val) {
    if (val < 0.0f) val = 0.0f;
    if (val > 255.99f) val = 255.99f;
    return (uint32_t)(val * 256.0f);
}

// Convert Q8.8 fixed-point to float
static inline float q88_to_float(uint32_t val) {
    return (float)(val & 0xFFFF) / 256.0f;
}

// Get current time in milliseconds
static inline float get_time_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (float)(ts.tv_sec * 1000) + (float)(ts.tv_nsec) / 1000000.0f;
}

//=============================================================================
// Initialization
//=============================================================================

tshield_handle_t* tshield_init(uint32_t base_addr) {
    tshield_handle_t *handle = (tshield_handle_t *)calloc(1, sizeof(tshield_handle_t));
    if (!handle) return NULL;

    handle->base_addr = base_addr;

#ifdef __linux__
    // Linux UIO/mmap path
    handle->uio_fd = open(UIO_DEVICE, O_RDWR | O_SYNC);
    if (handle->uio_fd < 0) {
        fprintf(stderr, "TSHIELD: Failed to open %s\n", UIO_DEVICE);
        free(handle);
        return NULL;
    }

    handle->mmap_base = mmap(NULL, UIO_MAP_SIZE,
                             PROT_READ | PROT_WRITE, MAP_SHARED,
                             handle->uio_fd, 0);
    if (handle->mmap_base == MAP_FAILED) {
        fprintf(stderr, "TSHIELD: mmap failed\n");
        close(handle->uio_fd);
        free(handle);
        return NULL;
    }
#else
    // Bare-metal: base_addr is directly accessible
    handle->mmap_base = (void *)(uintptr_t)base_addr;
    handle->uio_fd = -1;
#endif

    // Verify hardware version
    uint32_t version = reg_read(handle, TSHIELD_REG_VERSION);
    if (version != TSHIELD_VERSION_V1_0) {
        fprintf(stderr, "TSHIELD: Version mismatch! Expected 0x%08X, got 0x%08X\n",
                TSHIELD_VERSION_V1_0, version);
        // Continue anyway — may be simulation
    }

    // Soft reset
    reg_write(handle, TSHIELD_REG_CTRL, TSHIELD_CTRL_SOFT_RESET);
    reg_write(handle, TSHIELD_REG_CTRL, 0);

    // Set default thresholds
    tshield_set_dz_thresholds(handle, 1.0f / 256.0f, 0.1f);

    handle->is_initialized = 1;
    return handle;
}

void tshield_cleanup(tshield_handle_t *handle) {
    if (!handle) return;

    // Soft reset
    if (handle->is_initialized) {
        reg_write(handle, TSHIELD_REG_CTRL, TSHIELD_CTRL_SOFT_RESET);
    }

#ifdef __linux__
    if (handle->mmap_base && handle->mmap_base != MAP_FAILED)
        munmap(handle->mmap_base, UIO_MAP_SIZE);
    if (handle->uio_fd >= 0)
        close(handle->uio_fd);
#endif

    free(handle);
}

//=============================================================================
// Configuration
//=============================================================================

void tshield_set_dz_thresholds(tshield_handle_t *handle,
                               float dz_thresh, float warn_thresh) {
    if (!handle || !handle->is_initialized) return;
    reg_write(handle, TSHIELD_REG_DZ_THRESH, float_to_q88(dz_thresh));
    reg_write(handle, TSHIELD_REG_WARN_THRESH, float_to_q88(warn_thresh));
}

//=============================================================================
// Dead-Zone Check
//=============================================================================

int tshield_deadzone_check(tshield_handle_t *handle,
                           const float *activations, int num_acts,
                           int *levels, tshield_result_t *result) {
    if (!handle || !handle->is_initialized) return -1;

    float start_time = get_time_ms();

    // Configure number of activations
    reg_write(handle, TSHIELD_REG_NUM_ACTS, (uint32_t)num_acts);

    // In a real DMA implementation, we would DMA the activations to PL here.
    // For now, this uses the software fallback for the data path,
    // and reads the PL result for comparison.
    // TODO: Implement AXI DMA transfer for activation data.

    // Start Dead-Zone check
    reg_write(handle, TSHIELD_REG_CTRL, TSHIELD_CTRL_DZ_START);
    reg_write(handle, TSHIELD_REG_CTRL, 0);

    // Wait for completion (polling — in production, use interrupt)
    int timeout = 10000;  // 10ms timeout
    while (!(reg_read(handle, TSHIELD_REG_STATUS) & TSHIELD_STATUS_DZ_DONE)) {
        if (--timeout == 0) {
            fprintf(stderr, "TSHIELD: Dead-Zone timeout!\n");
            return -1;
        }
    }

    // Read results
    int dead_cnt = (int)reg_read(handle, TSHIELD_REG_DZ_DEAD_CNT);
    int warn_cnt = (int)reg_read(handle, TSHIELD_REG_DZ_WARN_CNT);
    float iota = tshield_get_iota_scene(handle);

    // Fill output (PL results — for verification, compare with SW fallback)
    if (levels) {
        // Note: individual levels come from DMA stream, not registers.
        // Use software fallback for per-element levels.
        tshield_sw_deadzone_check(activations, num_acts,
                                  q88_to_float(reg_read(handle, TSHIELD_REG_DZ_THRESH)),
                                  q88_to_float(reg_read(handle, TSHIELD_REG_WARN_THRESH)),
                                  levels, NULL, NULL);
    }

    if (result) {
        result->dz_dead_count = dead_cnt;
        result->dz_warning_count = warn_cnt;
        result->iota_scene = iota;
        result->latency_ms = get_time_ms() - start_time;
    }

    return 0;
}

//=============================================================================
// MUS Ambiguity Detection
//=============================================================================

int tshield_mus_detect(tshield_handle_t *handle,
                       tshield_box_t *boxes, int num_boxes,
                       tshield_result_t *result) {
    if (!handle || !handle->is_initialized) return -1;

    float start_time = get_time_ms();

    // Configure
    reg_write(handle, TSHIELD_REG_NUM_BOXES, (uint32_t)num_boxes);

    // Start MUS computation
    reg_write(handle, TSHIELD_REG_CTRL, TSHIELD_CTRL_MUS_START);
    reg_write(handle, TSHIELD_REG_CTRL, 0);

    // Wait for completion
    int timeout = 10000;
    while (!(reg_read(handle, TSHIELD_REG_STATUS) & TSHIELD_STATUS_MUS_DONE)) {
        if (--timeout == 0) {
            fprintf(stderr, "TSHIELD: MUS timeout!\n");
            return -1;
        }
    }

    // Read results
    int ambig_cnt = (int)reg_read(handle, TSHIELD_REG_MUS_AMBIG_CNT);

    // Use software fallback for per-box MUS marking
    tshield_sw_mus_detect(boxes, num_boxes, 0.3f, 0.05f, &ambig_cnt);

    if (result) {
        result->mus_ambig_count = ambig_cnt;
        result->iota_scene = tshield_get_iota_scene(handle);
        result->latency_ms = get_time_ms() - start_time;
    }

    return 0;
}

//=============================================================================
// Full T-Shield Inference
//=============================================================================

int tshield_infer(tshield_handle_t *handle,
                  const float *activations, int num_acts,
                  tshield_box_t *boxes, int num_boxes,
                  tshield_result_t *result) {
    if (!handle || !handle->is_initialized) return -1;

    float start_time = get_time_ms();

    // Step 1: Dead-Zone check
    int *levels = (int *)calloc(num_acts, sizeof(int));
    if (!levels) return -1;

    tshield_result_t dz_result = {0};
    if (tshield_deadzone_check(handle, activations, num_acts, levels, &dz_result) < 0) {
        free(levels);
        return -1;
    }

    // Mark boxes with DZ levels (simplified: map activation DZ to box DZ)
    for (int i = 0; i < num_boxes && i < num_acts; i++) {
        boxes[i].dz_level = levels[i];
    }

    // Step 2: MUS ambiguity detection
    tshield_result_t mus_result = {0};
    if (tshield_mus_detect(handle, boxes, num_boxes, &mus_result) < 0) {
        free(levels);
        return -1;
    }

    // Step 3: Compute ℐ-scene
    float iota = tshield_get_iota_scene(handle);

    // Compile final result
    if (result) {
        result->iota_scene = iota;
        result->dz_dead_count = dz_result.dz_dead_count;
        result->dz_warning_count = dz_result.dz_warning_count;
        result->mus_ambig_count = mus_result.mus_ambig_count;
        result->latency_ms = get_time_ms() - start_time;
    }

    free(levels);
    return 0;
}

//=============================================================================
// Utility functions
//=============================================================================

uint32_t tshield_get_version(tshield_handle_t *handle) {
    if (!handle || !handle->is_initialized) return 0;
    return reg_read(handle, TSHIELD_REG_VERSION);
}

float tshield_get_iota_scene(tshield_handle_t *handle) {
    if (!handle || !handle->is_initialized) return 0.0f;
    return q88_to_float(reg_read(handle, TSHIELD_REG_IOTA_SCENE));
}

//=============================================================================
// Software fallback implementations
//=============================================================================

void tshield_sw_deadzone_check(const float *activations, int num_acts,
                               float dz_thresh, float warn_thresh,
                               int *levels, int *dead_cnt, int *warn_cnt) {
    int dead = 0, warn = 0;

    for (int i = 0; i < num_acts; i++) {
        float abs_val = activations[i] < 0 ? -activations[i] : activations[i];

        if (abs_val < warn_thresh) {
            levels[i] = TSHIELD_DZ_DEAD;
            dead++;
        } else if (abs_val < dz_thresh) {
            levels[i] = TSHIELD_DZ_WARNING;
            warn++;
        } else {
            levels[i] = TSHIELD_DZ_SAFE;
        }
    }

    if (dead_cnt) *dead_cnt = dead;
    if (warn_cnt) *warn_cnt = warn;
}

void tshield_sw_mus_detect(tshield_box_t *boxes, int num_boxes,
                           float iou_thresh, float conf_diff_thresh,
                           int *ambig_count) {
    int count = 0;

    for (int i = 0; i < num_boxes; i++) {
        boxes[i].mus_status = TSHIELD_MUS_CLEAR;
        boxes[i].ambiguous_with = -1;
    }

    for (int i = 0; i < num_boxes; i++) {
        for (int j = i + 1; j < num_boxes; j++) {
            // Compute IoU
            float x1 = boxes[i].x1 > boxes[j].x1 ? boxes[i].x1 : boxes[j].x1;
            float y1 = boxes[i].y1 > boxes[j].y1 ? boxes[i].y1 : boxes[j].y1;
            float x2 = boxes[i].x2 < boxes[j].x2 ? boxes[i].x2 : boxes[j].x2;
            float y2 = boxes[i].y2 < boxes[j].y2 ? boxes[i].y2 : boxes[j].y2;

            float inter = (x2 > x1 && y2 > y1) ? (x2 - x1) * (y2 - y1) : 0.0f;
            float area_i = (boxes[i].x2 - boxes[i].x1) * (boxes[i].y2 - boxes[i].y1);
            float area_j = (boxes[j].x2 - boxes[j].x1) * (boxes[j].y2 - boxes[j].y1);
            float iou = inter / (area_i + area_j - inter + 1e-6f);

            float conf_diff = boxes[i].confidence - boxes[j].confidence;
            if (conf_diff < 0) conf_diff = -conf_diff;

            if (iou > iou_thresh && conf_diff < conf_diff_thresh) {
                boxes[i].mus_status = TSHIELD_MUS_AMBIGUOUS;
                boxes[i].ambiguous_with = j;
                boxes[j].mus_status = TSHIELD_MUS_AMBIGUOUS;
                boxes[j].ambiguous_with = i;
                count++;
            }
        }
    }

    if (ambig_count) *ambig_count = count;
}

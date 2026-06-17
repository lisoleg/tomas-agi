//=============================================================================
// tshield_hal.h — T-Shield Hardware Abstraction Layer (PS side)
// T-Shield Cognitive Safety Layer — Zynq-7000 PS (ARM Cortex-A9)
//
// Provides a C interface for the T-Shield PL accelerators via AXI4-Lite.
// Designed for Xilinx Vitis/XSDK bare-metal or Linux userspace (UIO).
//=============================================================================

#ifndef TSHIELD_HAL_H
#define TSHIELD_HAL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

//=============================================================================
// Register Map (offsets from base address)
//=============================================================================
#define TSHIELD_REG_CTRL           0x00  // [0]=dz_start, [1]=mus_start, [2]=reset
#define TSHIELD_REG_STATUS         0x04  // [0]=dz_done, [1]=mus_done, [2]=dz_busy, [3]=mus_busy
#define TSHIELD_REG_DZ_THRESH      0x08  // Dead-Zero threshold (Q8.8)
#define TSHIELD_REG_WARN_THRESH    0x0C  // Warning threshold (Q8.8)
#define TSHIELD_REG_NUM_BOXES      0x10  // Number of detection boxes
#define TSHIELD_REG_NUM_ACTS       0x14  // Number of activation values
#define TSHIELD_REG_DZ_DEAD_CNT    0x18  // Dead count (read-only)
#define TSHIELD_REG_DZ_WARN_CNT    0x1C  // Warning count (read-only)
#define TSHIELD_REG_MUS_AMBIG_CNT  0x20  // MUS ambiguity count (read-only)
#define TSHIELD_REG_IOTA_SCENE     0x24  // ℐ-scene value (Q8.8, read-only)
#define TSHIELD_REG_KSNAP_CFG      0x28  // κ-Snap config [7:0]=max_config, [15:8]=strategy
#define TSHIELD_REG_VERSION        0x2C  // Hardware version (read-only)

//=============================================================================
// Constants
//=============================================================================
#define TSHIELD_VERSION_V1_0       0x00010000

// CTRL register bits
#define TSHIELD_CTRL_DZ_START      (1 << 0)
#define TSHIELD_CTRL_MUS_START     (1 << 1)
#define TSHIELD_CTRL_SOFT_RESET    (1 << 2)

// STATUS register bits
#define TSHIELD_STATUS_DZ_DONE     (1 << 0)
#define TSHIELD_STATUS_MUS_DONE    (1 << 1)
#define TSHIELD_STATUS_DZ_BUSY     (1 << 2)
#define TSHIELD_STATUS_MUS_BUSY    (1 << 3)

// Dead-Zone levels
#define TSHIELD_DZ_SAFE            0x00
#define TSHIELD_DZ_WARNING         0x01
#define TSHIELD_DZ_DEAD            0x02

// MUS status
#define TSHIELD_MUS_CLEAR          0x00
#define TSHIELD_MUS_AMBIGUOUS      0x01

//=============================================================================
// Data structures
//=============================================================================

// Detection box for MUS processing
typedef struct {
    float x1, y1, x2, y2;       // Bounding box coordinates
    float confidence;            // Detection confidence [0.0, 1.0]
    int   label;                 // Class label
    int   dz_level;              // Dead-Zone level (SAFE/WARNING/DEAD)
    int   mus_status;            // MUS status (CLEAR/AMBIGUOUS)
    int   ambiguous_with;        // Index of ambiguous pair (-1 if none)
} tshield_box_t;

// T-Shield inference result
typedef struct {
    float  iota_scene;           // ℐ-scene value [0.0, 1.0]
    int    dz_dead_count;        // Number of DEAD activations
    int    dz_warning_count;     // Number of WARNING activations
    int    mus_ambig_count;      // Number of ambiguous pairs
    float  latency_ms;           // Processing latency in milliseconds
} tshield_result_t;

// T-Shield hardware handle
typedef struct {
    uint32_t base_addr;          // AXI4-Lite base address
    int      uio_fd;             // UIO device file descriptor (Linux)
    void    *mmap_base;          // Memory-mapped register base
    int      is_initialized;     // Initialization flag
} tshield_handle_t;

//=============================================================================
// API Functions
//=============================================================================

/**
 * Initialize T-Shield HAL
 * @param base_addr  AXI4-Lite base address (physical or mmap'd)
 * @return Handle pointer, or NULL on failure
 */
tshield_handle_t* tshield_init(uint32_t base_addr);

/**
 * Cleanup T-Shield HAL
 * @param handle  T-Shield handle
 */
void tshield_cleanup(tshield_handle_t *handle);

/**
 * Set Dead-Zone thresholds
 * @param handle        T-Shield handle
 * @param dz_thresh     Dead-Zero threshold [0.0, 1.0]
 * @param warn_thresh   Warning threshold [0.0, dz_thresh]
 */
void tshield_set_dz_thresholds(tshield_handle_t *handle,
                               float dz_thresh, float warn_thresh);

/**
 * Run Dead-Zone check on activation values
 * @param handle        T-Shield handle
 * @param activations   Array of activation values (float, [-1.0, 1.0])
 * @param num_acts      Number of activations
 * @param[out] levels   Output level array (SAFE/WARNING/DEAD per element)
 * @param[out] result   Result structure
 * @return 0 on success, -1 on failure
 */
int tshield_deadzone_check(tshield_handle_t *handle,
                           const float *activations, int num_acts,
                           int *levels, tshield_result_t *result);

/**
 * Run MUS ambiguity detection on detection boxes
 * @param handle        T-Shield handle
 * @param boxes         Detection box array
 * @param num_boxes     Number of boxes
 * @param[out] result   Result structure
 * @return 0 on success, -1 on failure
 */
int tshield_mus_detect(tshield_handle_t *handle,
                       tshield_box_t *boxes, int num_boxes,
                       tshield_result_t *result);

/**
 * Full T-Shield inference (Dead-Zone + MUS + ℐ-scene)
 * @param handle        T-Shield handle
 * @param activations   Activation values
 * @param num_acts      Number of activations
 * @param boxes         Detection boxes
 * @param num_boxes     Number of boxes
 * @param[out] result   Complete result
 * @return 0 on success, -1 on failure
 */
int tshield_infer(tshield_handle_t *handle,
                  const float *activations, int num_acts,
                  tshield_box_t *boxes, int num_boxes,
                  tshield_result_t *result);

/**
 * Get hardware version
 * @param handle  T-Shield handle
 * @return Version number (0x00010000 = v1.0.0)
 */
uint32_t tshield_get_version(tshield_handle_t *handle);

/**
 * Get ℐ-scene value from last inference
 * @param handle  T-Shield handle
 * @return ℐ-scene value [0.0, 1.0]
 */
float tshield_get_iota_scene(tshield_handle_t *handle);

/**
 * Software fallback: Dead-Zone check (pure CPU)
 * Used when PL is not available or for verification
 */
void tshield_sw_deadzone_check(const float *activations, int num_acts,
                               float dz_thresh, float warn_thresh,
                               int *levels, int *dead_cnt, int *warn_cnt);

/**
 * Software fallback: MUS ambiguity detection (pure CPU)
 */
void tshield_sw_mus_detect(tshield_box_t *boxes, int num_boxes,
                           float iou_thresh, float conf_diff_thresh,
                           int *ambig_count);

#ifdef __cplusplus
}
#endif

#endif /* TSHIELD_HAL_H */

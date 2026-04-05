//
// Academic License - for use in teaching, academic research, and meeting
// course requirements at degree granting institutions only.  Not for
// government, commercial, or other organizational use.
//
// File: MotorCMDSending_types.h
//
// Code generated for Simulink model 'MotorCMDSending'.
//
// Model version                  : 1.2
// Simulink Coder version         : 25.1 (R2025a) 21-Nov-2024
// C/C++ source code generated on : Thu Aug 28 11:22:32 2025
//
// Target selection: ert.tlc
// Embedded hardware selection: ARM Compatible->ARM Cortex
// Code generation objectives: Unspecified
// Validation result: Not run
//
#ifndef MotorCMDSending_types_h_
#define MotorCMDSending_types_h_
#include "rtwtypes.h"
#ifndef struct_px4_internal_block_PX4Actuato_T
#define struct_px4_internal_block_PX4Actuato_T

struct px4_internal_block_PX4Actuato_T
{
  boolean_T matlabCodegenIsDeleted;
  int32_T isInitialized;
  boolean_T isSetupComplete;
  uint8_T QSize;
  boolean_T ValidMotorIdx[12];
  boolean_T ValidServoIdx[8];
};

#endif                                // struct_px4_internal_block_PX4Actuato_T

// Parameters (default storage)
typedef struct P_MotorCMDSending_T_ P_MotorCMDSending_T;

// Forward declaration for rtModel
typedef struct tag_RTM_MotorCMDSending_T RT_MODEL_MotorCMDSending_T;

#endif                                 // MotorCMDSending_types_h_

//
// File trailer for generated code.
//
// [EOF]
//

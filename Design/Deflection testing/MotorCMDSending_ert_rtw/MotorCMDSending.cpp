//
// Academic License - for use in teaching, academic research, and meeting
// course requirements at degree granting institutions only.  Not for
// government, commercial, or other organizational use.
//
// File: MotorCMDSending.cpp
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
#include "MotorCMDSending.h"
#include "MotorCMDSending_types.h"
#include "rtwtypes.h"
#include "MotorCMDSending_private.h"

extern "C"
{

#include "rt_nonfinite.h"

}

// Block signals (default storage)
B_MotorCMDSending_T MotorCMDSending_B;

// Block states (default storage)
DW_MotorCMDSending_T MotorCMDSending_DW;

// Real-time model
RT_MODEL_MotorCMDSending_T MotorCMDSending_M_ = RT_MODEL_MotorCMDSending_T();
RT_MODEL_MotorCMDSending_T *const MotorCMDSending_M = &MotorCMDSending_M_;

// Forward declaration for local functions
static void MotorCMD_PX4Actuators_setupImpl(px4_internal_block_PX4Actuato_T *obj);
static void MotorCMD_PX4Actuators_setupImpl(px4_internal_block_PX4Actuato_T *obj)
{
  int32_T n;
  int32_T n_0;
  obj->ValidMotorIdx[0] = true;
  obj->ValidMotorIdx[1] = true;
  obj->ValidMotorIdx[2] = true;
  obj->ValidMotorIdx[3] = true;
  n = 0;
  for (int32_T b_k = 0; b_k < 12; b_k++) {
    // Start for MATLABSystem: '<Root>/PX4 Actuator Write'
    if (obj->ValidMotorIdx[b_k]) {
      n++;
    }
  }

  n_0 = 0;
  for (int32_T b_k = 0; b_k < 8; b_k++) {
    // Start for MATLABSystem: '<Root>/PX4 Actuator Write'
    if (obj->ValidServoIdx[b_k]) {
      n_0++;
    }
  }

  // Start for MATLABSystem: '<Root>/PX4 Actuator Write'
  obj->QSize = static_cast<uint8_T>(n + n_0);
  MW_actuators_init(obj->QSize);
}

// Model step function
void MotorCMDSending_step(void)
{
  int32_T i;
  real32_T servoValues[8];

  // MATLABSystem: '<Root>/PX4 Actuator Write' incorporates:
  //   Constant: '<Root>/Constant'
  //   Constant: '<Root>/Constant1'

  for (i = 0; i < 12; i++) {
    MotorCMDSending_B.motorValues_m[i] = (rtNaNF);
  }

  for (i = 0; i < 8; i++) {
    servoValues[i] = (rtNaNF);
  }

  MotorCMDSending_B.motorValues_m[0] = MotorCMDSending_P.Constant_Value;
  MotorCMDSending_B.motorValues_m[1] = MotorCMDSending_P.Constant_Value;
  MotorCMDSending_B.motorValues_m[2] = MotorCMDSending_P.Constant_Value;
  MotorCMDSending_B.motorValues_m[3] = MotorCMDSending_P.Constant_Value;
  MW_actuators_set(MotorCMDSending_P.Constant1_Value,
                   &MotorCMDSending_B.motorValues_m[0], &servoValues[0]);

  // End of MATLABSystem: '<Root>/PX4 Actuator Write'

  // Update absolute time for base rate
  // The "clockTick0" counts the number of times the code of this task has
  //  been executed. The absolute time is the multiplication of "clockTick0"
  //  and "Timing.stepSize0". Size of "clockTick0" ensures timer will not
  //  overflow during the application lifespan selected.

  MotorCMDSending_M->Timing.taskTime0 =
    ((time_T)(++MotorCMDSending_M->Timing.clockTick0)) *
    MotorCMDSending_M->Timing.stepSize0;
}

// Model initialize function
void MotorCMDSending_initialize(void)
{
  // Registration code

  // initialize non-finites
  rt_InitInfAndNaN(sizeof(real_T));
  rtmSetTFinal(MotorCMDSending_M, -1);
  MotorCMDSending_M->Timing.stepSize0 = 0.2;

  // External mode info
  MotorCMDSending_M->Sizes.checksums[0] = (3198317602U);
  MotorCMDSending_M->Sizes.checksums[1] = (2774527369U);
  MotorCMDSending_M->Sizes.checksums[2] = (2410989924U);
  MotorCMDSending_M->Sizes.checksums[3] = (3130403880U);

  {
    static const sysRanDType rtAlwaysEnabled = SUBSYS_RAN_BC_ENABLE;
    static RTWExtModeInfo rt_ExtModeInfo;
    static const sysRanDType *systemRan[2];
    MotorCMDSending_M->extModeInfo = (&rt_ExtModeInfo);
    rteiSetSubSystemActiveVectorAddresses(&rt_ExtModeInfo, systemRan);
    systemRan[0] = &rtAlwaysEnabled;
    systemRan[1] = &rtAlwaysEnabled;
    rteiSetModelMappingInfoPtr(MotorCMDSending_M->extModeInfo,
      &MotorCMDSending_M->SpecialInfo.mappingInfo);
    rteiSetChecksumsPtr(MotorCMDSending_M->extModeInfo,
                        MotorCMDSending_M->Sizes.checksums);
    rteiSetTPtr(MotorCMDSending_M->extModeInfo, rtmGetTPtr(MotorCMDSending_M));
  }

  {
    int32_T i;

    // Start for MATLABSystem: '<Root>/PX4 Actuator Write'
    for (i = 0; i < 12; i++) {
      MotorCMDSending_DW.obj.ValidMotorIdx[i] = false;
    }

    for (i = 0; i < 8; i++) {
      MotorCMDSending_DW.obj.ValidServoIdx[i] = false;
    }

    MotorCMDSending_DW.obj.matlabCodegenIsDeleted = false;
    MotorCMDSending_DW.obj.isSetupComplete = false;
    MotorCMDSending_DW.obj.isInitialized = 1;
    MotorCMD_PX4Actuators_setupImpl(&MotorCMDSending_DW.obj);
    MotorCMDSending_DW.obj.isSetupComplete = true;

    // End of Start for MATLABSystem: '<Root>/PX4 Actuator Write'
  }
}

// Model terminate function
void MotorCMDSending_terminate(void)
{
  real32_T servoValues[8];

  // Terminate for MATLABSystem: '<Root>/PX4 Actuator Write'
  if (!MotorCMDSending_DW.obj.matlabCodegenIsDeleted) {
    MotorCMDSending_DW.obj.matlabCodegenIsDeleted = true;
    if ((MotorCMDSending_DW.obj.isInitialized == 1) &&
        MotorCMDSending_DW.obj.isSetupComplete) {
      for (int32_T i = 0; i < 12; i++) {
        MotorCMDSending_B.motorValues[i] = (rtNaNF);
      }

      for (int32_T i = 0; i < 8; i++) {
        servoValues[i] = (rtNaNF);
      }

      for (int32_T i = 0; i < 12; i++) {
        if (MotorCMDSending_DW.obj.ValidMotorIdx[i]) {
          MotorCMDSending_B.motorValues[i] = 0.0F;
        }
      }

      for (int32_T i = 0; i < 8; i++) {
        if (MotorCMDSending_DW.obj.ValidServoIdx[i]) {
          servoValues[i] = 0.0F;
        }
      }

      MW_actuators_set(false, &MotorCMDSending_B.motorValues[0], &servoValues[0]);
      MW_actuators_terminate();
    }
  }

  // End of Terminate for MATLABSystem: '<Root>/PX4 Actuator Write'
}

//
// File trailer for generated code.
//
// [EOF]
//

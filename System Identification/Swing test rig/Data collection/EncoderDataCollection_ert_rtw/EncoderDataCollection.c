/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: EncoderDataCollection.c
 *
 * Code generated for Simulink model 'EncoderDataCollection'.
 *
 * Model version                  : 2.0
 * Simulink Coder version         : 24.1 (R2024a) 19-Nov-2023
 * C/C++ source code generated on : Wed Sep  4 11:33:23 2024
 *
 * Target selection: ert.tlc
 * Embedded hardware selection: Atmel->AVR
 * Code generation objectives: Unspecified
 * Validation result: Not run
 */

#include "EncoderDataCollection.h"
#include "rtwtypes.h"
#include <stddef.h>
#include "EncoderDataCollection_private.h"

/* Block states (default storage) */
DW_EncoderDataCollection_T EncoderDataCollection_DW;

/* Real-time model */
static RT_MODEL_EncoderDataCollectio_T EncoderDataCollection_M_;
RT_MODEL_EncoderDataCollectio_T *const EncoderDataCollection_M =
  &EncoderDataCollection_M_;

/* Model step function */
void EncoderDataCollection_step(void)
{
  int32_T dataIn;
  char_T labelTerminated[4];

  /* MATLABSystem: '<Root>/Encoder' */
  if (EncoderDataCollection_DW.obj_p.SampleTime !=
      EncoderDataCollection_P.Encoder_SampleTime) {
    EncoderDataCollection_DW.obj_p.SampleTime =
      EncoderDataCollection_P.Encoder_SampleTime;
  }

  if (EncoderDataCollection_DW.obj_p.TunablePropsChanged) {
    EncoderDataCollection_DW.obj_p.TunablePropsChanged = false;
  }

  /* MATLABSystem: '<Root>/Serial Transmit' incorporates:
   *  MATLABSystem: '<Root>/Encoder'
   * */
  MW_EncoderRead(EncoderDataCollection_DW.obj_p.Index, &dataIn);
  if (EncoderDataCollection_DW.obj.Protocol !=
      EncoderDataCollection_P.SerialTransmit_Protocol) {
    EncoderDataCollection_DW.obj.Protocol =
      EncoderDataCollection_P.SerialTransmit_Protocol;
  }

  labelTerminated[0] = 'v';
  labelTerminated[1] = 'a';
  labelTerminated[2] = 'l';
  labelTerminated[3] = '\x00';
  MW_Serial_write(EncoderDataCollection_DW.obj.port, &dataIn, 1.0,
                  EncoderDataCollection_DW.obj.dataSizeInBytes,
                  EncoderDataCollection_DW.obj.sendModeEnum,
                  EncoderDataCollection_DW.obj.dataType,
                  EncoderDataCollection_DW.obj.sendFormatEnum, 2.0,
                  &labelTerminated[0], NULL, 0.0, NULL, 0.0);

  /* End of MATLABSystem: '<Root>/Serial Transmit' */

  /* Update absolute time for base rate */
  /* The "clockTick0" counts the number of times the code of this task has
   * been executed. The absolute time is the multiplication of "clockTick0"
   * and "Timing.stepSize0". Size of "clockTick0" ensures timer will not
   * overflow during the application lifespan selected.
   */
  EncoderDataCollection_M->Timing.taskTime0 =
    ((time_T)(++EncoderDataCollection_M->Timing.clockTick0)) *
    EncoderDataCollection_M->Timing.stepSize0;
}

/* Model initialize function */
void EncoderDataCollection_initialize(void)
{
  /* Registration code */
  rtmSetTFinal(EncoderDataCollection_M, 10.0);
  EncoderDataCollection_M->Timing.stepSize0 = 0.01;

  /* External mode info */
  EncoderDataCollection_M->Sizes.checksums[0] = (3179649214U);
  EncoderDataCollection_M->Sizes.checksums[1] = (259806278U);
  EncoderDataCollection_M->Sizes.checksums[2] = (35518794U);
  EncoderDataCollection_M->Sizes.checksums[3] = (3942112654U);

  {
    static const sysRanDType rtAlwaysEnabled = SUBSYS_RAN_BC_ENABLE;
    static RTWExtModeInfo rt_ExtModeInfo;
    static const sysRanDType *systemRan[3];
    EncoderDataCollection_M->extModeInfo = (&rt_ExtModeInfo);
    rteiSetSubSystemActiveVectorAddresses(&rt_ExtModeInfo, systemRan);
    systemRan[0] = &rtAlwaysEnabled;
    systemRan[1] = &rtAlwaysEnabled;
    systemRan[2] = &rtAlwaysEnabled;
    rteiSetModelMappingInfoPtr(EncoderDataCollection_M->extModeInfo,
      &EncoderDataCollection_M->SpecialInfo.mappingInfo);
    rteiSetChecksumsPtr(EncoderDataCollection_M->extModeInfo,
                        EncoderDataCollection_M->Sizes.checksums);
    rteiSetTPtr(EncoderDataCollection_M->extModeInfo, rtmGetTPtr
                (EncoderDataCollection_M));
  }

  /* Start for MATLABSystem: '<Root>/Encoder' */
  EncoderDataCollection_DW.obj_p.Index = 0U;
  EncoderDataCollection_DW.obj_p.matlabCodegenIsDeleted = false;
  EncoderDataCollection_DW.obj_p.SampleTime =
    EncoderDataCollection_P.Encoder_SampleTime;
  EncoderDataCollection_DW.obj_p.isInitialized = 1L;
  MW_EncoderSetup(2UL, 3UL, &EncoderDataCollection_DW.obj_p.Index);
  EncoderDataCollection_DW.obj_p.isSetupComplete = true;
  EncoderDataCollection_DW.obj_p.TunablePropsChanged = false;

  /* InitializeConditions for MATLABSystem: '<Root>/Encoder' */
  MW_EncoderReset(EncoderDataCollection_DW.obj_p.Index);

  /* Start for MATLABSystem: '<Root>/Serial Transmit' */
  EncoderDataCollection_DW.obj.matlabCodegenIsDeleted = false;
  EncoderDataCollection_DW.obj.Protocol =
    EncoderDataCollection_P.SerialTransmit_Protocol;
  EncoderDataCollection_DW.obj.isInitialized = 1L;
  EncoderDataCollection_DW.obj.port = 0.0;
  EncoderDataCollection_DW.obj.dataSizeInBytes = 4.0;
  EncoderDataCollection_DW.obj.dataType = 5.0;
  EncoderDataCollection_DW.obj.sendModeEnum = 2.0;
  EncoderDataCollection_DW.obj.sendFormatEnum = 0.0;
  MW_SCI_Open(0);
  EncoderDataCollection_DW.obj.isSetupComplete = true;
}

/* Model terminate function */
void EncoderDataCollection_terminate(void)
{
  /* Terminate for MATLABSystem: '<Root>/Encoder' */
  if (!EncoderDataCollection_DW.obj_p.matlabCodegenIsDeleted) {
    EncoderDataCollection_DW.obj_p.matlabCodegenIsDeleted = true;
    if ((EncoderDataCollection_DW.obj_p.isInitialized == 1L) &&
        EncoderDataCollection_DW.obj_p.isSetupComplete) {
      MW_EncoderRelease();
    }
  }

  /* End of Terminate for MATLABSystem: '<Root>/Encoder' */

  /* Terminate for MATLABSystem: '<Root>/Serial Transmit' */
  if (!EncoderDataCollection_DW.obj.matlabCodegenIsDeleted) {
    EncoderDataCollection_DW.obj.matlabCodegenIsDeleted = true;
  }

  /* End of Terminate for MATLABSystem: '<Root>/Serial Transmit' */
}

/*
 * File trailer for generated code.
 *
 * [EOF]
 */

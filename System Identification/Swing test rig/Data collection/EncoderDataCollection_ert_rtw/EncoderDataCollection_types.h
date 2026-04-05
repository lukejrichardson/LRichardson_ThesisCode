/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: EncoderDataCollection_types.h
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

#ifndef EncoderDataCollection_types_h_
#define EncoderDataCollection_types_h_
#include "rtwtypes.h"
#ifndef struct_tag_hiATgaifu8RfrjZ2yifYbH
#define struct_tag_hiATgaifu8RfrjZ2yifYbH

struct tag_hiATgaifu8RfrjZ2yifYbH
{
  boolean_T matlabCodegenIsDeleted;
  int32_T isInitialized;
  boolean_T isSetupComplete;
  boolean_T TunablePropsChanged;
  real_T SampleTime;
  uint8_T Index;
};

#endif                                 /* struct_tag_hiATgaifu8RfrjZ2yifYbH */

#ifndef typedef_codertarget_arduinobase_inter_T
#define typedef_codertarget_arduinobase_inter_T

typedef struct tag_hiATgaifu8RfrjZ2yifYbH codertarget_arduinobase_inter_T;

#endif                             /* typedef_codertarget_arduinobase_inter_T */

#ifndef struct_tag_qbUFhX6Bp3RsgYGeqgZpEH
#define struct_tag_qbUFhX6Bp3RsgYGeqgZpEH

struct tag_qbUFhX6Bp3RsgYGeqgZpEH
{
  int16_T __dummy;
};

#endif                                 /* struct_tag_qbUFhX6Bp3RsgYGeqgZpEH */

#ifndef typedef_c_arduinodriver_ArduinoSerial_T
#define typedef_c_arduinodriver_ArduinoSerial_T

typedef struct tag_qbUFhX6Bp3RsgYGeqgZpEH c_arduinodriver_ArduinoSerial_T;

#endif                             /* typedef_c_arduinodriver_ArduinoSerial_T */

#ifndef struct_tag_ghK8YWVQwtwpThnQHmUfd
#define struct_tag_ghK8YWVQwtwpThnQHmUfd

struct tag_ghK8YWVQwtwpThnQHmUfd
{
  boolean_T matlabCodegenIsDeleted;
  int32_T isInitialized;
  boolean_T isSetupComplete;
  real_T Protocol;
  real_T port;
  real_T dataSizeInBytes;
  real_T dataType;
  real_T sendModeEnum;
  real_T sendFormatEnum;
  c_arduinodriver_ArduinoSerial_T SerialDriverObj;
};

#endif                                 /* struct_tag_ghK8YWVQwtwpThnQHmUfd */

#ifndef typedef_codertarget_arduinobase_int_g_T
#define typedef_codertarget_arduinobase_int_g_T

typedef struct tag_ghK8YWVQwtwpThnQHmUfd codertarget_arduinobase_int_g_T;

#endif                             /* typedef_codertarget_arduinobase_int_g_T */

/* Parameters (default storage) */
typedef struct P_EncoderDataCollection_T_ P_EncoderDataCollection_T;

/* Forward declaration for rtModel */
typedef struct tag_RTM_EncoderDataCollection_T RT_MODEL_EncoderDataCollectio_T;

#endif                                 /* EncoderDataCollection_types_h_ */

/*
 * File trailer for generated code.
 *
 * [EOF]
 */

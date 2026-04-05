## This cmakelist.txt file was generated from
## the UAVToolbox Support Package for PX4 Autopilots

set(MAVLINK_LIBRARY_DIR "${CMAKE_BINARY_DIR}/mavlink")
set(MAVLINK_DIALECT_UAVIONIX "uAvionix")

add_definitions(
-DMODEL=MotorCMDSending -DNUMST=1 -DNCSTATES=0 -DHAVESTDIO -DMODEL_HAS_DYNAMICALLY_LOADED_SFCNS=0 -DXCP_DAQ_SUPPORT -DXCP_CALIBRATION_SUPPORT -DXCP_TIMESTAMP_SUPPORT -DXCP_TIMESTAMP_BASED_ON_SIMULATION_TIME -DXCP_SET_MTA_SUPPORT -DEXTMODE_XCP_TRIGGER_SUPPORT -DXCP_ADDRESS_GRANULARITY=XCP_ADDRESS_GRANULARITY_BYTE -DXCP_MEM_BLOCK_1_SIZE=0 -DXCP_MEM_BLOCK_1_NUMBER=1 -DXCP_MEM_BLOCK_2_SIZE=0 -DXCP_MEM_BLOCK_2_NUMBER=0 -DXCP_MEM_BLOCK_3_SIZE=0 -DXCP_MEM_BLOCK_3_NUMBER=0 -DXCP_MEM_RESERVED_POOLS_TOTAL_SIZE=130 -DXCP_MEM_RESERVED_POOLS_NUMBER=1 -DXCP_MEM_DAQ_RESERVED_POOL_BLOCKS_NUMBER=3 -DXCP_MEM_DAQ_RESERVED_POOLS_NUMBER=1 -DXCP_MIN_EVENT_NO_RESERVED_POOL=1 -DXCP_MAX_CTO_SIZE=32 -DXCP_MAX_DTO_SIZE=65532 -DXCP_MAX_ODT_ENTRY_SIZE=255 -DEXTMODE_STATIC -DEXTMODE_STATIC_SIZE=1024 -DON_TARGET_WAIT_FOR_START=0 -DCLASSIC_INTERFACE=0 -DALLOCATIONFCN=0 -DTID01EQ=0 -DTERMFCN=1 -DONESTEPFCN=1 -DMAT_FILE=0 -DMULTI_INSTANCE_CODE=0 -DEXT_MODE=1 -DINTEGER_CODE=0 -DMT=0 -DPX4 -DFMUvx -DNULL=0 -DMW_PX4_NUTTX_BUILD -DEXTMODE_DISABLETESTING -DEXTMODE_DISABLEPRINTF -DEXTMODE_DISABLE_ARGS_PROCESSING=1 -D__linux__ -DXCP_PLATFORM_LINUX_NO_PIE_SUPPORT -DSTACK_SIZE=64 -D__MW_TARGET_USE_HARDWARE_RESOURCES_H__ -DRT -DMW_PX4_DISABLE_MAVLINK=1 -DMW_PX4_EXTMODE_BAUD_RATE=3000000 -DMW_PX4_EXTMODE_HWPORT=\"/dev/ttyACM0\" )

px4_add_module(
    MODULE modules__px4_simulink_app
    MAIN px4_simulink_app
    STACK_MAIN 2000
SRCS
   MW_PX4_ActuatorDevice.cpp
   MW_PX4_Actuators.cpp
   xcp_ext_mode.c
   ert_main.cpp
   MotorCMDSending.cpp
   MotorCMDSending_data.cpp
   rtGetInf.cpp
   rtGetNaN.cpp
   rt_nonfinite.cpp
   xcp_ext_common.c
   xcp_ext_classic_trigger.c
   xcp.c
   xcp_standard.c
   xcp_daq.c
   xcp_calibration.c
   xcp_fifo.c
   xcp_transport.c
   xcp_mem_default.c
   xcp_drv_rtiostream.c
   xcp_utils.c
   xcp_frame_serial.c
   xcp_ext_param_default_serial.c
   MW_PX4_TaskControl.cpp
   nuttxinitialize.cpp
   MW_PX4_rtiostream_serial.cpp
   xcp_platform_default.c
   MW_PX4_Actuators.h
   MW_PX4_ActuatorDevice.h
   rtGetInf.h
   rtGetNaN.h
   rt_nonfinite.h
   MW_custom_RTOS_header.h
   MotorCMDSending.h
   MotorCMDSending_private.h
   MotorCMDSending_types.h
   ext_mode_types.h
   multiword_types.h
   rtmodel.h
   rtwtypes.h
   rtw_extmode.h
   sysran_types.h
   MW_uORB_busstruct_conversion.h
   ext_types.h
   ext_work.h
   rtiostream.h
   ext_mode.h
   xcp_ext_classic_trigger.h
   xcp_ext_common.h
   xcp_ext_param.h
   xcp_common.h
   xcp_utils.h
   xcp.h
   xcp_transport.h
   xcp_drv.h
   xcp_mem.h
   xcp_mem_config.h
   xcp_mem_config_helper.h
   xcp_mem_default.h
   xcp_platform_default.h
   xcp_platform.h
   xcp_internal.h
   xcp_calibration.h
   xcp_calibration_types.h
   xcp_cfg.h
   xcp_daq.h
   xcp_daq_ext.h
   xcp_daq_types.h
   xcp_standard.h
   xcp_standard_ext.h
   xcp_standard_types.h
   xcp_types.h
   xcp_transport_internal.h
   xcp_fifo.h
   xcp_frame.h
   xcp_frame_serial.h
   xcp_transport_types.h
   MW_PX4_TaskControl.h
   nuttxinitialize.h
   MW_target_hardware_resources.h
    COMPILE_FLAGS
       -fpermissive
       -Wno-narrowing
       -Wno-address-of-packed-member 
       -Wno-cast-align
    INCLUDES
       ${PX4_SOURCE_DIR}/src/modules/px4_simulink_app
       ${PX4_SOURCE_DIR}/src/modules/mavlink
       ${MAVLINK_LIBRARY_DIR}
       ${MAVLINK_LIBRARY_DIR}/${CONFIG_MAVLINK_DIALECT}
       ${MAVLINK_LIBRARY_DIR}/${MAVLINK_DIALECT_UAVIONIX}
)

get_target_property(PX4_SL_APP_COMPILE_FLAGS modules__px4_simulink_app COMPILE_OPTIONS)
list(REMOVE_ITEM PX4_SL_APP_COMPILE_FLAGS -Werror)
set_target_properties(modules__px4_simulink_app PROPERTIES COMPILE_OPTIONS "${PX4_SL_APP_COMPILE_FLAGS}")


# NVIDIA GPU metric module using the Python bindings for NVML
#
# (C)opyright 2011, 2012 Bernard Li <bernard@vanhpc.org>
# All Rights Reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import datetime
from pynvml import *
from random import randint
import time

descriptors = list()

device = 0
eventSet = 0
violation_dur = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

'''Return the descriptor based on the name'''
def find_descriptor(name):
    for d in descriptors:
        if d['name'] == name:
            return d

'''Build descriptor from arguments and append it to the global descriptors list if call_back does not return with error'''
def build_descriptor(name, call_back, time_max, value_type, units, slope, format, description, groups):
    d = {'name': name,
        'call_back': call_back,
        'time_max': time_max,
        'value_type': value_type,
        'units': units,
        'slope': slope,
        'format': format,
        'description': description,
        'groups': groups,
        }

    try:
        call_back(name)
        descriptors.append(d)
    except NVMLError, err:
        print "Failed to build descriptor :", name, ":", str(err)
        pass
    except NameError, err:
        print "Failed to build descriptor :", name, ":", str(err)
        pass

def get_gpu_num():
    return int(nvmlDeviceGetCount())
def get_gpu_use_num(name):
    use_num = 0
    for i in range(get_gpu_num()):
         is_use = gpu_device_handler('gpu%s_process' %i)
         if(int(is_use)):
            use_num += 1
    return use_num

def gpu_num_handler(name):
    return get_gpu_num()

def gpu_driver_version_handler(name):
    return nvmlSystemGetDriverVersion()

def gpu_get_device_by_name(name):
    d = find_descriptor(name)
    (gpu, metric) = name.split('_', 1)
    gpu_id = int(gpu.split('gpu')[1])
    gpu_device = nvmlDeviceGetHandleByIndex(gpu_id)
    return gpu_device

def gpu_device_handler(name):
    global violation_dur, violation_rate
    (gpu, metric) = name.split('_', 1)
    gpu_id = int(gpu.split('gpu')[1])
    gpu_device = gpu_get_device_by_name(name)

    if (metric == 'type'):
        return nvmlDeviceGetName(gpu_device)
    elif (metric == 'uuid'):
        return nvmlDeviceGetUUID(gpu_device)
    elif (metric == 'pci_id'):
        return nvmlDeviceGetPciInfo(gpu_device).pciDeviceId
    elif (metric == 'temp'):
        return nvmlDeviceGetTemperature(gpu_device, NVML_TEMPERATURE_GPU)
    elif (metric == 'mem_total'):
        return int(nvmlDeviceGetMemoryInfo(gpu_device).total/(1024*1024))
    elif (metric == 'fb_memory'):
        return int(nvmlDeviceGetMemoryInfo(gpu_device).used/1048576)
    elif (metric == 'util'):
        return nvmlDeviceGetUtilizationRates(gpu_device).gpu
    elif (metric == 'mem_util'):
        return nvmlDeviceGetUtilizationRates(gpu_device).memory
    elif (metric == 'fan'):
        try:
            return nvmlDeviceGetFanSpeed(gpu_device)
        except NVMLError, nvmlError:
            # Not all GPUs have fans - a fatal error would not be appropriate
            if NVML_ERROR_NOT_SUPPORTED == nvmlError.value:
                return 0
    elif (metric == 'ecc_mode'):
        try:
            ecc_mode = nvmlDeviceGetPendingEccMode(gpu_device)
            if (NVML_FEATURE_DISABLED == ecc_mode):
                return "OFF"
            elif (NVML_FEATURE_ENABLED == ecc_mode):
                return "ON"
            else:
                return "UNKNOWN"
        except NVMLError, nvmlError:
            if NVML_ERROR_NOT_SUPPORTED == nvmlError.value:
                return 'N/A'
    elif (metric == 'perf_state' or metric == 'performance_state'):
        state = nvmlDeviceGetPerformanceState(gpu_device)
        try:
            int(state)
            return "P%s" % state
        except ValueError:
            return state
    elif (metric == 'graphics_clock_report'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_GRAPHICS)
    elif (metric == 'sm_clock_report'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_SM)
    elif (metric == 'mem_clock_report'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_MEM)
    elif (metric == 'max_graphics_clock'):
        return nvmlDeviceGetMaxClockInfo(gpu_device, NVML_CLOCK_GRAPHICS)
    elif (metric == 'max_sm_clock'):
        return nvmlDeviceGetMaxClockInfo(gpu_device, NVML_CLOCK_SM)
    elif (metric == 'max_mem_clock'):
        return nvmlDeviceGetMaxClockInfo(gpu_device, NVML_CLOCK_MEM)
    elif (metric == 'power_usage_report'):
        return nvmlDeviceGetPowerUsage(gpu_device)/1000
    elif (metric == 'serial'):
        return nvmlDeviceGetSerial(gpu_device)
    elif (metric == 'power_man_mode'):
        pow_man_mode = nvmlDeviceGetPowerManagementMode(gpu_device)
        if (NVML_FEATURE_DISABLED == pow_man_mode):
           return "OFF"
        elif (NVML_FEATURE_ENABLED == pow_man_mode):
           return "ON"
        else:
            return "UNKNOWN"
    elif (metric == 'power_man_limit'):
        powerLimit = nvmlDeviceGetPowerManagementLimit(gpu_device)
        return powerLimit/1000
    elif (metric == 'ecc_db_error'):
        eccCount =  nvmlDeviceGetTotalEccErrors(gpu_device, 1, 1) 
        return eccCount
    elif (metric == 'ecc_sb_error'):
        eccCount =  nvmlDeviceGetTotalEccErrors(gpu_device, 0, 1)
        return eccCount
    elif (metric == 'bar1_memory'):
	memory =  nvmlDeviceGetBAR1MemoryInfo(gpu_device)
        return int(memory.bar1Used/1000000)
    elif (metric == 'bar1_max_memory'):
        memory =  nvmlDeviceGetBAR1MemoryInfo(gpu_device)
        return int(memory.bar1Total/1000000)
    elif (metric == 'shutdown_temp'):
        return nvmlDeviceGetTemperatureThreshold(gpu_device,0)
    elif (metric == 'slowdown_temp'):
        return nvmlDeviceGetTemperatureThreshold(gpu_device,1)
    elif (metric == 'encoder_util'):
        return int(nvmlDeviceGetEncoderUtilization(gpu_device)[0])
    elif (metric == 'decoder_util'):
        return int(nvmlDeviceGetDecoderUtilization(gpu_device)[0])
    elif (metric == 'power_violation_report'):
       violationData = nvmlDeviceGetViolationStatus(gpu_device, 0)
       newTime = violationData.violationTime
       
       if (violation_dur[gpu_id] == 0):
          violation_dur[gpu_id] = newTime
      
       diff = newTime - violation_dur[gpu_id]
       # % calculation (diff/10)*100/10^9
       rate = diff / 100000000
       violation_dur[gpu_id] = newTime
       print rate
       return rate
    elif (metric == 'process'):
        procs = nvmlDeviceGetComputeRunningProcesses(gpu_device)
        return len(procs)
    else:
        print "Handler for %s not implemented, please fix in gpu_device_handler()" % metric
        os._exit(1)

def metric_init(params):
    global descriptors

    try:
        nvmlInit()
    except NVMLError, err:
        print "Failed to initialize NVML:", str(err)
        print "Exiting..."
        os._exit(1)

    default_time_max = 90

    build_descriptor('gpu_num', gpu_num_handler, default_time_max, 'uint', 'GPUs', 'zero', '%u', 'Total number of GPUs', 'gpu')
    build_descriptor('gpu_use_num', gpu_num_handler, default_time_max, 'uint', 'GPUs', 'zero', '%u', 'Total number of Use  GPUs', 'gpu')
    build_descriptor('gpu_driver', gpu_driver_version_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU Driver Version', 'gpu')

    for i in range(get_gpu_num()):
        build_descriptor('gpu%s_type' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Type' % i, 'gpu')
        build_descriptor('gpu%s_graphics_clock_report' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Graphics Clock' % i, 'gpu')
        build_descriptor('gpu%s_sm_clock_report' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s SM Clock' % i, 'gpu')
        build_descriptor('gpu%s_mem_clock_report' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Memory Clock' % i, 'gpu')
        build_descriptor('gpu%s_uuid' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s UUID' % i, 'gpu')
        build_descriptor('gpu%s_pci_id' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s PCI ID' % i, 'gpu')
        build_descriptor('gpu%s_temp' % i, gpu_device_handler, default_time_max, 'uint', 'C', 'both', '%u', 'Temperature of GPU %s' % i, 'gpu,temp')
        build_descriptor('gpu%s_mem_total' % i, gpu_device_handler, default_time_max, 'uint', 'MB', 'zero', '%u', 'GPU%s FB Memory Total' %i, 'gpu')
        build_descriptor('gpu%s_fb_memory' % i, gpu_device_handler, default_time_max, 'uint', 'MB', 'both', '%u', 'GPU%s FB Memory Used' %i, 'gpu')
        build_descriptor('gpu%s_ecc_mode' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s ECC Mode' %i, 'gpu')
        #build_descriptor('gpu%s_perf_state' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Performance State' %i, 'gpu')
        build_descriptor('gpu%s_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Utilization' %i, 'gpu')
        build_descriptor('gpu%s_mem_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Memory Utilization' %i, 'gpu')
        build_descriptor('gpu%s_fan' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Fan Speed' %i, 'gpu')
        build_descriptor('gpu%s_power_usage_report' % i, gpu_device_handler, default_time_max, 'uint', 'watts', 'both', '%u', 'GPU%s Power Usage' % i, 'gpu')

        # Added for version 2.285
        build_descriptor('gpu%s_max_graphics_clock' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'zero', '%u', 'GPU%s Max Graphics Clock' % i, 'gpu')
        build_descriptor('gpu%s_max_sm_clock' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'zero', '%u', 'GPU%s Max SM Clock' % i, 'gpu')
        build_descriptor('gpu%s_max_mem_clock' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'zero', '%u', 'GPU%s Max Memory Clock' % i, 'gpu')
        build_descriptor('gpu%s_serial' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Serial' % i, 'gpu')
        #build_descriptor('gpu%s_power_man_mode' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Power Management' % i, 'gpu')
        
        # Driver version 340.25
        build_descriptor('gpu%s_power_man_limit' % i, gpu_device_handler, default_time_max, 'uint', 'Watts', 'zero', '%u', 'GPU%s Power Management Limit' % i, 'gpu')
        build_descriptor('gpu%s_ecc_db_error' % i, gpu_device_handler, default_time_max, 'uint', 'No Of Errors', 'both', '%u', 'GPU%s ECC Report' % i, 'gpu')
        build_descriptor('gpu%s_ecc_sb_error' % i, gpu_device_handler, default_time_max, 'uint', 'No Of Errors', 'both', '%u', 'GPU%s Single Bit ECC' % i, 'gpu')
        build_descriptor('gpu%s_power_violation_report' % i, gpu_device_handler, default_time_max, 'uint', '', 'both', '%u', 'GPU%s Power Violation Report' % i, 'gpu')
        build_descriptor('gpu%s_bar1_memory' % i, gpu_device_handler, default_time_max, 'uint', 'MB', 'both', '%u', 'GPU%s Bar1 Memory Used' % i, 'gpu')
        build_descriptor('gpu%s_bar1_max_memory' % i, gpu_device_handler, default_time_max, 'uint', 'MB', 'zero', '%u', 'GPU%s Bar1 Memory Total' % i, 'gpu')
        build_descriptor('gpu%s_shutdown_temp' % i, gpu_device_handler, default_time_max, 'uint', 'C', 'zero', '%u', 'GPU%s Type' % i, 'gpu')
        build_descriptor('gpu%s_slowdown_temp' % i, gpu_device_handler, default_time_max, 'uint', 'C', 'zero', '%u', 'GPU%s Type' % i, 'gpu')
        build_descriptor('gpu%s_encoder_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Type' % i, 'gpu')
        build_descriptor('gpu%s_decoder_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Type' % i, 'gpu')
    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    try:
        nvmlShutdown()
    except NVMLError, err:
        print "Error shutting down NVML:", str(err)
        return 1

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        if d['value_type'] == 'uint':
            print 'value for %s is %u %s' % (d['name'], v, d['units'])
        elif d['value_type'] == 'float' or d['value_type'] == 'double':
            print 'value for %s is %f %s' % (d['name'], v, d['units'])
        elif d['value_type'] == 'string':
            print 'value for %s is %s %s' % (d['name'], v, d['units'])
    metric_cleanup()

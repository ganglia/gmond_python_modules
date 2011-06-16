# NVIDIA GPU metric module using the Python bindings for NVML
#
# (C)opyright 2011 Bernard Li <bernard@vanhpc.org>
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
from pynvml import *

descriptors = list()

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

def get_gpu_num():
    return int(nvmlDeviceGetCount())

def gpu_num_handler(name):
    return get_gpu_num()

def gpu_driver_version_handler(name):
    return nvmlSystemGetDriverVersion()

def gpu_device_handler(name):
    d = find_descriptor(name)

    (gpu, metric) = name.split('_', 1)
    gpu_id = int(gpu.split('gpu')[1])
    gpu_device = nvmlDeviceGetHandleByIndex(gpu_id)

    if (metric == 'type'):
        return nvmlDeviceGetName(gpu_device)
    elif (metric == 'uuid'):
        return nvmlDeviceGetUUID(gpu_device)
    elif (metric == 'pci_id'):
        return nvmlDeviceGetPciInfo(gpu_device).pciDeviceId
    elif (metric == 'temp'):
        return nvmlDeviceGetTemperature(gpu_device, NVML_TEMPERATURE_GPU)
    elif (metric == 'mem_total'):
        return int(nvmlDeviceGetMemoryInfo(gpu_device).total/1024)
    elif (metric == 'mem_used'):
        return int(nvmlDeviceGetMemoryInfo(gpu_device).used/1024)
    elif (metric == 'util'):
        return nvmlDeviceGetUtilizationRates(gpu_device).gpu
    elif (metric == 'mem_util'):
        return nvmlDeviceGetUtilizationRates(gpu_device).memory
    elif (metric == 'fan'):
        return nvmlDeviceGetFanSpeed(gpu_device)
    elif (metric == 'ecc_mode'):
        try:
            ecc_mode = nvmlDeviceGetPendingEccMode(gpu_device)
            if (ecc_mode == 0):
                return "OFF"
            elif (ecc_mode == 1):
                return "ON"
            else:
                return "UNKNOWN"
        except NVMLError, nvmlError:
            if NVML_ERROR_NOT_SUPPORTED == nvmlError.value:
                return 'N/A'
    elif (metric == 'power_state'):
        state = nvmlDeviceGetPowerState(gpu_device)
        try:
            int(state)
            return "P%s" % state
        except ValueError:
            return state
    elif (metric == 'graphics_speed'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_GRAPHICS)
    elif (metric == 'sm_speed'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_SM)
    elif (metric == 'mem_speed'):
        return nvmlDeviceGetClockInfo(gpu_device, NVML_CLOCK_MEM)
    elif (metric == 'power_usage'):
        return nvmlDeviceGetPowerUsage(gpu_device)
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
    build_descriptor('gpu_driver', gpu_driver_version_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU Driver Version', 'gpu')
 
    for i in range(get_gpu_num()):
        build_descriptor('gpu%s_type' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Type' % i, 'gpu')
        build_descriptor('gpu%s_graphics_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Graphics Speed' % i, 'gpu')
        build_descriptor('gpu%s_sm_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s SM Speed' % i, 'gpu')
        build_descriptor('gpu%s_mem_speed' % i, gpu_device_handler, default_time_max, 'uint', 'MHz', 'both', '%u', 'GPU%s Memory Speed' % i, 'gpu')
        build_descriptor('gpu%s_uuid' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s UUID' % i, 'gpu')
        build_descriptor('gpu%s_pci_id' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s PCI ID' % i, 'gpu')
        build_descriptor('gpu%s_temp' % i, gpu_device_handler, default_time_max, 'uint', 'C', 'both', '%u', 'Temperature of GPU %s' % i, 'gpu,temp')
        build_descriptor('gpu%s_mem_total' % i, gpu_device_handler, default_time_max, 'uint', 'KB', 'zero', '%u', 'GPU%s Total Memory' %i, 'gpu')
        build_descriptor('gpu%s_mem_used' % i, gpu_device_handler, default_time_max, 'uint', 'KB', 'both', '%u', 'GPU%s Used Memory' %i, 'gpu')
        build_descriptor('gpu%s_ecc_mode' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s ECC Mode' %i, 'gpu')
        build_descriptor('gpu%s_power_state' % i, gpu_device_handler, default_time_max, 'string', '', 'zero', '%s', 'GPU%s Power State' %i, 'gpu')
        build_descriptor('gpu%s_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Utilization' %i, 'gpu')
        build_descriptor('gpu%s_mem_util' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Memory Utilization' %i, 'gpu')
        build_descriptor('gpu%s_fan' % i, gpu_device_handler, default_time_max, 'uint', '%', 'both', '%u', 'GPU%s Fan Speed' %i, 'gpu')
        build_descriptor('gpu%s_power_usage' % i, gpu_device_handler, default_time_max, 'uint', 'watts', 'both', '%u', 'GPU%s Power Usage' % i, 'gpu')

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

#####
# Copyright (c) 2011-2012, NVIDIA Corporation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the NVIDIA Corporation nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
# THE POSSIBILITY OF SUCH DAMAGE.
#####

#
# nvidia_smi
# nvml_bindings <at> nvidia <dot> com
#
# Sample code that attempts to reproduce the output of nvidia-smi -q- x
# For many cases the output should match
#
# To Run:
# $ python
# Python 2.7 (r27:82500, Sep 16 2010, 18:02:00) 
# [GCC 4.5.1 20100907 (Red Hat 4.5.1-3)] on linux2
# Type "help", "copyright", "credits" or "license" for more information.
# >>> import nvidia_smi
# >>> print(nvidia_smi.XmlDeviceQuery())
# ...
#

from pynvml import *
import datetime

#
# Helper functions
#
def GetEccByType(handle, counterType, bitType):
    try:
        count = str(nvmlDeviceGetTotalEccErrors(handle, bitType, counterType))
    except NVMLError as err:
        count = handleError(err)
    
    try:
        detail = nvmlDeviceGetDetailedEccErrors(handle, bitType, counterType)
        deviceMemory = str(detail.deviceMemory)
        registerFile = str(detail.registerFile)
        l1Cache = str(detail.l1Cache)
        l2Cache = str(detail.l2Cache)
    except NVMLError as err:
        msg = handleError(err)
        deviceMemory = msg
        registerFile = msg
        l1Cache = msg
        l2Cache = msg
    strResult = ''
    strResult += '          <device_memory>' + deviceMemory + '</device_memory>\n'
    strResult += '          <register_file>' + registerFile + '</register_file>\n'
    strResult += '          <l1_cache>' + l1Cache + '</l1_cache>\n'
    strResult += '          <l2_cache>' + l2Cache + '</l2_cache>\n'
    strResult += '          <total>' + count + '</total>\n'
    return strResult

def GetEccByCounter(handle, counterType):
    strResult = ''
    strResult += '        <single_bit>\n'
    strResult += str(GetEccByType(handle, counterType, NVML_SINGLE_BIT_ECC))
    strResult += '        </single_bit>\n'
    strResult += '        <double_bit>\n'
    strResult += str(GetEccByType(handle, counterType, NVML_DOUBLE_BIT_ECC))
    strResult += '        </double_bit>\n'
    return strResult

def GetEccStr(handle):
    strResult = ''
    strResult += '      <volatile>\n'
    strResult += str(GetEccByCounter(handle, NVML_VOLATILE_ECC))
    strResult += '      </volatile>\n'
    strResult += '      <aggregate>\n'
    strResult += str(GetEccByCounter(handle, NVML_AGGREGATE_ECC))
    strResult += '      </aggregate>\n'
    return strResult

#
# Converts errors into string messages
#
def handleError(err):
    if (err.value == NVML_ERROR_NOT_SUPPORTED):
        return "N/A"
    else:
        return err.__str__()

#######
def XmlDeviceQuery():

    try:
        #
        # Initialize NVML
        #
        nvmlInit()
        strResult = ''

        strResult += '<?xml version="1.0" ?>\n'
        strResult += '<!DOCTYPE nvidia_smi_log SYSTEM "nvsmi_device.dtd">\n'
        strResult += '<nvidia_smi_log>\n'

        strResult += '  <timestamp>' + str(datetime.date.today()) + '</timestamp>\n'
        strResult += '  <driver_version>' + str(nvmlSystemGetDriverVersion()) + '</driver_version>\n'

        deviceCount = nvmlDeviceGetCount()
        strResult += '  <attached_gpus>' + str(deviceCount) + '</attached_gpus>\n'

        for i in range(0, deviceCount):
            handle = nvmlDeviceGetHandleByIndex(i)
            
            pciInfo = nvmlDeviceGetPciInfo(handle)    
            
            strResult += '  <gpu id="%s">\n' % pciInfo.busId
            
            strResult += '    <product_name>' + nvmlDeviceGetName(handle) + '</product_name>\n'
            
            try:
                state = ('Enabled' if (nvmlDeviceGetDisplayMode(handle) != 0) else 'Disabled')
            except NVMLError as err:
                state = handleError(err)
            
            strResult += '    <display_mode>' + state + '</display_mode>\n'

            try:
                mode = 'Enabled' if (nvmlDeviceGetPersistenceMode(handle) != 0) else 'Disabled'
            except NVMLError as err:
                mode = handleError(err)
            
            strResult += '    <persistence_mode>' + mode + '</persistence_mode>\n'
                
            strResult += '    <driver_model>\n'

            try:
                current = str(nvmlDeviceGetCurrentDriverModel(handle))
            except NVMLError as err:
                current = handleError(err)
            strResult += '      <current_dm>' + current + '</current_dm>\n'

            try:
                pending = str(nvmlDeviceGetPendingDriverModel(handle))
            except NVMLError as err:
                pending = handleError(err)

            strResult += '      <pending_dm>' + pending + '</pending_dm>\n'

            strResult += '    </driver_model>\n'

            try:
                serial = nvmlDeviceGetSerial(handle)
            except NVMLError as err:
                serial = handleError(err)

            strResult += '    <serial>' + serial + '</serial>\n'

            try:
                uuid = nvmlDeviceGetUUID(handle)
            except NVMLError as err:
                uuid = handleError(err)

            strResult += '    <uuid>' + uuid + '</uuid>\n'
            
            try:
                vbios = nvmlDeviceGetVbiosVersion(handle)
            except NVMLError as err:
                vbios = handleError(err)

            strResult += '    <vbios_version>' + vbios + '</vbios_version>\n'

            strResult += '    <inforom_version>\n'
            
            try:
                oem = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_OEM)
                if oem == '':
                    oem = 'N/A'
            except NVMLError as err:
                oem = handleError(err)
                
            strResult += '      <oem_object>' + oem + '</oem_object>\n'
            
            try:
                ecc = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_ECC)
                if ecc == '':
                    ecc = 'N/A'
            except NVMLError as err:
                ecc = handleError(err)
            
            strResult += '      <ecc_object>' + ecc + '</ecc_object>\n'
            try:
                pwr = nvmlDeviceGetInforomVersion(handle, NVML_INFOROM_POWER)
                if pwr == '':
                    pwr = 'N/A'
            except NVMLError as err:
                pwr = handleError(err)
            
            strResult += '      <pwr_object>' + pwr + '</pwr_object>\n'
            strResult += '    </inforom_version>\n'

            strResult += '    <pci>\n'
            strResult += '      <pci_bus>%02X</pci_bus>\n' % pciInfo.bus
            strResult += '      <pci_device>%02X</pci_device>\n' % pciInfo.device
            strResult += '      <pci_domain>%04X</pci_domain>\n' % pciInfo.domain
            strResult += '      <pci_device_id>%08X</pci_device_id>\n' % (pciInfo.pciDeviceId)
            strResult += '      <pci_sub_system_id>%08X</pci_sub_system_id>\n' % (pciInfo.pciSubSystemId)
            strResult += '      <pci_bus_id>' + str(pciInfo.busId) + '</pci_bus_id>\n'
            strResult += '      <pci_gpu_link_info>\n'


            strResult += '        <pcie_gen>\n'

            try:
                gen = str(nvmlDeviceGetMaxPcieLinkGeneration(handle))
            except NVMLError as err:
                gen = handleError(err)

            strResult += '          <max_link_gen>' + gen + '</max_link_gen>\n'

            try:
                gen = str(nvmlDeviceGetCurrPcieLinkGeneration(handle))
            except NVMLError as err:
                gen = handleError(err)

            strResult += '          <current_link_gen>' + gen + '</current_link_gen>\n'
            strResult += '        </pcie_gen>\n'
            strResult += '        <link_widths>\n'

            try:
                width = str(nvmlDeviceGetMaxPcieLinkWidth(handle)) + 'x'
            except NVMLError as err:
                width = handleError(err)

            strResult += '          <max_link_width>' + width + '</max_link_width>\n'

            try:
                width = str(nvmlDeviceGetCurrPcieLinkWidth(handle)) + 'x'
            except NVMLError as err:
                width = handleError(err)

            strResult += '          <current_link_width>' + width + '</current_link_width>\n'

            strResult += '        </link_widths>\n'
            strResult += '      </pci_gpu_link_info>\n'
            strResult += '    </pci>\n'

            try:
                fan = str(nvmlDeviceGetFanSpeed(handle)) + ' %'
            except NVMLError as err:
                fan = handleError(err)
            strResult += '    <fan_speed>' + fan + '</fan_speed>\n'

            try:
                memInfo = nvmlDeviceGetMemoryInfo(handle)
                mem_total = str(memInfo.total / 1024 / 1024) + ' MB'
                mem_used = str(memInfo.used / 1024 / 1024) + ' MB'
                mem_free = str(memInfo.free / 1024 / 1024) + ' MB'
            except NVMLError as err:
                error = handleError(err)
                mem_total = error
                mem_used = error
                mem_free = error

            strResult += '    <memory_usage>\n'
            strResult += '      <total>' + mem_total + '</total>\n'
            strResult += '      <used>' + mem_used + '</used>\n'
            strResult += '      <free>' + mem_free + '</free>\n'
            strResult += '    </memory_usage>\n'

            
            try:
                mode = nvmlDeviceGetComputeMode(handle)
                if mode == NVML_COMPUTEMODE_DEFAULT:
                    modeStr = 'Default'
                elif mode == NVML_COMPUTEMODE_EXCLUSIVE_THREAD:
                    modeStr = 'Exclusive Thread'
                elif mode == NVML_COMPUTEMODE_PROHIBITED:
                    modeStr = 'Prohibited'
                elif mode == NVML_COMPUTEMODE_EXCLUSIVE_PROCESS:
                    modeStr = 'Exclusive Process'
                else:
                    modeStr = 'Unknown'
            except NVMLError as err:
                modeStr = handleError(err)

            strResult += '    <compute_mode>' + modeStr + '</compute_mode>\n'

            try:
                util = nvmlDeviceGetUtilizationRates(handle)
                gpu_util = str(util.gpu)
                mem_util = str(util.memory)
            except NVMLError as err:
                error = handleError(err)
                gpu_util = error
                mem_util = error
            
            strResult += '    <utilization>\n'
            strResult += '      <gpu_util>' + gpu_util + ' %</gpu_util>\n'
            strResult += '      <memory_util>' + mem_util + ' %</memory_util>\n'
            strResult += '    </utilization>\n'
            
            try:
                (current, pending) = nvmlDeviceGetEccMode(handle)
                curr_str = 'Enabled' if (current != 0) else 'Disabled'
                pend_str = 'Enabled' if (pending != 0) else 'Disabled'
            except NVMLError as err:
                error = handleError(err)
                curr_str = error
                pend_str = error

            strResult += '    <ecc_mode>\n'
            strResult += '      <current_ecc>' + curr_str + '</current_ecc>\n'
            strResult += '      <pending_ecc>' + pend_str + '</pending_ecc>\n'
            strResult += '    </ecc_mode>\n'

            strResult += '    <ecc_errors>\n'
            strResult += GetEccStr(handle)
            strResult += '    </ecc_errors>\n'
            
            try:
                temp = str(nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)) + ' C'
            except NVMLError as err:
                temp = handleError(err)

            strResult += '    <temperature>\n'
            strResult += '      <gpu_temp>' + temp + '</gpu_temp>\n'
            strResult += '    </temperature>\n'

            strResult += '    <power_readings>\n'
            try:
                perfState = nvmlDeviceGetPowerState(handle)
            except NVMLError as err:
                perfState = handleError(err)
            strResult += '      <power_state>P%s</power_state>\n' % perfState
            try:
                powMan = nvmlDeviceGetPowerManagementMode(handle)
                powManStr = 'Supported' if powMan != 0 else 'N/A'
            except NVMLError as err:
                powManStr = handleError(err)
            strResult += '      <power_management>' + powManStr + '</power_management>\n'
            try:
                powDraw = (nvmlDeviceGetPowerUsage(handle) / 1000.0)
                powDrawStr = '%.2f W' % powDraw
            except NVMLError as err:
                powDrawStr = handleError(err)
            strResult += '      <power_draw>' + powDrawStr + '</power_draw>\n'
            try:
                powLimit = (nvmlDeviceGetPowerManagementLimit(handle) / 1000.0)
                powLimitStr = '%d W' % powLimit
            except NVMLError as err:
                powLimitStr = handleError(err)
            strResult += '      <power_limit>' + powLimitStr + '</power_limit>\n'
            strResult += '    </power_readings>\n'

            strResult += '    <clocks>\n'
            try:
                graphics = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS))
            except NVMLError as err:
                graphics = handleError(err)
            strResult += '      <graphics_clock>' +graphics + ' MHz</graphics_clock>\n'
            try:
                sm = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_SM))
            except NVMLError as err:
                sm = handleError(err)
            strResult += '      <sm_clock>' + sm + ' MHz</sm_clock>\n'
            try:
                mem = str(nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM))
            except NVMLError as err:
                mem = handleError(err)
            strResult += '      <mem_clock>' + mem + ' MHz</mem_clock>\n'
            strResult += '    </clocks>\n'

            strResult += '    <max_clocks>\n'
            try:
                graphics = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_GRAPHICS))
            except NVMLError as err:
                graphics = handleError(err)
            strResult += '      <graphics_clock>' + graphics + ' MHz</graphics_clock>\n'
            try:
                sm = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_SM))
            except NVMLError as err:
                sm = handleError(err)
            strResult += '      <sm_clock>' + sm + ' MHz</sm_clock>\n'
            try:
                mem = str(nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_MEM))
            except NVMLError as err:
                mem = handleError(err)
            strResult += '      <mem_clock>' + mem + ' MHz</mem_clock>\n'
            strResult += '    </max_clocks>\n'
            
            try:
                perfState = nvmlDeviceGetPowerState(handle)
                perfStateStr = 'P%s' % perfState
            except NVMLError as err:
                perfStateStr = handleError(err)
            strResult += '    <performance_state>' + perfStateStr + '</performance_state>\n'
            
            strResult += '    <compute_processes>\n'
            
            procstr = ""
            try:
                procs = nvmlDeviceGetComputeRunningProcesses(handle)
            except NVMLError as err:
                procs = []
                procstr = handleError(err)
             
            for p in procs:
                procstr += '    <process_info>\n'
                procstr += '      <pid>%d</pid>\n' % p.pid
                try:
                    name = str(nvmlSystemGetProcessName(p.pid))
                except NVMLError as err:
                    if (err.value == NVML_ERROR_NOT_FOUND):
                        # probably went away
                        continue
                    else:
                        name = handleError(err)
                procstr += '      <process_name>' + name + '</process_name>\n'
                procstr += '      <used_memory>\n'
                if (p.usedGpuMemory == None):
                    procstr += 'N\A'
                else:
                    procstr += '%d MB\n' % (p.usedGpuMemory / 1024 / 1024)
                procstr += '</used_memory>\n'
                procstr += '    </process_info>\n'
            
            strResult += procstr
            strResult += '    </compute_processes>\n'
            strResult += '  </gpu>\n'
            
        strResult += '</nvidia_smi_log>\n'
        
    except NVMLError as err:
        strResult += 'nvidia_smi.py: ' + err.__str__() + '\n'
    
    nvmlShutdown()
    
    return strResult


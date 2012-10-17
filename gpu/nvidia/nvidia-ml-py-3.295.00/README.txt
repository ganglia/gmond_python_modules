======
pyNVML
======

------------------------------------------------
Python bindings to the NVIDIA Management Library
------------------------------------------------

Provides a Python interface to GPU management and monitoring functions.

This is a wrapper around the NVML library.
For information about the NVML library, see the NVML developer page
http://developer.nvidia.com/nvidia-management-library-nvml

Download the latest package from:
http://pypi.python.org/pypi/nvidia-ml-py/

Note this file can be run with 'python -m doctest -v README.txt'
although the results are system dependent

REQUIRES
--------
Python 2.5, or an earlier version with the ctypes module.

INSTALLATION
------------
sudo python setup.py install

USAGE
-----

    >>> from pynvml import *
    >>> nvmlInit()
    >>> print "Driver Version:", nvmlSystemGetDriverVersion()
    Driver Version: 295.00
    >>> deviceCount = nvmlDeviceGetCount()
    >>> for i in range(deviceCount):
    ...     handle = nvmlDeviceGetHandleByIndex(i)
    ...     print "Device", i, ":", nvmlDeviceGetName(handle)
    ... 
    Device 0 : Tesla C2070
    
    >>> nvmlShutdown()

Additionally, see nvidia_smi.py.  A sample application.

FUNCTIONS
---------
Python methods wrap NVML functions, implemented in a C shared library.
Each function's use is the same with the following exceptions:

- Instead of returning error codes, failing error codes are raised as 
  Python exceptions.

    >>> try:
    ...     nvmlDeviceGetCount()
    ... except NVMLError as error:
    ...     print error
    ... 
    Uninitialized

- C function output parameters are returned from the corresponding
  Python function left to right.

::
    
    nvmlReturn_t nvmlDeviceGetEccMode(nvmlDevice_t device,
                                      nvmlEnableState_t *current,
                                      nvmlEnableState_t *pending);

    >>> nvmlInit()
    >>> handle = nvmlDeviceGetHandleByIndex(0)
    >>> (current, pending) = nvmlDeviceGetEccMode(handle)

- C structs are converted into Python classes.

::
    
    nvmlReturn_t DECLDIR nvmlDeviceGetMemoryInfo(nvmlDevice_t device,
                                                 nvmlMemory_t *memory);
    typedef struct nvmlMemory_st {
        unsigned long long total;
        unsigned long long free;
        unsigned long long used;
    } nvmlMemory_t;

    >>> info = nvmlDeviceGetMemoryInfo(handle)
    >>> print "Total memory:", info.total
    Total memory: 5636292608
    >>> print "Free memory:", info.free
    Free memory: 5578420224
    >>> print "Used memory:", info.used
    Used memory: 57872384

- Python handles string buffer creation.

::
    
    nvmlReturn_t nvmlSystemGetDriverVersion(char* version,
                                            unsigned int length);

    >>> version = nvmlSystemGetDriverVersion();
    >>> nvmlShutdown()

For usage information see the NVML documentation.

VARIABLES
---------
All meaningful NVML constants and enums are exposed in Python.

The NVML_VALUE_NOT_AVAILABLE constant is not used.  Instead None is mapped to the field.

RELEASE NOTES
-------------
Version 2.285.0
- Added new functions for NVML 2.285.  See NVML documentation for more information.
- Ported to support Python 3.0 and Python 2.0 syntax.
- Added nvidia_smi.py tool as a sample app.
Version 3.295.0
- Added new functions for NVML 3.295.  See NVML documentation for more information.
- Updated nvidia_smi.py tool
  - Includes additional error handling

COPYRIGHT
---------
Copyright (c) 2011-2012, NVIDIA Corporation.  All rights reserved.

LICENSE
-------
Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

- Neither the name of the NVIDIA Corporation nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


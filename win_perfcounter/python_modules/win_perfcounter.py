from __future__ import absolute_import
# TODO update winstats source code and return to the upstream project
# https://bitbucket.org/mixmastamyk/winstats/src/fa7a0b568a5c/winstats.py
import sys
import types

# TODO remove hardcoded True value
if True or sys.platform == 'cygwin':
    # This hack pretends that the posix-like ctypes provides windows
    # functionality. COM does not work with this hack.
    import ctypes
    ctypes.windll = ctypes.cdll
    ctypes.oledll = ctypes.cdll
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE
    ctypes.HRESULT = ctypes.c_long

    # http://epydoc.sourceforge.net/stdlib/ctypes.wintypes-module.html
    wintypes_module = types.ModuleType('wintypes'.encode('ascii'))
    wintypes_module.HANDLE = ctypes.c_ulong
    wintypes_module.LONG = ctypes.c_long
    wintypes_module.LPCSTR = ctypes.c_char_p
    wintypes_module.LPCWSTR = ctypes.c_wchar_p
    wintypes_module.DWORD = ctypes.c_ulong
    sys.modules['ctypes.wintypes'] = wintypes_module


from ctypes import byref
from ctypes import Structure, Union
from ctypes.wintypes import HANDLE, LONG, LPCSTR, LPCWSTR, DWORD


# PerfMon --------------------------------------------------------------------
HQUERY = HCOUNTER = HANDLE
pdh = ctypes.windll.pdh
PDH_FMT_RAW = 16L
PDH_FMT_ANSI = 32L
PDH_FMT_UNICODE = 64L
PDH_FMT_LONG = 256L
PDH_FMT_DOUBLE = 512L
PDH_FMT_LARGE = 1024L
PDH_FMT_1000 = 8192L
PDH_FMT_NODATA = 16384L
PDH_FMT_NOSCALE = 4096L

#~ dwType = DWORD(0)
_pdh_errcodes = {
    0x00000000: 'PDH_CSTATUS_VALID_DATA',
    0x800007d0: 'PDH_CSTATUS_NO_MACHINE',
    0x800007d2: 'PDH_MORE_DATA',
    0x800007d5: 'PDH_NO_DATA',
    0xc0000bb8: 'PDH_CSTATUS_NO_OBJECT',
    0xc0000bb9: 'PDH_CSTATUS_NO_COUNTER',
    0xc0000bbb: 'PDH_MEMORY_ALLOCATION_FAILURE',
    0xc0000bbc: 'PDH_INVALID_HANDLE',
    0xc0000bbd: 'PDH_INVALID_ARGUMENT',
    0xc0000bc0: 'PDH_CSTATUS_BAD_COUNTERNAME',
    0xc0000bc2: 'PDH_INSUFFICIENT_BUFFER',
    0xc0000bc6: 'PDH_INVALID_DATA',
    0xc0000bd3: 'PDH_NOT_IMPLEMENTED',
    0xc0000bd4: 'PDH_STRING_NOT_FOUND',
}


class PDH_Counter_Union(Union):
    _fields_ = [
        ('longValue', LONG),
        ('doubleValue', ctypes.c_double),
        ('largeValue', ctypes.c_longlong),
        ('ansiValue', LPCSTR),              # aka AnsiString...
        ('unicodeValue', LPCWSTR)           # aka WideString..
    ]


class PDH_FMT_COUNTERVALUE(Structure):
    _fields_ = [
        ('CStatus', DWORD),
        ('union', PDH_Counter_Union),
    ]


def get_pdherr(code):
    """Convert a PDH error code."""
    code &= 2 ** 32 - 1  # signed to unsigned :/
    return _pdh_errcodes.get(code, code)


def get_perfdata(counter_name, fmt='long', delay=0):
    """ Wrap up PerfMon's low-level API.

        Arguments:
            counter_name    Windows PerfMon counter name.
            fmt             One of 'long', 'double', 'large', 'ansi', 'unicode'
            delay           Some metrics need a delay to acquire (as int ms).
        Returns:
            requested Value
        Raises:
            WindowsError
    """
    counter_name = unicode(counter_name)
    FMT = globals().get('PDH_FMT_' + fmt.upper(), PDH_FMT_LONG)
    hQuery = HQUERY()
    hCounter = HCOUNTER()
    value = PDH_FMT_COUNTERVALUE()

    # Open Sie, bitte
    errs = pdh.PdhOpenQueryW(None, 0, byref(hQuery))
    if errs:
        raise OSError('PdhOpenQueryW failed: %s' % get_pdherr(errs))

    # Add Counter
    errs = pdh.PdhAddCounterW(hQuery, counter_name, 0, byref(hCounter))
    if errs:
        raise OSError('PdhAddCounterW failed: %s' % get_pdherr(errs))

    # Collect
    errs = pdh.PdhCollectQueryData(hQuery)
    if errs:
        raise OSError('PdhCollectQueryData failed: %s' % get_pdherr(errs))
    if delay:
        ctypes.windll.kernel32.Sleep(delay)
        errs = pdh.PdhCollectQueryData(hQuery)
        if errs:
            raise OSError(('PdhCollectQueryData failed: %s' %
                           get_pdherr(errs)))

    # Format  # byref(dwType), is optional
    errs = pdh.PdhGetFormattedCounterValue(hCounter, FMT, None, byref(value))
    if errs:
        raise OSError(('PdhGetFormattedCounterValue failed: %s' %
                       get_pdherr(errs)))

    # Close
    errs = pdh.PdhCloseQuery(hQuery)
    if errs:
        raise OSError('PdhCloseQuery failed: %s' % get_pdherr(errs))

    return getattr(value.union, fmt + 'Value')


def metric_handler(name):
    print('metric_handler_name: ' + name)


def metric_init(params):
    cpu_usage = get_perfdata('\Processor(_Total)\% Processor Time',
                             fmt='double', delay=100)
    print('cpu usage: ' + str(cpu_usage))

    disk_queue = get_perfdata('\LogicalDisk(_Total)\Current Disk Queue Length',
                              fmt='long', delay=100)
    print('disk_queue: ' + str(disk_queue))

    print('metric_init_params ' + str(params))


def metric_cleanup():
    pass
# InfiniBand metric module for Ganglia gmond
#
# Copyright 2015 Microway, Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVIES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import os
import subprocess
import time


# Dict containing the LIDs of InfiniBand devices in this system
IB_PORTS = {
    # '8':    'mlx4_0',
    # '234':  'scif0',
    # '888':  'qib0',
}

# Dict containing IB HCA devices and ports
IB_DEVS = {}

# Dict containing the most recent readings
METRICS = {
    'data': {}
}

# Dict containing the raw values from the previous reading
LAST_METRICS = {}

# Dict containing the full path to a /sys file for each individual metric
METRICS_FILES = {}

# Minimum number of seconds between reading updates (even if Ganglia calls more
# frequently). This is necessary since Ganglia will call us for each metric.
METRIC_UPDATE_INTERVAL = 2

IB_STATS_DIR = '/sys/class/infiniband'

IB_QUERY_UTILITY = 'perfquery'

# Dict of the currently-known InfiniBand metrics that come from the perfquery tool
KNOWN_PERFQUERY_METRICS = {
    # Note that this value is actually reported in 32-bit words (4 bytes)!
    'PortXmitData': {
        'name_prefix': 'ib_port_xmit_data',
        'units': 'bytes/sec',
        'description': 'Number of bytes transmitted per second',
    },

    # Note that this value is actually reported in 32-bit words (4 bytes)!
    'PortRcvData': {
        'name_prefix': 'ib_port_rcv_data',
        'units': 'bytes/sec',
        'description': 'Number of bytes received per second',
    },

    'PortXmitPkts': {
        'name_prefix': 'ib_port_xmit_packets',
        'units': 'pkts/sec',
        'description': 'Number of InfiniBand packets transmitted per second',
    },

    'PortRcvPkts': {
        'name_prefix': 'ib_port_rcv_packets',
        'units': 'pkts/sec',
        'description': 'Number of InfiniBand packets received per second',
    },

    'PortUnicastXmitPkts': {
        'name_prefix': 'ib_port_unicast_xmit_packets',
        'units': 'pkts/sec',
        'description': 'Number of UniCast packets transmitted per second',
    },

    'PortUnicastRcvPkts': {
        'name_prefix': 'ib_port_unicast_rcv_packets',
        'units': 'pkts/sec',
        'description': 'Number of UniCast packets received per second',
    },

    'PortMulticastXmitPkts': {
        'name_prefix': 'ib_port_multicast_xmit_packets',
        'units': 'pkts/sec',
        'description': 'Number of MultiCast packets transmitted per second',
    },

    'PortMulticastRcvPkts': {
        'name_prefix': 'ib_port_multicast_rcv_packets',
        'units': 'pkts/sec',
        'description': 'Number of MultiCast packets received per second',
    },
}


# Dict of the currently-known InfiniBand metrics that come from Linux sysfs.
#
# Note that some of the perfquery counters are also available via sysfs, but are
# only available as 32-bit counters (which very quickly overflow).
#
KNOWN_SYSFILE_METRICS = {
    'ib_excessive_buffer_overrun_errors': {
        'filename': 'counters/excessive_buffer_overrun_errors',
        'units': 'errors/sec',
        'description': 'Number of times that OverrunErrors consecutive flow control update periods occurred',
    },

    'ib_link_downed': {
        'filename': 'counters/link_downed',
        'units': 'errors/sec',
        'description': 'Number of times the link could not recover from an error',
    },

    'ib_link_error_recovery': {
        'filename': 'counters/link_error_recovery',
        'units': 'errors/sec',
        'description': 'Number of times the link has recovered from an error',
    },

    'ib_local_link_integrity_errors': {
        'filename': 'counters/local_link_integrity_errors',
        'units': 'errors/sec',
        'description': 'Number of times the count of local physical errors exceeded thresholds',
    },

    'ib_port_rcv_constraint_errors': {
        'filename': 'counters/port_rcv_constraint_errors',
        'units': 'pkts/sec',
        'description': 'Number of packets received on the switch physical port that are discarded',
    },

    'ib_port_rcv_errors': {
        'filename': 'counters/port_rcv_errors',
        'units': 'pkts/sec',
        'description': 'Number of packets that contained an error',
    },

    'ib_port_rcv_remote_physical_errors': {
        'filename': 'counters/port_rcv_remote_physical_errors',
        'units': 'pkts/sec',
        'description': 'Number of packets marked with the EBP (End of Bad Packet) delimiter',
    },

    'ib_port_rcv_switch_relay_errors': {
        'filename': 'counters/port_rcv_switch_relay_errors',
        'units': 'pkts/sec',
        'description': 'Number of packets which could not be forwarded through the switch',
    },

    'ib_port_xmit_constraint_errors': {
        'filename': 'counters/port_xmit_constraint_errors',
        'units': 'pkts/sec',
        'description': 'Number of packets not transmitted by the switch physical port',
    },

    'ib_port_xmit_discards': {
        'filename': 'counters/port_xmit_discards',
        'units': 'pkts/sec',
        'description': 'Number of outbound packets discarded because the port is down or congested',
    },

    'ib_symbol_error': {
        'filename': 'counters/symbol_error',
        'units': 'errors/sec',
        'description': 'Number of minor link errors detected at the physical layer',
    },

    'ib_vl15_dropped': {
        'filename': 'counters/VL15_dropped',
        'units': 'pkts/sec',
        'description': 'Number of incoming subnet management packets dropped due to buffer limits',
    },

    'ib_rate': {
        'filename': 'rate',
        'units': 'Gbps',
        'description': 'Current InfiniBand data rate (in gigabits per second)',
    },
}


def find_executable(program):
    """Look through the system's PATH looking for the specified executable

    Parameters
    ----------
        program: Name of the desired executable

    Returns
    -------
        Full path to the executable (if found) or None

    """
    def is_executable(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_executable(program):
            return program
    else:
        try:
            system_paths = os.environ["PATH"]
        except KeyError:
            # If no system path has been set, make a guess
            system_paths = "/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/sbin:/usr/local/bin"

        for path in system_paths.split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_executable(exe_file):
                return exe_file

    return None


def build_metric_definition(metric_overrides):
    """Build a metric definition using the specified parameters

    Metric definitions contain the following values:
    ------------------------------------------------
        name: Single-word name of the metric (often contains underscores)

        call_back: Function which returns the current value of this metric

        time_max: Maximum time allowed between updates of this metric (seconds)

        value_type: Data type of this metric (string, uint, float, double)

        units: String describing the unit of measure for this metric

        slope: (zero, positive, negative, both)
            Provide a hint of this metric's behavior (to allow more efficient
            storage of the values). This indicates the slope of the metric over
            its entire lifetime. 'zero' values never change; 'positive' and
            'negative' values go in one direction; 'both' indicates the value
            will go up and down.

        format: The string formatting for this metric (e.g., '%s', '%u', '%.0f')

        description: Human-readable description of this metric

        groups: String of comma-separated metric group names (e.g., 'cpu,load')

    Returns
    -------
        None _or_ A Dict containing the definition of a metric

    """
    metric_skeleton = {
        'name':        'XXXundefinedXXX',
        'call_back':   get_metric,
        'time_max':    60,
        'value_type':  'float',
        'units':       'XXXundefinedXXX',
        'slope':       'both',
        'format':      '%.1f',
        'description': 'XXXundefinedXXX',
        'groups':      'infiniband',
    }

    # Make a copy of the base metric dict and then apply any overrides
    metric = metric_skeleton.copy()
    for key, value in metric_overrides.iteritems():
        metric[key] = value

    return metric


def get_metric(name):
    """Return the current value for the named metric"""
    # Check if the metrics need to be updated
    update_metrics()
    if not name in METRICS['data']:
        print "ERROR metric: "+str(name)+" not found in dict METRICS"
        return False
    # Return the latest value for the desired metric
    return METRICS['data'][name]


def metric_init(params):
    """Initialize this metric-gathering module and build a list of metrics

    Parameters
    ----------
        params: Dict of configuration parameters for this module

    Returns
    -------
        List of metric definition Dicts

    """
    global IB_QUERY_UTILITY, IB_DEVS

    metric_definitions = []

    # If there are no InfiniBand devices (or we can't access them), return
    if not os.path.exists(IB_STATS_DIR):
        print("Unable to locate the InfiniBand entries in: %s" % IB_STATS_DIR)
        return metric_definitions

    # Ensure we will be able to execute the perfquery utility
    perfquery_path = find_executable(IB_QUERY_UTILITY)
    if perfquery_path:
        IB_QUERY_UTILITY = perfquery_path
    else:
        print("Unable to locate the InfiniBand utility: 'perfquery'")
        return metric_definitions

    # Loop through the InfiniBand devices on this system
    for ib_device in os.listdir(IB_STATS_DIR):
        # Loop through the InfiniBand ports on this device

        if not ib_device in IB_DEVS: IB_DEVS[ib_device]=[]

        ports_path = os.path.join(IB_STATS_DIR, ib_device, 'ports')
        for ib_port_number in os.listdir(ports_path):
            # Store the device information for this port
            sys_file_path = os.path.join(ports_path, ib_port_number)
            state_file = os.path.join(sys_file_path, 'state')
            link_layer_file = os.path.join(sys_file_path, 'link_layer')
            lid_file = os.path.join(sys_file_path, 'lid')

            try:
                with open(state_file) as f:
                    port_state = int(f.readline().split(' ')[0][0])
            except IOError:
                print("Unable to read IB port state from file: %s" % state_file)
            f.close()
            
            # check if port state is down
            if port_state == 1:
                continue ##skip rest of loop/ib_port_number

            try:
                with open(link_layer_file) as f:
                    port_link_layer = str(f.readline())
            except IOError:
                print("Unable to read IB link_layer from file: %s" % link_layer_file)
            f.close()

            # check if port state is down
            if 'InfiniBand' not in port_link_layer:
                continue ##skip rest of loop/ib_port_number
                
            try:
                with open(lid_file) as f:
                    # Linux sysfs lists the port_lid in hex
                    port_lid = int(f.readline().split(' ')[0], 0)
            except IOError:
                print("Unable to read IB port LID # from file: %s" % lid_file)
            f.close()

            # check if connected to fabric manager/subnet manager
            if port_lid == 0:
                continue ##skip rest of loop/ib_port_number

            # build Dict IB_DEVS
            if not ib_port_number in IB_DEVS[ib_device]: IB_DEVS[ib_device].append(ib_port_number)
            
            IB_PORTS[port_lid] = ib_device

            # Create definitions for the known perfquery InfiniBand metrics
            for metric_name, metric_settings in KNOWN_PERFQUERY_METRICS.iteritems():
                name_prefix = metric_settings['name_prefix']
                full_name = "%s_%s_port%s" % (name_prefix, ib_device, ib_port_number)

                # Create the definition using the specified settings
                overrides = metric_settings
                overrides['name'] = full_name
                overrides['ca_name'] = ib_device
                overrides['ca_port'] = ib_port_number
                metric_definitions.append(build_metric_definition(overrides))

            # Create definitions for the known sysfs InfiniBand metrics
            for metric_name, metric_settings in KNOWN_SYSFILE_METRICS.iteritems():
                full_name = "%s_%s_port%s" % (metric_name, ib_device, ib_port_number)

                # Store the full name of this metric's file name
                metric_file_name = metric_settings['filename']
                full_sys_file_path = os.path.join(sys_file_path, metric_file_name)
                METRICS_FILES[full_name] = full_sys_file_path

                # Create the definition using the specified settings
                overrides = metric_settings
                overrides['name'] = full_name
                metric_definitions.append(build_metric_definition(overrides))

    return metric_definitions


def metric_cleanup():
    """Clean up the metric module."""
    pass


def update_metrics():
    """If enough time has passed, update the metric values"""
    current_time = time.time()

    try:
        if(current_time - METRICS['time']) < METRIC_UPDATE_INTERVAL:
            # The last update happened recently. We don't need to update again.
            return
    except KeyError:
        # If updates have never been run, METRICS will be empty
        pass

    def process_metric_value(metric_name, counter_value):
        """This function will be called for each metric"""
        if metric_name.startswith('ib_rate'):
            METRICS['data'][metric_name] = counter_value
        else:
            # Calculate the change relative to the last update
            delta = 0.0
            last_value = 0.0
            try:
                last_value = LAST_METRICS[metric_name]

                # If a counter reset occurred previously, we could go negative
                if last_value > counter_value:
                    delta = counter_value
                else:
                    delta = counter_value - last_value

            except KeyError:
                # If LAST_METRICS has no value, this is our first time updating.
                # Rather than using the current value, we'll report zero; this
                # prevents the first reading from approaching Infinity...
                pass

            LAST_METRICS[metric_name] = counter_value

            # If this metric is one of the 32-bit data volume counters, we have
            # to adjust for the fact that we're reporting the value in bytes
            if metric_name.startswith(('ib_port_xmit_data','ib_port_rcv_data')):
                delta *= 4.0

            # Adjust this value so that we're measuring in values per second
            try:
                last_time = METRICS['time']
                measurement_interval = current_time - last_time
                METRICS['data'][metric_name] = delta / measurement_interval
            except KeyError:
                # If METRICS has no value, this is our first time updating
                METRICS['data'][metric_name] = delta

    # Loop through all the Linux sysfs InfiniBand counter files
    for metric_name, metric_file in METRICS_FILES.iteritems():
        counter_value = 0.0

        # Get the current value from the /sys file
        try:
            with open(metric_file) as f:
                counter_value = float(f.readline().split(' ')[0])
        except IOError:
            print("Unable to read metric file: %s" % metric_file)
        except KeyError:
            # If there is a parsing error, report 0
            print("Unable to read a numerical value from the InfiniBand counter in %s" % metric_file)

        if counter_value >= 4294967295:
            print("Of the 32-bit InfiniBand counters in /sys, only the error values are checked. These are unlikely to overflow (as that many errors would cause giant fabric explosions). However, that case has occurred on the following counter: %s" % metric_name)

        process_metric_value(metric_name, counter_value)

    ## Collect perfquery output for Infiniband devices and ports
    ib_query_output = str()
    for ibdev,plist in IB_DEVS.iteritems():
        for pn in plist:
            cmd_args = [IB_QUERY_UTILITY+" -x "+" -C "+str(ibdev)+" -P "+str(pn)]

            # Run an instance of perfquery and parse the results
            try:
                process = subprocess.Popen(cmd_args,stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
                [stdoutdata,stderrdata] = process.communicate()
                if stderrdata:
                    print 'ERROR command '+str(cmd_args)
                    print str(stderrdata)
                    return False

            except subprocess.CalledProcessError:
                print 'ERROR command: '+str(cmd_args)
                print str(stderrdata)
                return False

            ib_query_output = ib_query_output + stdoutdata


    current_lid = None
    current_port = None
    current_device = None

    ## split output into multilines (along line breaks)
    for line in ib_query_output.splitlines():
        # Each section header will tell us which port is being listed:
        #
        #     # Port extended counters: Lid 8 port 1 (CapMask: 0x1400)
        #
        if line.startswith('# Port extended counters'):
            try:
                current_lid = int(line.split()[5])
                current_port = line.split()[7]
            except KeyError, ValueError:
                print("Unable to read LID and port # details from InfiniBand perfquery")
                print str(line)
                break
            
            try:
                current_device = IB_PORTS[current_lid]
            except KeyError:
                print("Unable to reconcile the InfiniBand port LID number between Linux sysfs and the perfquery utility (%d)." % current_lid)
                break

        # Port select and counter select are not needed
        elif line.startswith(('PortSelect', 'CounterSelect')):
            pass

        # The remaining lines of each section will be port counters. E.g.:
        #
        #     PortRcvData:.....................2089265119334
        #
        else:
            counter_name = line.split(':')[0]
            
            try:
                counter_name_prefix = KNOWN_PERFQUERY_METRICS[counter_name]['name_prefix']
            except KeyError:
                print("An unknown InfiniBand counter was returned by perfquery: '%s'" % counter_name)
                continue

            try:
                counter_value = float(line.split('.')[-1])
            except KeyError, ValueError:
                # If there is a parsing error, report 0
                counter_value = 0
                print("Unable to read a value from InfiniBand counter %s" % counter_name)

            metric_name = "%s_%s_port%s" % (counter_name_prefix, current_device, current_port)
            process_metric_value(metric_name, counter_value)

    METRICS['time'] = current_time


##############################
# This module may be run as an executable when debugging
if __name__ == "__main__":
    params = {}
    metric_definitions = metric_init(params)

    num_metric_definitions = len(metric_definitions)
    print("\n%d metric definitions were detected:\n" % num_metric_definitions)
    for metric_id in range(0, num_metric_definitions):
        print(metric_definitions[metric_id]['name'])
    print("\n\n")

    while True:
        for metric in metric_definitions:
            metric_name = metric['name']
            metric_value_type = metric['value_type']
            metric_value = metric['call_back'](metric_name)
            metric_units = metric['units']

            if metric_value_type == 'uint':
                print('%-16u %-16s %-50s' % (
                    metric_value, metric_units, metric_name
                ))
            elif metric_value_type == 'float' or metric_value_type == 'double':
                print('%-16.1f %-16s %-50s' % (
                    metric_value, metric_units, metric_name
                ))
            elif metric_value_type == 'string':
                print('%-16s %-16s %-50s' % (
                    metric_value, metric_units, metric_name
                ))

        print('Current time: %s\n' % (
                METRICS['time']
            ))

        time.sleep(10)

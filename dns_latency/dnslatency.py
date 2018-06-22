# Script: dnslatency.py
# Author: Matty <matty91@gmail.com>
# Date: 10-05-2016
# Purpose:
#   DNS latency checking module written for Ganglia.
# Usage:
#   The dnslatency script takes one or more DNS strings similar
#   to the following as arguments:
#
#       google-public-dns-a.google.com google.com A
#
#   THe first argument is the DNS server to query, the second
#   argument is the record to request and the third argument
#   is the resource record type to request. The polling interval
#   is controlled by the .pyconf collect_every option.
# License: 
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.

import sys
import socket
import dns.resolver
from datetime import datetime
from timeit import default_timer as timer

DEBUG = 0

def lookup_failure(status_code, domain, name_server, dns_answer):
    """
       Routine to call if a DNS lookup fails.
    """
    if DEBUG:
        print "%s: Unable to resolve %s from %s at %s" % (status_code,
                                                          domain,
                                                          name_server,
                                                          str(datetime.now()))
        if dns_answer:
            dns_answer.response.to_text()


def resolve_name(name):
    """
        Convert a name to an IP address
    """
    try:
        ip_addr = socket.gethostbyname(name)
    except socket.herror:
        print "Unable to resolve " + name + " to an IP address"
        sys.exit(1)
    return ip_addr


def time_name_resolution(name_server, domain, rr_type):
    """
       Calculate the time it takes to resolve a domain name
    """
    dns_answer = None
    resolver = dns.resolver.Resolver()
    resolver.nameservers = name_server
    start_time = timer()

    try:
        dns_answer = resolver.query(domain, rr_type)
    except dns.resolver.NXDOMAIN:
        lookup_failure("NXDOMAIN", domain, name_server, dns_answer)
        return 60
    except dns.resolver.NoAnswer:
        lookup_failure("NOANSWER", domain, name_server, dns_answer)
        return 60
    except dns.exception.Timeout:
        lookup_failure("TIMEOUT", domain, name_server, dns_answer)
        return 60

    end_time = timer()
    return end_time - start_time


def query_handler(name):
    """
       Callback invoked by ganglia to ocollect metrics
    """
    name_servers = []
    _, dns_server_name, domain, rrec = name.split('_')
    name_servers.append(resolve_name(dns_server_name))
    resolution_time = time_name_resolution(name_servers, domain, rrec)

    if DEBUG:
        print "DNSINFO: Query handler variables:"
        print "  DNSINFO: DNS Server name " + dns_server_name
        print "  DNSINFO: DNS List ", name_servers
        print "  DNSINFO: DOmain: " + domain
        print "  DNSINFO: Record type: " + rrec
        print "  DNSINFO: Resolution time: ", resolution_time

    return resolution_time


def metric_init(params):
    """
       Initializes the Ganglia descriptor table
    """
    descriptors = []

    for _, values in params.items():
        dns_server_name, domain, rrec = values.split()

        desc = {
            'name': 'dnslatency_' + dns_server_name + '_' + domain + '_' + rrec,
            'call_back': query_handler,
            'time_max': 60,
            'value_type': 'double',
            'units': 'Query Time',
            'slope': 'both',
            'format': '%.4f',
            'description': 'DNS resolution time',
            'groups': 'dns_latency'
        }

        descriptors.append(desc)

    return descriptors


def metric_cleanup():
    """
       Function used to perform cleanup when ganglia exit()'s
    """
    pass


def main():
    """
       Code to test the script w/o involving ganglia
    """
    params = {
        'googlednsa_dns_resolution': 'google-public-dns-a.google.com prefetch.net A',
        'googlednsb_dns_resolution': 'google-public-dns-b.google.com google.prefetch.net A',
    }
    descriptors = metric_init(params)
    for desc in descriptors:
        latency = desc['call_back'](desc['name'])
        _, dns_server, domain, _ = desc['name'].split("_")
        print "It took %f to resolve %s on %s" % (latency, domain, dns_server)


if __name__ == "__main__":
    main()

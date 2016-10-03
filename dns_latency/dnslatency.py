""" DNS latency checking module written for Ganglia. """

import sys
import socket
import dns.resolver
from datetime import datetime
from timeit import default_timer as timer

DEBUG = 0
descriptors = []


def lookup_failure(status_code, domain, name_server, dns_answer):
    """
       Routine to call if a DNS lookup fails.
    """
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
    metric, dns_server_name, domain, rrec = name.split('_')
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
    for param_name, values in params.items():
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

def main():
    """
       Code to test the script w/o involving ganglia
    """
    params = {
        'googlednsa_dns_resolution': 'google-public-dns-a.google.com prefetch.net A'
        #'googlednsb_dns_resolution': 'google-public-dns-b.google.com google.prefetch.net A',
    }
    descriptors = metric_init(params)
    for desc in descriptors:
        latency = desc['call_back'](desc['name'])
        metric, dns_server, domain, rrec = desc['name'].split("_")
        print "It took %f to resolve %s on %s" % (latency, domain, dns_server)


if __name__ == "__main__":
    main()

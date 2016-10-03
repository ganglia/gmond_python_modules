# Ganglia DNS latency

Ganglia python plug-in to collect and graph DNS query response times

# Sample CLI ouput
<pre>
$ python dnslatency.py
It took 0.014626 to resolve google.com on google-public-dns-b.google.com
It took 0.017215 to resolve google.com on google-public-dns-a.google.com
</pre>
# Installation

Create a dnslatency.pyconf in /etc/ganglia/conf.d with one or more params similar to the following:
<pre>
param googledns_dns_resolution {
    # Format: SERVER_NAME<SPACE>NAME_TO_QUERY<SPACE>RECORD_TYPE
    #   value = "google-public-dns-a.google.com google.com A"
}
</pre>
Each param needs a unique name and the value should contain the name of the DNS server to query, a domain name and the type of record to check.

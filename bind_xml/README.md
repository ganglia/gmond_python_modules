## Overview

Provides statistics (memory use, query counts) using the xml
statistics from BIND versions >= 9.5.  Parsing of the xml is done
using [pybindxml](https://github.com/jforman/pybindxml).

BIND configuration to enable looks something like:

    statistics-channels {
        inet 127.0.0.1 port 8053 allow {127.0.0.1;};
    };

## System Dependencies

yum-rhel6: libxml2-devel libxslt-devel

pip: pybindxml beautifulsoup4 lxml

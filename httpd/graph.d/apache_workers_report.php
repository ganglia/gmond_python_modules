<?php

/* Pass in by reference! */
function graph_apache_workers_report ( &$rrdtool_graph ) {

    global $context,
           $hostname,
           $range,
           $rrd_dir,
           $size,
           $strip_domainname;

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'Apache Workers';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'workers';
    $rrdtool_graph['extras']         = '--rigid';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'busyWorkers'='${rrd_dir}/httpd_busy_workers.rrd':'sum':AVERAGE "
		."DEF:'idleWorkers'='${rrd_dir}/httpd_idle_workers.rrd':'sum':AVERAGE "
		."DEF:'maxClients'='${rrd_dir}/httpd_max_clients.rrd':'sum':AVERAGE "
		."DEF:'minSpareServers'='${rrd_dir}/httpd_min_spare_servers.rrd':'sum':AVERAGE "
		."DEF:'maxSpareServers'='${rrd_dir}/httpd_max_spare_servers.rrd':'sum':AVERAGE "
		."AREA:'busyWorkers'#47748B:'Busy Workers' "
		."STACK:'idleWorkers'#EEB78E:'Idle Workers' "
		."LINE:'0'#00000033:'':STACK "
		."LINE2:'maxClients'#FF0000:'Max Clients' "
		."LINE1:'minSpareServers'#FF0000aa:'Min Spare Servers' "
		."LINE1:'maxSpareServers'#FF0000aa:'Max Spare Servers' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

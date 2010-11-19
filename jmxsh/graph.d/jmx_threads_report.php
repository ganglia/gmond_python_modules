<?php

/* Pass in by reference! */
function graph_jmx_threads_report ( &$rrdtool_graph ) {

    global $context,
           $hostname,
           $graph_var,
           $range,
           $rrd_dir,
           $size,
           $strip_domainname;

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $jmx = $graph_var;
    $title = $jmx.' JMX Threads';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'threads';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'live'='${rrd_dir}/jmx_${jmx}_thread_count.rrd':'sum':AVERAGE "
		."DEF:'daemon'='${rrd_dir}/jmx_${jmx}_daemon_threads.rrd':'sum':AVERAGE "
		."LINE1:'live'#F19A2A:'Live' "
		."LINE1:'daemon'#20ABD9:'Daemon' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

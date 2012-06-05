<?php

/* Pass in by reference! */
function graph_jmx_sessions_report ( &$rrdtool_graph ) {

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
    $title = $jmx.' JMX Jetty Sessions';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;
	$rrdtool_graph['vertical-label'] = 'sessions';

	$series = "DEF:'sessions'='${rrd_dir}/jmx_${jmx}_sessions.rrd':'sum':AVERAGE "
		."AREA:'sessions'#ADCFF5:'' "
		."LINE2:'sessions'#000098:'${jmx}' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

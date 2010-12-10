<?php

/* Pass in by reference! */
function graph_jmx_heap_report ( &$rrdtool_graph ) {

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
    $title = $jmx.' JMX Heap';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'Bytes';
	$rrdtool_graph['extras']         = '--rigid --base 1024';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'heap'='${rrd_dir}/jmx_${jmx}_heap_committed.rrd':'sum':AVERAGE "
		."DEF:'used'='${rrd_dir}/jmx_${jmx}_heap_used.rrd':'sum':AVERAGE "
		."AREA:'heap'#F8DAB2:'' "
		."LINE2:'heap'#F19A2A:'Heap' "
		."AREA:'used'#CFF1FC:'' "
		."LINE2:'used'#20ABD9:'Used' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

<?php

/* Pass in by reference! */
function graph_diskstat_iotime_report ( &$rrdtool_graph ) {

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

    $disk = $graph_var;
    $title = $disk.' IO Time';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'ms';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'io'='${rrd_dir}/diskstat_${disk}_io_time.rrd':'sum':AVERAGE "
		."DEF:'weighted_io'='${rrd_dir}/diskstat_${disk}_weighted_io_time.rrd':'sum':AVERAGE "
		."LINE1:'io'#700004:'IO' "
		."LINE1:'weighted_io'#5D868C:'Weighted IO' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

<?php

/* Pass in by reference! */
function graph_diskstat_disktime_report ( &$rrdtool_graph ) {

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
    $title = $disk.' Time on Disk';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['vertical-label'] = 'ms';
	$rrdtool_graph['extras']         = '--rigid';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'read'='${rrd_dir}/diskstat_${disk}_read_time.rrd':'sum':AVERAGE "
		."DEF:'write'='${rrd_dir}/diskstat_${disk}_write_time.rrd':'sum':AVERAGE "
		."CDEF:'_write'=write,-1,* "
		."AREA:'read'#8F005C:'Reading' "
		."AREA:'_write'#002A97:'Writing' "
		."LINE1:'0'#00000066:'' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

<?php

/* Pass in by reference! */
function graph_diskstat_readwritekb_report ( &$rrdtool_graph ) {

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
    $title = $disk.' Data Transferred';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'Bytes/sec';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'readKBytes'='${rrd_dir}/diskstat_${disk}_read_kbytes_per_sec.rrd':'sum':AVERAGE "
		."DEF:'writeKBytes'='${rrd_dir}/diskstat_${disk}_write_kbytes_per_sec.rrd':'sum':AVERAGE "
		."CDEF:'read_bytes'=readKBytes,1024,* "
		."CDEF:'write_bytes'=writeKBytes,1024,* "
		."LINE1:'read_bytes'#700004:'Read' "
		."LINE1:'write_bytes'#5D868C:'Written' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

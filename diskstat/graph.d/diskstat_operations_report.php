<?php

/* Pass in by reference! */
function graph_diskstat_operations_report ( &$rrdtool_graph ) {

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
    $title = $disk.' Operations';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['vertical-label'] = 'ops';
    $rrdtool_graph['extras']         = '--rigid';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

	$series = "DEF:'reads'='${rrd_dir}/diskstat_${disk}_reads.rrd':'sum':AVERAGE "
		."DEF:'reads_merged'='${rrd_dir}/diskstat_${disk}_reads_merged.rrd':'sum':AVERAGE "
		."DEF:'writes'='${rrd_dir}/diskstat_${disk}_writes.rrd':'sum':AVERAGE "
		."DEF:'writes_merged'='${rrd_dir}/diskstat_${disk}_writes_merged.rrd':'sum':AVERAGE "
		."CDEF:'_writes'=writes,-1,* "
		."CDEF:'_writes_merged'=writes_merged,-1,* "
		."AREA:'reads'#FA6900:'Reads' "
		."STACK:'reads_merged'#F38630:'Reads Merged' "
		."AREA:'_writes'#69D2E7:'Writes' "
		."STACK:'_writes_merged'#A7DBD8:'Writes Merged' "
		."LINE1:'0'#00000066:'' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

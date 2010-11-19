<?php

/* Pass in by reference! */
function graph_jmx_ehcache_hitrate_report ( &$rrdtool_graph ) {

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
    $title = $jmx.' JMX Ehcache Hitrate';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;
	$rrdtool_graph['vertical-label'] = 'percent';

	$series = "DEF:'hit'='${rrd_dir}/jmx_game-ehcache_${jmx}_hit_count.rrd':'sum':AVERAGE "
		."DEF:'miss'='${rrd_dir}/jmx_game-ehcache_${jmx}_miss_count.rrd':'sum':AVERAGE "
		."CDEF:hitrate=hit,miss,+,0,LE,0,hit,hit,miss,+,/,100,*,IF "
		//."CDEF:hitrate=hit,hit,miss,+,/,100,* "
		."AREA:'hitrate'#CCFFBB:'' "
		."LINE2:'hitrate'#005A04:'${jmx} hitrate' "
	;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

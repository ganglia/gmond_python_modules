<?php

error_reporting(E_ALL);
ini_set("display_errors", 1);

/* Pass in by reference! */
function graph_gpu0_power_violation_report ( &$rrdtool_graph ) {

    global $context,
           $hostname,
           $mem_shared_color,
           $mem_cached_color,
           $mem_buffered_color,
           $mem_swapped_color,
           $mem_used_color,
           $cpu_num_color,
           $range,
           $rrd_dir,
           $size,
           $strip_domainname;

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'GPU0 SM Speed';
    if ($context != 'host') {
       //$rrdtool_graph['title'] = $title;
    } else {
       //$rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    //$rrdtool_graph['upper-limit']    = '300.0';
    $rrdtool_graph['vertical-label'] = '';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    
    $series = "DEF:'gpu_speed'='${rrd_dir}/gpu0_power_violation_report.rrd':'sum':AVERAGE "
             ."LINE2:gpu_speed#555555:'GPU0  Power Violation' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}


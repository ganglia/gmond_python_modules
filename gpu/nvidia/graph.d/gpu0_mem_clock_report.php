<?php

error_reporting(E_ALL);
ini_set("display_errors", 1);

/* Pass in by reference! */
function graph_gpu0_mem_clock_report ( &$rrdtool_graph ) {

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

    $title = 'GPU0 Memory Clock';
    if ($context != 'host') {
       //$rrdtool_graph['title'] = $title;
    } else {
       //$rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['upper-limit']    = '5000.0';
    $rrdtool_graph['vertical-label'] = 'MHz';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    
    $series = "DEF:'gpu_speed'='${rrd_dir}/gpu0_mem_clock_report.rrd':'sum':AVERAGE "
             ."DEF:gpu_max_clock=${rrd_dir}/gpu0_max_mem_clock.rrd:sum:AVERAGE "
             ."VDEF:max_speed=gpu_max_clock,MAXIMUM "
             ."LINE2:gpu_speed#555555:'GPU0 Memory Clock' "
             ."LINE2:gpu_max_clock#FF0000:'MAX Limit=' "
             ."GPRINT:max_speed:'%6.2lf MHz' "
             ."TEXTALIGN:left ";


    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}


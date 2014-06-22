<?php

error_reporting(E_ALL);
ini_set("display_errors", 1);

/* Pass in by reference! */
function graph_gpu0_mem_used_report ( &$rrdtool_graph ) {

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

    $title = 'GPU0 Memory Used';
    if ($context != 'host') {
       //$rrdtool_graph['title'] = $title;
    } else {
       //$rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['upper-limit']    = '100000.0';
    $rrdtool_graph['vertical-label'] = 'Memory Used';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    
    $series = "DEF:'gpu_test_report'='${rrd_dir}/gpu0_mem_used_report.rrd':'sum':AVERAGE "
             ."LINE2:gpu_test_report#FF0000:'Total ECC Errors' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

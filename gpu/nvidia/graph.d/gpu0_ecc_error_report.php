<?php

error_reporting(E_ALL);
ini_set("display_errors", 1);

/* Pass in by reference! */
function graph_gpu0_ecc_error_report ( &$rrdtool_graph ) {

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

    $title = 'GPU0 ECC Error';
    if ($context != 'host') {
       //$rrdtool_graph['title'] = $title;
    } else {
       //$rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    //$rrdtool_graph['upper-limit']    = '10.0';
    $rrdtool_graph['vertical-label'] = 'Number of Errors';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    
    $series = "DEF:'gpu_test_report'='${rrd_dir}/gpu0_ecc_error_report.rrd':'sum':AVERAGE "
             ."DEF:'ecc_sb'='${rrd_dir}/gpu0_ecc_sb_error.rrd':'sum':AVERAGE "
             ."LINE2:ecc_sb#808080:'Single Bit Aggregate ECC Errors' "
             ."LINE2:gpu_test_report#000000:'Double Bit Aggregate ECC Errors' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

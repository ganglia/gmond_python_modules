<?php

/* Pass in by reference! */
function graph_gpu_ecc_error_report ( &$rrdtool_graph ) {

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
    $dIndex = $rrdtool_graph["arguments"]["dindex"];    
    $title = 'GPU'.$dIndex.' ECC Error';
    $rrdtool_graph['title'] = $title;
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'Number of Errors';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    
    $series = "DEF:'ecc_db'='${rrd_dir}/gpu".$dIndex."_ecc_error_report.rrd':'sum':AVERAGE "
             ."DEF:'ecc_sb'='${rrd_dir}/gpu".$dIndex."_ecc_sb_error.rrd':'sum':AVERAGE "
             ."LINE2:ecc_sb#808080:'Single Bit Aggregate ECC Errors' "
             ."LINE2:ecc_db#000000:'Double Bit Aggregate ECC Errors' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

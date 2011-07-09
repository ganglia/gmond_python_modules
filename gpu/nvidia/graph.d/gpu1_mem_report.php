<?php

/* Pass in by reference! */
function graph_gpu1_mem_report ( &$rrdtool_graph ) {

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

    if (!file_exists("${rrd_dir}/gpu_num.rrd")) {
       return;
    }

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'GPU1 Memory';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'Bytes';
    $rrdtool_graph['extras']         = '--rigid --base 1024';

    $series = "DEF:'gpu_mem_total'='${rrd_dir}/gpu1_mem_total.rrd':'sum':AVERAGE "
        ."CDEF:'bgpu_mem_total'=gpu_mem_total,1024,* "
        ."DEF:'gpu_mem_used'='${rrd_dir}/gpu1_mem_used.rrd':'sum':AVERAGE "
        ."CDEF:'bgpu_mem_used'=gpu_mem_used,1024,* "
        ."AREA:'bgpu_mem_used'#$mem_used_color:'GPU Memory Used' ";

    $series .= "LINE2:'bgpu_mem_total'#$cpu_num_color:'Total GPU Memory' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

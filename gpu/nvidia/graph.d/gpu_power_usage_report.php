<?php

/* Pass in by reference! */
function graph_gpu_power_usage_report ( &$rrdtool_graph ) {

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
    $title = 'GPU'.$dIndex.' Power Usage';
    $rrdtool_graph['title'] = $title;
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'Watts';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
 
    $series = "DEF:'gpu_power_usage'='${rrd_dir}/gpu".$dIndex."_power_usage_report.rrd':'sum':AVERAGE "
              ."LINE2:'gpu_power_usage'#555555:'GPU".$dIndex."  Power Usage' "
              ."CDEF:user_pos=gpu_power_usage,0,INF,LIMIT "
                . "VDEF:user_last=user_pos,LAST "
                . "VDEF:user_min=user_pos,MINIMUM "
                . "VDEF:user_avg=user_pos,AVERAGE "
                . "VDEF:user_max=user_pos,MAXIMUM "
                . "GPRINT:'user_last':'  Now\:%5.0lf' "
                . "GPRINT:'user_min':' Min\:%5.0lf\\l' "
                . "GPRINT:'user_avg':' Avg\:%5.0lf' "
                . "GPRINT:'user_max':' Max\:%5.0lf\\l' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}


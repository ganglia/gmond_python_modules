<?php

/* Pass in by reference! */
function graph_gpu_mem_util_report ( &$rrdtool_graph ) {

    global $context,
           $hostname,
           $mem_cached_color,
           $mem_used_color,
           $mem_swapped_color,
           $cpu_num_color,
           $range,
           $rrd_dir,
           $size,
           $strip_domainname;

    if (!file_exists("${rrd_dir}/gpu_num.rrd")) {
       return;
    }

    if (!file_exists("${rrd_dir}/gpu0_mem_util.rrd")) {
       return;
    }

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'GPU Memory Utilization';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    #$rrdtool_graph['upper-limit']    = '100';
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'Percent';
    $rrdtool_graph['extras']         = '--rigid --base 1024';

    $color = array($mem_cached_color, $mem_used_color, $mem_swapped_color, $cpu_num_color);

    $gpu_count = exec("find ${rrd_dir}/gpu?_mem_util.rrd | wc -l");
    $series = '';
    foreach (range(0, $gpu_count-1) as $i) {
       $series .= "DEF:'gpu$i'='${rrd_dir}/gpu${i}_mem_util.rrd':'sum':AVERAGE ";
    }
    foreach (range(0, $gpu_count-1) as $i) {
       if ($i == 0) {
          $series .= "AREA:'gpu$i'#$color[$i]:'gpu$i' ";
       } else {
          $series .= "STACK:'gpu$i'#$color[$i]:'gpu$i' ";
       }
    }
    
    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

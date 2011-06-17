<?php

/* Pass in by reference! */
function graph_gpu_temp_report ( &$rrdtool_graph ) {
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

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'GPU Temperature';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'C';
    $rrdtool_graph['extras']         = '--rigid --base 1024';

    $color = array($mem_cached_color, $mem_used_color, $mem_swapped_color, $cpu_num_color);

    $gpu_count = exec("find ${rrd_dir}/gpu?_temp.rrd | wc -l");
    $series = '';
    foreach (range(0, $gpu_count-1) as $i) {
       $series .= "DEF:'gpu$i'='${rrd_dir}/gpu${i}_temp.rrd':'sum':AVERAGE ";
    }
    foreach (range(0, $gpu_count-1) as $i) {
       $series .= "LINE2:'gpu$i'#$color[$i]:'gpu$i' ";
    }
    
    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

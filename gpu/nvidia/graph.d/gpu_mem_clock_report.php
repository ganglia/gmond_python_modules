<?php

/* Pass in by reference! */
function graph_gpu_mem_clock_report ( &$rrdtool_graph ) {

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
    $title = 'GPU'.$dIndex.' Memory Clock';
    $rrdtool_graph['title'] = $title;
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['upper-limit']    = '5000.0';
    $rrdtool_graph['vertical-label'] = 'MHz';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
    
    //for max line dot style
    include_once __DIR__."/gpu_common.php";
    list($range, $mod) =  calculate_mod_range($range);
   
    $series = "DEF:'gpu_mem_clock'='${rrd_dir}/gpu".$dIndex."_mem_clock_report.rrd':'sum':AVERAGE "
             ."DEF:gpu_mem_max_clock=${rrd_dir}/gpu".$dIndex."_max_mem_clock.rrd:sum:AVERAGE "
             ."DEF:temp=${rrd_dir}/gpu".$dIndex."_max_mem_clock.rrd:sum:AVERAGE "
             ."VDEF:max_clock=gpu_mem_max_clock,MAXIMUM "
             ."CDEF:dash_value=temp,POP,TIME,$range,%,$mod,LE,temp,UNKN,IF "
             ."LINE2:dash_value#FF0000:'MAX Limit=' "
             ."GPRINT:max_clock:'%6.2lf MHz' "
             ."TEXTALIGN:left "
             ."LINE2:'gpu_mem_clock'#555555:'GPU".$dIndex." Memory Clock' "
             ."CDEF:user_pos=gpu_mem_clock,0,INF,LIMIT "
                . "VDEF:user_last=user_pos,LAST "
                . "VDEF:user_min=user_pos,MINIMUM "
                . "VDEF:user_avg=user_pos,AVERAGE "
                . "VDEF:user_max=user_pos,MAXIMUM "
                . "GPRINT:'user_last':' Now\:%5.0lf\\l' "
                . "GPRINT:'user_min':' Min\:%5.0lfl' "
                . "GPRINT:'user_avg':' Avg\:%5.0lf' "
                . "GPRINT:'user_max':' Max\:%5.0lf\\l' ";


    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}


<?php
/* Pass in by reference! */
function graph_gpu_graphics_clock_report ( &$rrdtool_graph ) {

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
    $title = 'GPU'.$dIndex.' Graphics Clock';
    $rrdtool_graph['title'] = $title;
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['upper-limit']    = '1000.0';
    $rrdtool_graph['vertical-label'] = 'MHz';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
      
       //for max line dot style
    include_once __DIR__."/gpu_common.php";
    list($range, $mod) =  calculate_mod_range($range);

    $series = "DEF:'gpu_speed'='${rrd_dir}/gpu".$dIndex."_graphics_clock_report.rrd':'sum':AVERAGE "
             ."DEF:gpu_max_speed=${rrd_dir}/gpu".$dIndex."_max_graphics_clock.rrd:sum:AVERAGE "
             ."DEF:temp=${rrd_dir}/gpu".$dIndex."_max_graphics_clock.rrd:sum:AVERAGE "
             ."VDEF:max_speed=gpu_max_speed,MAXIMUM "
             ."CDEF:dash_value=temp,POP,TIME,$range,%,$mod,LE,temp,UNKN,IF "
             ."LINE2:dash_value#FF0000:'MAX Limit=' "
             ."GPRINT:max_speed:'%6.2lf MHz' "
             ."TEXTALIGN:left "
             ."LINE2:'gpu_speed'#555555:'GPU".$dIndex." Graphics Clock' "
	     ."CDEF:user_pos=gpu_speed,0,INF,LIMIT "
                . "VDEF:user_last=user_pos,LAST "
                . "VDEF:user_min=user_pos,MINIMUM "
                . "VDEF:user_avg=user_pos,AVERAGE "
                . "VDEF:user_max=user_pos,MAXIMUM "
                . "GPRINT:'user_last':' Now\:%5.1lf' "
                . "GPRINT:'user_min':' Min\:%5.1lf' "
                . "GPRINT:'user_avg':' Avg\:%5.1lf' "
                . "GPRINT:'user_max':' Max\:%5.1lf\\l' ";

    $rrdtool_graph['series'] = $series;
    return $rrdtool_graph;

}


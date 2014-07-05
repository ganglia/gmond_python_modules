<?php

error_reporting(E_ALL);
ini_set("display_errors", 1);

/* Pass in by reference! */
function graph_gpu0_graphics_clock_report ( &$rrdtool_graph ) {

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

    $title = 'GPU0 Graphics Clock';
    if ($context != 'host') {
       //$rrdtool_graph['title'] = $title;
    } else {
       //$rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['upper-limit']    = '1000.0';
    $rrdtool_graph['vertical-label'] = 'MHz';
    $rrdtool_graph['extras']         = '--rigid --base 1024';
      
    switch($range)
    {
	case "hour":
	   $range = 30;break;
        case "2hr":
           $range = 60;break;
        case "4hr":
           $range = 120;break;
        case "day":
           $range = 720;break;
        case "week":
           $range = 3600;break;
        case "month":
           $range = 6000;break;
        case "year":
           $range = 50000;break;
        default:
           $range = 30;
    }
    $mod = $range/3; 
      
    $series = "DEF:'gpu_speed'='${rrd_dir}/gpu0_graphics_clock_report.rrd':'sum':AVERAGE "
             ."DEF:gpu_max_speed=${rrd_dir}/gpu0_max_graphics_clock.rrd:sum:AVERAGE "
             ."DEF:temp=${rrd_dir}/gpu0_max_graphics_clock.rrd:sum:AVERAGE "
             ."VDEF:max_speed=gpu_max_speed,MAXIMUM "
             ."CDEF:temp1=temp,POP,TIME,$range,%,$mod,LE,temp,UNKN,IF "
             //."CDEF:rcount1=rcount,0,LE,UNKN,rcount,IF " 
             //."LINE2:gpu_speed#555555:'GPU0 Graphics Clock' "
             ."LINE2:temp1#FF0000:'MAX Limit=' "
             //."LINE2:gpu_max_speed#FF0000:'MAX Limit=' "
             ."GPRINT:max_speed:'%6.2lf MHz' "
             //."LINE2:gpu_speed#555555:'GPU0 Graphics Speed' ";
             ."TEXTALIGN:left "
             ."LINE2:gpu_speed#555555:'GPU0 Graphics Clock' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}


<?php
/*
 * Graphs take from the mysql-cacti-templates project:
 * http://code.google.com/p/mysql-cacti-templates/wiki/NginxTemplates
 */

/* Pass in by reference! */
function graph_nginx_scoreboard_report ( &$rrdtool_graph ) {

    global $context,
           $hostname,
           $range,
           $rrd_dir,
           $size,
           $strip_domainname;

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'Nginx Scoreboard';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['vertical-label'] = 'requests/sec';
    $rrdtool_graph['extras']         = '--rigid';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

    $series =
        "DEF:'active'='${rrd_dir}/nginx_active_connections.rrd':'sum':AVERAGE "
        ."DEF:'reading'='${rrd_dir}/nginx_reading.rrd':'sum':AVERAGE "
        ."DEF:'writing'='${rrd_dir}/nginx_writing.rrd':'sum':AVERAGE "
        ."DEF:'waiting'='${rrd_dir}/nginx_waiting.rrd':'sum':AVERAGE "
        ."AREA:'reading'#D1642E:'Reading' "
        ."STACK:'writing'#850707:'Writing' "
        ."STACK:'waiting'#487860:'Waiting' "
        ."LINE1:'active'#000000:'Active' "
    ;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

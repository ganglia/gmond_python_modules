<?php
/*
 * Graphs take from the mysql-cacti-templates project:
 * http://code.google.com/p/mysql-cacti-templates/wiki/NginxTemplates
 */

/* Pass in by reference! */
function graph_nginx_accepts_ratio_report ( &$rrdtool_graph ) {

    global $context,
           $hostname,
           $range,
           $rrd_dir,
           $size,
           $strip_domainname;

    if ($strip_domainname) {
       $hostname = strip_domainname($hostname);
    }

    $title = 'Nginx Accepts Ratio';
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['extras']         = '--rigid';
    $rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;

    $series =
        "DEF:'accepts'='${rrd_dir}/nginx_accepts.rrd':'sum':AVERAGE "
        ."DEF:'handled'='${rrd_dir}/nginx_handled.rrd':'sum':AVERAGE "
        ."DEF:'requests'='${rrd_dir}/nginx_requests.rrd':'sum':AVERAGE "
        ."CDEF:'handled_ratio'='accepts,handled,/' "
        ."CDEF:'requests_ratio'='requests,accepts,/' "
        ."LINE2:'handled_ratio'#850707:'Accepted / Handled' "
        ."LINE2:'requests_ratio'#D1642E:'Requests / Accepted' "
    ;

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}

?>

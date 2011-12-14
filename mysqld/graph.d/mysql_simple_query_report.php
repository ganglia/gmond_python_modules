<?php

/* Pass in by reference! */
function graph_mysql_simple_query_report ( &$rrdtool_graph ) {

	global $context,
		$hostname,
		$range,
		$rrd_dir,
		$size,
		$strip_domainname;

	if ($strip_domainname) {
		$hostname = strip_domainname($hostname);
	}

	$title = 'Mysql Query Report';
	if ($context != 'host') {
		$rrdtool_graph['title'] = $title;
	} else {
		$rrdtool_graph['title'] = "$hostname $title last $range";
	}

	$rrdtool_graph['lower-limit']    = '0';
	$rrdtool_graph['extras']         = '--rigid';
	$rrdtool_graph['height'] += ($size == 'medium') ? 28 : 0;
	$series = "DEF:'questions'='${rrd_dir}/mysql_questions.rrd':'sum':AVERAGE "
		."DEF:'select'='${rrd_dir}/mysql_com_select.rrd':'sum':AVERAGE "
		."DEF:'insert'='${rrd_dir}/mysql_com_insert.rrd':'sum':AVERAGE "
		."DEF:'update'='${rrd_dir}/mysql_com_update.rrd':'sum':AVERAGE "
		."DEF:'delete'='${rrd_dir}/mysql_com_delete.rrd':'sum':AVERAGE "
		."AREA:'questions'#CCCCCC:'Questions' "
		."AREA:'select'#0000FF:'Select' "
		."STACK:'delete'#FF0000:'Delete' "
		."STACK:'insert'#00FFFF:'Insert' "
		."STACK:'update'#FF00FF:'Update' "
		."LINE:'questions'#00000033:'' "
		;

	$rrdtool_graph['series'] = $series;

	return $rrdtool_graph;
}


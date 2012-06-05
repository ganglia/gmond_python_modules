<?php
/* Pass in by reference! */
function graph_apache_status_report ( &$rrdtool_graph ) {

  global $context,
         $hostname,
         $range,
         $rrd_dir,
         $size;

  # Unique colors
  $color_array = array("#3366FF",
                       "#33FF66",
                       "#BB9933",
                       "#FF3366",
                       "#FFFF00",
                       "#00FF00",
                       "#AA0000",
                       "#FFFFAA",
                       "#FF33CC",
                       "#FF0000",
                       "#CC0000");
  $metric_array = array("ap_open_slot",
                        "ap_waiting",
                        "ap_reading_request",
                        "ap_sending_reply",
                        "ap_keepalive",
                        "ap_dns_lookup",
                        "ap_logging",
                        "ap_closing",
                        "ap_starting",
                        "ap_gracefully_fin",
                        "ap_idle");

  $title = "apache status $hostname";
  if ($context != 'host') {
    $rrdtool_graph['title'] = $title;
  } else {
    $rrdtool_graph['title'] = "$title last $range";
  }

  $rrdtool_graph['lower-limit']    = '0';
  $rrdtool_graph['vertical-label'] = 'connections';
  $rrdtool_graph['extras']         = '--slope-mode';

  # Initialize some of the RRDtool components
  $rrd_defs = "";
  $rrd_graphs = "";
  $rrd_legend = "";
  $counter = 0;
  for ( $i = 0 ; $i < sizeof($metric_array); $i++ ) {
    # Need index for generating RRD labels
    $index = chr($counter + 97);
    $rrd_file =  $rrd_dir . "/" . $metric_array[$i] . ".rrd";
    if ( file_exists($rrd_file)) {
      $rrd_defs .= "DEF:" . $index . "='" . $rrd_file . "':'sum':AVERAGE ";
      $rrd_graphs .= "CDEF:n" . $index . "=" . $index . ",UN,0," . $index . ",IF ";
      ##################################################################################
      if ( $counter == 0) {
        $rrd_legend .= "AREA:" . $index . $color_array[$counter] . "91" . ":'" . $metric_array[$i] . "' ";
      } else {
        $rrd_legend .= "STACK:" . $index . $color_array[$counter] . "91" . ":'" . $metric_array[$i] . "' ";
      }
      if ($size == 'large') {
        $rrd_legend .= "VDEF:n" . $index . "_max" . "=" . $index . ",MAXIMUM ";
        $rrd_legend .= "GPRINT:n" . $index . "_max" . ":" . '"Max\:%6.0lf" ';
        $rrd_legend .= "VDEF:n" . $index . "_min" . "=" . $index . ",MINIMUM ";
        $rrd_legend .= "GPRINT:n" . $index . "_min" . ":" . '"Min\:%6.0lf" ';
        $rrd_legend .= "VDEF:n" . $index . "_avg" . "=" . $index . ",AVERAGE ";
        $rrd_legend .= "GPRINT:n" . $index . "_avg" . ":" . '"Avg\:%6.0lf" ';
        $rrd_legend .= "VDEF:n" . $index . "_last" . "=" . $index . ",LAST ";
	    # Can't figure out an easy way to line up the legend
        $rrd_legend .= "GPRINT:n" . $index . "_last" . ":" .'"Now\:%6.0lf                                                \r" ';
      }
      $counter++;
    }
  }

  $rrdtool_graph['series'] = $rrd_defs . $rrd_graphs . $rrd_legend;
  return $rrdtool_graph;
}
?>

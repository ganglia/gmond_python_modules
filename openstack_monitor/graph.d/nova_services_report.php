<?php
/*
 * Copyright 2011 GridDynamics
 * All Rights Reserved.
 *
 *    Licensed under the Apache License, Version 2.0 (the "License"); you may
 *    not use this file except in compliance with the License. You may obtain
 *    a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *    License for the specific language governing permissions and limitations
 *    under the License.
 */

/* Pass in by reference! */
function graph_nova_services_report ( &$rrdtool_graph ) {

    global $context, 
           $hostname,
           $cpu_num_color,
           $mem_used_color,
           $range,
           $rrd_dir,
           $size;

    $title = 'Openstack Nova services'; 
    if ($context != 'host') {
       $rrdtool_graph['title'] = $title;
    } else {
       $rrdtool_graph['title'] = "$hostname $title last $range";
    }
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['extras']         = '--rigid';

    $series = "DEF:'nova_running_services'='${rrd_dir}/nova_running_services.rrd':'sum':AVERAGE "
       ."DEF:'nova_registered_services'='${rrd_dir}/nova_registered_services.rrd':'sum':AVERAGE "
       ."AREA:'nova_running_services'#$cpu_num_color:'Running' "
       ."LINE2:'nova_registered_services'#$mem_used_color:'Registered' ";

    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;

}


?>
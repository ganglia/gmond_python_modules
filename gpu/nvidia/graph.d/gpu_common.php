<?php

/*
Calculate range and modulus value for dot structured graph
*/
function calculate_mod_range($range_str)
{
   switch($range_str)
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

    return array($range, $mod);
}

<?php

list($temp_hh, $temp_mm) = explode(':', date('P'));
$gmt_offset_server = $temp_hh + $temp_mm / 60;

$mtime = filemtime("reservations");
$mtime = $mtime - $gmt_offset_server * 3600;

echo "<!-- edit note -->Last fiddled with by RKN-Bot on ".date("d M y", $mtime)." at <span class=\"time\">".date("H:i", $mtime)."</span>\n";

echo "<pre><b>   Seq  Who             Index  Size  </b>\n";

echo file_get_contents("reservations");

echo "</pre>";
?>

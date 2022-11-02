function pub()
{
    var ajaxDelay = 1000;
    setInterval(function(){
            // Refresh details.
    var jqxhr = $.get( "umbral_2_val", function(data) {
    	alert(data)
	 	document.getElementById("umbral_2_value").innerHTML = data;
	});    

    }, ajaxDelay);
}
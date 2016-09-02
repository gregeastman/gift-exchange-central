function confirm_deletion(event_key) 
{
	if (confirm("Are you sure you want to delete the event?"))
	{
		$.ajax({
	          type: "POST",
	          url: "/admin/delete/" + event_key,
	          dataType: "json",
	          data: JSON.stringify(
	        	{ 
	        	  //"event": event_key
	          })
	        })
	        .done(function( data ) {
	        	window.location.replace("/admin/");
	        });
		
	}
}
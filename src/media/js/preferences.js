function update_preferences()
{
	var subscribed_string = "no";
	if (chk_is_subscribed.checked == 1)
	{
		subscribed_string = "yes";
	}
    $.ajax({
      type: "POST",
      url: "/preferences",
      dataType: "json",
      data: JSON.stringify({ 
    	  "subscribed_string": subscribed_string,
    	  "name": $("#txt_name").val(),
    	  "lastname": $("#txt_lastname").val(),
    	  "email": $("#txt_email").val()
      })
    })
    .done(function( data ) {
    	if (data["message"])
    	{
    		$("#span_error_message").text(data["message"]);
    		$("#div_error").show();
    	}
    	else
    	{
    		$("#div_error").hide();
    		set_temporary_message("#span_status_message", "Preferences updated successfully.")
    	}
    	
    });
}

function link_google()
{
	$.ajax({
	      type: "POST",
	      url: "/link",
	      dataType: "json",
	      data: JSON.stringify({ "type": "link"})
	    })
	    .done(function( data ) {
	    	if (data["message"])
	    	{
	    		$("#span_error_message").text(data["message"]);
	    		$("#div_error").show();
	    	}
	    	else 
	    	{
	    		window.location.replace("/preferences");
	    	}
	    });
}

function unlink_google()
{
	$.ajax({
	      type: "POST",
	      url: "/link",
	      dataType: "json",
	      data: JSON.stringify({ "type": "unlink"})
	    })
	    .done(function( data ) {
	    	if (data["message"])
	    	{
	    		$("#span_error_message").text(data["message"]);
	    		$("#div_error").show();
	    	}
	    	else 
	    	{
	    		window.location.replace("/preferences");
	    	}
	    });
}
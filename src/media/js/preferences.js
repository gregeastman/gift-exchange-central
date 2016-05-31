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
      data: JSON.stringify({ "subscribed_string": subscribed_string})
    })
    .done(function( data ) {
    	set_temporary_message("#span_status_message", data["message"])
    });
}


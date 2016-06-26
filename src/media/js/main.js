function update_ideas()
{
	$.ajax({
        type: "POST",
        url: "/update",
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  "gift_exchange_participant": $("#txt_gift_exchange_participant").val(),
      	  "ideas": $("#txt_ideas").val()
        })
      })
      .done(function( data ) {
    	  set_temporary_message("#span_status_message", data["message"])
      });
}

function get_assignment()
{
	$.ajax({
        type: "POST",
        url: "/assign",
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  "gift_exchange_participant": $("#txt_gift_exchange_participant").val()
        })
      })
      .done(function( data ) {
    	  location.reload();
    	  //could avoid the reload, but would also have to send up the ideas
    	  //target = data["target"];
      });
}
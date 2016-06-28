function send_message()
{
	$.ajax({
        type: "POST",
        url: "/message",
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  "gift_exchange_participant": $("#txt_gift_exchange_participant").val(),
      	  "email_body": $("#txt_email_body").val()
        })
      })
      .done(function( data ) {
    	  window.location.replace("/main?gift_exchange_participant=" + data["gift_exchange_participant_key"]);
      });
}
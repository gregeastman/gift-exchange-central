function reset_password()
{	
    $.ajax({
      type: "POST",
      url: "/forgot",
      dataType: "json",
      data: JSON.stringify({
    	  "username": $("#txt_username").val(),
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
    		disable_input_controls("#txt_username");
    		$("#btn_reset").prop('disabled', true);
    		$("#span_status_message").html("An email with a link to reset your password has been sent to your email.<br /><a href=\"/login\">Login!</a>");
    	}
    });
}
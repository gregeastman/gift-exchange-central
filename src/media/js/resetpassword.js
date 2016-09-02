function update_password()
{	
    $.ajax({
      type: "POST",
      url: "/password",
      dataType: "json",
      data: JSON.stringify({
    	  "password": $("#txt_password").val(),
    	  "confirm_password": $("#txt_confirm_password").val(),
    	  "token": $("#txt_token").val()
      })
    })
    .done(function( data ) {
    	if (data["message"])
    	{
    		$("#span_error_message").text(data["message"]);
    		$("#div_error").show();
    	} else {
    		$("#div_error").hide();
    		$("#txt_password").prop('disabled', true);
    		disable_input_controls("#txt_password");
    		disable_input_controls("#txt_confirm_password");
    		$("#btn_reset").prop('disabled', true);
    		$("#span_status_message").html("Password successfully updated.<br /><a href=\"/login\">Login!</a>");
    	}
    });
}
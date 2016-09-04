function create_user()
{
	var account_type = "";
	if (opt_google.checked)
	{
		account_type = "google";
	} 
	else if (opt_native.checked) 
	{
		account_type = "native";
	}
	//consider showing a "saving" message
    $.ajax({
      type: "POST",
      url: "/signup",
      dataType: "json",
      data: JSON.stringify({
    	  "account_type": account_type,
    	  "name": $("#txt_name").val(),
    	  "lastname": $("#txt_lastname").val(),
    	  "username": $("#txt_username").val(),
    	  "password": $("#txt_password").val(),
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
    		disable_input_controls(".native_field");
    		disable_input_controls("#txt_name");
    		disable_input_controls("#txt_lastname");
    		$("#btn_create").prop('disabled', true);
    		if (account_type === "native")
    		{
    			$("#span_status_message").html("Account successfully created.<br />A confirmation email has been sent to your account.");
    		}
    		else
			{
    			$("#span_status_message").html("Account successfully created.<br /><a href=\"/login\">Login!</a>");
			}
    	}
    });
}

function update_controls()
{
	if (opt_native.checked)
	{
		enable_input_controls(".native_field");
	} 
	else  
	{
		disable_input_controls(".native_field");
	}
}


$(function(){
	$('input:radio').change(update_controls);
	
	update_controls();
});


function add_row()
{
	save_all($("#tbl_ideas tbody"));
	$("#tbl_ideas tbody").append(
		"<tr>"+
		"<td><input type='text' class='idea_text' size='70' /></td>"+
		"<td><img src='/media/images/save.png' class='btn_save_row'><img src='/media/images/delete.png' class='btn_delete_row'/></td>"+
		"</tr>");
		
		$(".idea_text").focus();
		$(".btn_save_row").bind("click", save_row);		
		$(".btn_delete_row").bind("click", delete_row);
}

function save_row()
{
	var par = $(this).parent().parent(); //tr
	save_row_helper(par);
}

function edit_row()
{
	var par = $(this).parent().parent(); //tr
	save_all(par.parent());
	
	var td_ideas = par.children("td:nth-child(1)");
	if (td_ideas.html().indexOf("idea_text") > -1) //if already in edit mode, quit
	{
		return;	
	}
	var td_buttons = par.children("td:nth-child(2)");

	td_ideas.html("<input type='text' class='idea_text' size='70' value='"+td_ideas.html()+"'/>");
	td_buttons.html("<img src='/media/images/save.png' class='btn_save_row'/>");

	$(".idea_text").focus();
	$(".btn_save_row").bind("click", save_row);
	$(".btn_edit_row").bind("click", edit_row);
	$(".btn_delete_row").bind("click", delete_row);
}

function delete_row()
{
	var par = $(this).parent().parent(); //tr
	delete_row_helper(par);
	update_ideas();
}

function delete_row_helper(par)
{
	par.remove();
}

function save_row_helper(par) 
{
	var td_ideas = par.children("td:nth-child(1)");
	//if already disabled, quit out
	if (!(td_ideas.html().indexOf("idea_text") > -1))
	{
		return;	
	}
	var td_buttons = par.children("td:nth-child(2)");

	var ideas = td_ideas.children("input[type=text]").val()
	
	if (!ideas || (ideas.length === 0))
	{
		delete_row_helper(par);	
	} 
	else 
	{
		td_ideas.html(ideas);
		td_buttons.html("<img src='/media/images/edit.png' class='btn_edit_row'/><img src='/media/images/delete.png' class='btn_delete_row'/>");
		$(".btn_edit_row").bind("click", edit_row);
		$(".btn_delete_row").bind("click", delete_row);
	}
	update_ideas();
}

function save_all(tbody)
{
	var array_length = tbody.children().length;
	for (var i = 0; i < array_length; i++) 
	{
		var query = "tr:nth-child(" + (i+1).toString() + ")";
		var row = tbody.children(query);
		save_row_helper(row);
	}	
}

function update_ideas()
{
	save_all($("#tbl_ideas tbody"));
	
	var idea_list = [];
	$("#tbl_ideas tbody tr").each(
			function(index, value) {
				idea_list.push($(this).find('td').eq(0).text()); 
			});
	
	$.ajax({
        type: "POST",
        url: "/update/" + $("#txt_gift_exchange_participant").val(),
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  //"gift_exchange_participant": $("#txt_gift_exchange_participant").val(),
      	  "idea_list": idea_list
        })
      })
      .done(function( data ) {
    	  g_needs_update_email = true;
    	  //set_temporary_message("#span_status_message", data["message"])
      });
}

function get_assignment()
{
	$.ajax({
        type: "POST",
        url: "/assign/" + $("#txt_gift_exchange_participant").val(),
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  //"gift_exchange_participant": $("#txt_gift_exchange_participant").val()
        })
      })
      .done(function( data ) {
    	  window.location.reload();
    	  //could avoid the reload, but would also have to send up the ideas
    	  //target = data["target"];
      });
}

function send_to_target()
{
	$("#target_message").show();
}

function send_target_message()
{
	send_message($("#txt_target_email_body").val(), "target");
	close_target_message();
}

function cancel_target_message()
{
	close_target_message();
}

function close_target_message()
{
	$("#txt_target_email_body").val("");
	$("#target_message").hide();
}

function send_to_giver()
{
	$("#giver_message").show();
}

function send_giver_message()
{
	send_message($("#txt_giver_email_body").val(), "giver");
	close_giver_message();
}

function cancel_giver_message()
{
	close_giver_message();
}

function close_giver_message()
{
	$("#txt_giver_email_body").val("");
	$("#giver_message").hide();
}

function send_message(message_body, type)
{
	$.ajax({
        type: "POST",
        url: "/message/" + $("#txt_gift_exchange_participant").val(),
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  //"gift_exchange_participant": $("#txt_gift_exchange_participant").val(),
      	  "email_body": message_body,
      	  "message_type": type
        })
      })
      .done(function( data ) {
    	  if (data["message"])
    	  {
    		  //consider making permanent, since this is an erro
    		  set_temporary_message("#span_status_message", data["message"]);

    	  }
    	  else
    	  {
    		  set_temporary_message("#span_status_message", "Message successfully sent.");
	    	  var table_selector = "#tbl_target_messages tbody";
	    	  var header_selector = "#hdr_target_no_messages";
	    	  if (type === "giver")
	    	  {
	    		  table_selector = "#tbl_giver_messages tbody";  
	    		  header_selector = "#hdr_giver_no_messages";
	    	  }
	    	  $(header_selector).hide();
	    	  $(table_selector.split(" ")[0]).show();
	    	  var new_row = "<tr class=\"tr_link\">" +
				"<td style=\"display:none;\">" + data["message_key"] + "</td>" +
				"<td style=\"display:none;\">" + data["message_full"] + "</td>" +
				"<td style=\"display:none;\">" + data["sender"] + "</td>" +
				"<td style=\"display:none;\">" + data["recipient"] + "</td>" +
				"<td width=\"75px\">" + data["message_type"] + "</td>" +
				"<td width=\"240px\">" + data["time"] + "</td>" +
				"<td>" + data["message_truncated"] + "</td>" +
				"</tr>"
	    	  $(table_selector).prepend(new_row);
	    	  $("#tbl_target_messages tr, #tbl_giver_messages tr").click(show_message);
	    				
    	  }
      });
}

function show_message()
{
	td_list = $(this).closest('tr').children('td');
	var message_key = td_list.eq(0).text();
	var time_sent = td_list.eq(5).text();
	var sender = td_list.eq(2).text();
	var recipient = td_list.eq(3).text();
	var content = td_list.eq(1).html();
	$("#span_time_sent").html("Time Sent: " + time_sent);
	$("#span_sender").html("Sender: " + sender);
	$("#span_recipient").html("Recipient: " + recipient);
	$("#span_message_content").html(content);
	$("#div_modal_content, #div_modal_background").show();
}

function hide_background()
{
	$("#div_modal_content, #div_modal_background").hide();
}

function toggle_message_center()
{
	$("#img_message_center_expand").toggle();
	$("#img_message_center_collapse").toggle();
	$("#div_message_center").toggle();
}

function toggle_target()
{
	$("#img_target_expand").toggle();
	$("#img_target_collapse").toggle();
	$("#div_target").toggle();
}

function toggle_giver()
{
	$("#img_giver_expand").toggle();
	$("#img_giver_collapse").toggle();
	$("#div_giver").toggle();
}

function send_notification_email()
{
	if (g_needs_update_email)
	{
		$.ajax({
	        type: "POST",
	        url: "/broadcast/" + $("#txt_gift_exchange_participant").val(),
	        dataType: "json",
	        data: JSON.stringify(
	      	{ 
	      	  //"gift_exchange_participant": $("#txt_gift_exchange_participant").val()
	        })
	      })
	      .done(function( data ) {
	    	  //window.location.reload();
	    	  //could avoid the reload, but would also have to send up the ideas
	    	  //target = data["target"];
	      });
	}
}

var g_needs_update_email = false;

$(function()
{
	//Add, Save, Edit and Delete functions code
	$(".btn_edit_row").bind("click", edit_row);
	$(".btn_delete_row").bind("click", delete_row);
	//$("#btn_add_idea").bind("click", add_row);
	$("#tbl_target_messages tr, #tbl_giver_messages tr").click(show_message);
    $("#div_modal_background, #btn_message_close").click(hide_background);
    toggle_target(); //show target by default
    window.onbeforeunload = send_notification_email;
});
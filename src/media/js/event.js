function add_row()
{
	save_all($("#tbl_participants tbody"));
	$("#tbl_participants tbody").append(
		"<tr>"+
		"<td><input type='text' class='participant_display_name' /></td>"+
		"<td>"+$("#span_email_options").html()+"</td>"+
		"<td><input type='text' class='family_name'/></td>"+
		"<td><img src='/media/images/save.png' class='btn_save_row'><img src='/media/images/delete.png' class='btn_delete_row'/></td>"+
		"</tr>");

		$(".participant_display_name").focus();
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
	
	var td_name = par.children("td:nth-child(1)");
	if (td_name.html().indexOf("participant_display_name") > -1) //if already in edit mode, quit
	{
		return;	
	}
	var td_email = par.children("td:nth-child(2)");
	var selected = td_email.html();
	var td_family = par.children("td:nth-child(3)");
	var td_buttons = par.children("td:nth-child(4)");

	td_name.html("<input type='text' class='participant_display_name' value='"+td_name.html()+"'/>");
	td_email.html($("#span_email_options").html());
	td_email.children()[0].value = selected;
	td_family.html("<input type='text' class='family_name' value='"+td_family.html()+"'/>");
	td_buttons.html("<img src='/media/images/save.png' class='btn_save_row'/>");

	$(".participant_display_name").focus();
	$(".btn_save_row").bind("click", save_row);
	$(".btn_edit_row").bind("click", edit_row);
	$(".btn_delete_row").bind("click", delete_row);
}

function delete_row()
{
	var par = $(this).parent().parent(); //tr
	par.remove();
}


function save_row_helper(par) 
{
	var td_name = par.children("td:nth-child(1)");
	//if already disabled, quit out
	if (!(td_name.html().indexOf("participant_display_name") > -1))
	{
		return;	
	}
	//TODO: check for duplicates
	var td_email = par.children("td:nth-child(2)");
	var td_family = par.children("td:nth-child(3)");
	var td_buttons = par.children("td:nth-child(4)");

	td_name.html(td_name.children("input[type=text]").val());
	var email_caption = td_email.children()[0].value;
	td_email.html(email_caption);
	td_family.html(td_family.children("input[type=text]").val());
	td_buttons.html("<img src='/media/images/edit.png' class='btn_edit_row'/><img src='/media/images/delete.png' class='btn_delete_row'/>");

	$(".btn_edit_row").bind("click", edit_row);
	$(".btn_delete_row").bind("click", delete_row);
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

function save_to_database()
{
	save_all($("#tbl_participants tbody"));
	
	var participant_list = [];
	$("#tbl_participants tbody tr").each(
			function(index, value) {
				var row_object = {};
				row_object["display_name"] = $(this).find('td').eq(0).text();
				row_object["email"] = $(this).find('td').eq(1).text();
				row_object["family"] = $(this).find('td').eq(2).text();
				participant_list.push(row_object); 
			});
	$("#span_status_message").text("Saving...");
	$.ajax({
          type: "POST",
          url: "/admin/event/" + $("#txt_event").val(),
          dataType: "json",
          data: JSON.stringify(
        	{ 
        	  //"event": $("#txt_event").val(),
        	  "event_display_name": $("#txt_event_display_name").val(),
        	  "money_limit": $("#txt_money_limit").val(),
        	  "participant_list": participant_list
          })
        })
        .done(function( data ) {
        	if ($("#txt_event").val() != data["event_string"])
        	{
        		$("#txt_event").val(data["event_string"]);
        		$("#btn_start_event").show();
        		$("#event_status").text("The event has not yet started");
        		$("#txt_money_limit").val(data["money_limit"]);
        	}
        	set_temporary_message("#span_status_message", data["message"]);	   
        });
}

function start_event()
{
	$.ajax({
        type: "POST",
        url: "/admin/statuschange/" + $("#txt_event").val(),
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  //"event": $("#txt_event").val(),
      	  "status_change_type": "start"
        })
      })
      .done(function( data ) {
  		window.location.replace("/admin/event/" + data["event_string"]);
  		/* 
  		 * TODO: Update this to manipulate the DOM.
  		 * 			Disable table for editing
  		 * 			Disable the button to start the event
  		 * 			Enable the button to stop the event
  		 */
      });
}

function end_event()
{
	$.ajax({
        type: "POST",
        url: "/admin/statuschange/" + $("#txt_event").val(),
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  //"event": $("#txt_event").val(),
      	  "status_change_type": "stop"
        })
      })
      .done(function( data ) {
  		$("#btn_end_event").hide();
  		$("#event_status").text("The event has ended");
      });
}


$(function()
{
	//Add, Save, Edit and Delete functions code
	$(".btn_edit_row").bind("click", edit_row);
	$(".btn_delete_row").bind("click", delete_row);
	$("#btn_add_participant").bind("click", add_row);
});
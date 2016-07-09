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
        url: "/update",
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  "gift_exchange_participant": $("#txt_gift_exchange_participant").val(),
      	  "idea_list": idea_list
        })
      })
      .done(function( data ) {
    	  //set_temporary_message("#span_status_message", data["message"])
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
	$.ajax({
        type: "POST",
        url: "/message",
        dataType: "json",
        data: JSON.stringify(
      	{ 
      	  "gift_exchange_participant": $("#txt_gift_exchange_participant").val(),
      	  "email_body": $("#txt_target_email_body").val()
        })
      })
      .done(function( data ) {
    	  set_temporary_message("#span_status_message", data["message"]);
      });
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

$(function()
		{
			//Add, Save, Edit and Delete functions code
			$(".btn_edit_row").bind("click", edit_row);
			$(".btn_delete_row").bind("click", delete_row);
			//$("#btn_add_idea").bind("click", add_row);
		});
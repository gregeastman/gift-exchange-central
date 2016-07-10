function generate_report()
{
	//there's likely a better way
	if (key.checked)
	{
		$(".key").show();
	} 
	else 
	{
		$(".key").hide();
	}
	if (display_name.checked)
	{
		$(".display_name").show();
	} 
	else 
	{
		$(".display_name").hide();
	}
	if (family.checked)
	{
		$(".family").show();
	} 
	else 
	{
		$(".family").hide();
	}
	if (email.checked)
	{
		$(".email").show();
	} 
	else 
	{
		$(".email").hide();
	}
	if (target.checked)
	{
		$(".target").show();
	} 
	else 
	{
		$(".target").hide();
	}
	if (is_target_known.checked)
	{
		$(".is_target_known").show();
	} 
	else 
	{
		$(".is_target_known").hide();
	}
	if (previous_target.checked)
	{
		$(".previous_target").show();
	} 
	else 
	{
		$(".previous_target").hide();
	}
	if (ideas.checked)
	{
		$(".ideas").show();
	} 
	else 
	{
		$(".ideas").hide();
	}
	if (subscribed_to_updates.checked)
	{
		$(".subscribed_to_updates").show();
	} 
	else 
	{
		$(".subscribed_to_updates").hide();
	}
}


$(function()
{
	$("#key").bind("click", generate_report);
	$("#display_name").bind("click", generate_report);
	$("#family").bind("click", generate_report);
	$("#email").bind("click", generate_report);
	$("#target").bind("click", generate_report);
	$("#is_target_known").bind("click", generate_report);
	$("#previous_target").bind("click", generate_report);
	$("#ideas").bind("click", generate_report);
	$("#subscribed_to_updates").bind("click", generate_report);
	
	generate_report();
});
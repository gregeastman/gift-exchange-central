function trim(str) 
{
   return str.replace(/^\s+|\s+$/g,'');
}

function set_temporary_message(span_selector, text)
{
	$(span_selector).text(text);
    setTimeout(clear_message.bind(null, span_selector), 3000);
}

function clear_message(span_selector)
{
	$(span_selector).text("");
}

function external_links() 
{
	if  (!document.getElementsByTagName) return;
	var anchors=document.getElementsByTagName("a");
	for (var i=0;i<anchors.length;i++) {
		var anchor=anchors[i];
		if (anchor.getAttribute("href") && anchor.getAttribute("rel") == "external") {
			anchor.target="_blank";
		}
	}
}
window.onload=external_links();


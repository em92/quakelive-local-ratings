function toggle_table( cat, btn ) {

  var active_toggle = document.querySelector("#table_btns .active");
  active_toggle.className = active_toggle.className.replace(" active", "");

  btn.className = cat + " active";

  var els = document.getElementsByClassName("s");
  for (var i=0; i < els.length; i++) {
    if (els[i].className == "s " + cat) {
      els[i].style.display = "table-cell";
    } else {
      els[i].style.display = "none";
    }
  }

}

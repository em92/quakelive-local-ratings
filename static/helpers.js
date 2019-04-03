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

function relative_time_humanized(ts) {
  var diff = Math.floor(Date.now() / 1000) - ts;
  if (diff < 0) return "Dr. Emmett Brown was here"; // happens if client has incorrect date or timezone

  var r = (
    (diff < 60      && "just now") ||
    (diff < 120     && "a minute ago") ||
    (diff < 3600    && Math.floor(diff / 60) + " minutes ago") ||
    (diff < 7200    && "an hour ago") ||
    (diff < 86400   && Math.floor(diff / 3600) + " hours ago")
  );

  if (r) return r;

  function between_one_and_two_years(diff, one_to_a) {
    var one = one_to_a ? "a" : "1";
    return (
      (diff < 2       && one + " day") ||
      (diff < 31      && diff + " days") ||
      (diff < 60      && one + " month") ||
      (diff < 365     && Math.floor(diff / 30.5) + " months") ||
      (diff == 365    && one + " year") ||
      ("1 year, " + between_one_and_two_years(diff-365, false))
    );
  }

  diff = Math.floor(diff / 86400); // day diff
  if (diff < 730) {
    return between_one_and_two_years(diff, true) + " ago";
  } else {
    return Math.floor(diff / 365) + " years ago";
  };
}

window.onload = function() {
  var els = document.querySelectorAll('[data-timestamp]');
  for(var i=0; i<els.length; i++) {
    var item = els[i];
    var result = relative_time_humanized(parseInt(item.getAttribute('data-timestamp')));
    if (result) item.innerHTML = result;
  }
};

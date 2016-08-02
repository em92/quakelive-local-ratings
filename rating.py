#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

def getList(gametype, page):
  return {"ok": False, "message": "not implemented"}

def getPlayerInfo(player_id):
  return {"ok": False, "message": "not implemented"}

def getForBalancePlugin(ids):
  return {"ok": False, "message": "not implemented"}

def submitMatch(body):
  print(body.decode('utf-8'))
  return {"ok": False, "message": "not implemented", "match_id": "0"}

'''
app.listen(LISTEN_PORT, function () {
  console.log("Listening on port " + LISTEN_PORT.toString());
  
  if (RUN_POST_PROCESS == false) return;
  
  console.log("Updating ratings...");
  rating.update(function(result) {
    if (result.ok == true) {
      console.log("Updated successfully");
    } else {
      console.error(result.message);
    }
  });
});
'''

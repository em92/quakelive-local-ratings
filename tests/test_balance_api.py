from jsonschema import validate

API_ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {
            "type" : "boolean" # TODO: value - false
        },
        "message": {
            "type": "string"
        }
    },
}

BALANCE_API_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {
            "type" : "boolean" # TODO: value - true
        },
        "playerinfo": {
            "type": "object"
        },
        "players": {
            "type": "array"
        },
        "untracked": {
            "type": "array"
        },
        "deactivated":{
            "type": "array"
        }
    },
}

def test_simple_no_steam_ids(test_cli):
    resp = test_cli.get('/elo/')
    assert resp.status_code == 422
    validate(resp.json(), API_ERROR_SCHEMA)

def test_simple_one_invalid_steam_id(test_cli):
    resp = test_cli.get('/elo/1+invalid_steam_id')
    assert resp.status_code == 422
    validate(resp.json(), API_ERROR_SCHEMA)

def test_simple_two_non_existing_steam_id(test_cli):
    resp = test_cli.get('/elo/1+2')
    assert resp.status_code == 200
    validate(resp.json(), BALANCE_API_SCHEMA)

def test_upload_no_signature(service):
    resp = service.upload_match_report(
        sample="something", headers={"Content-Type": "text/plain"}
    )
    assert resp.status_code == 403
    assert "signature" in resp.text.lower()


# TODO:
# shit posting examples
# 202 or 200


def test_upload_junk(service):
    resp = service.upload_match_report(sample="junk sample")
    assert resp.status_code == 500  # TODO: change to 422 in future


def test_upload_sample_again(service):
    resp = service.upload_match_report(sample_name="sample01")
    assert resp.status_code == 409

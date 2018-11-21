def test_404(test_cli):
    resp = test_cli.get('/404')
    assert resp.status_code == 404

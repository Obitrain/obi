import json


def test_list_all_operations(run_cli):
    code, out, _ = run_cli('schema', 'list')
    ops = json.loads(out)
    assert code == 0
    assert {'method', 'path', 'operation_id', 'tags', 'summary'} <= ops[0].keys()
    assert any(o['path'] == '/v1/activities' for o in ops)


def test_list_grep_filters(run_cli):
    _, out, _ = run_cli('schema', 'list', '--grep', 'activities')
    ops = json.loads(out)
    assert ops and all('activities' in o['path'] for o in ops)


def test_list_tag_filters(run_cli):
    _, out, _ = run_cli('schema', 'list', '--tag', 'Activities')
    assert all('Activities' in o['tags'] for o in json.loads(out))


def test_tags_have_counts(run_cli):
    _, out, _ = run_cli('schema', 'tags')
    tags = json.loads(out)
    assert {'tag', 'operations'} == tags[0].keys()
    assert tags[0]['operations'] >= tags[-1]['operations']  # sorted descending


def test_show_by_operation_id(run_cli):
    _, out, _ = run_cli('schema', 'show', 'Get_information_about_the_user_v1_user_get')
    op = json.loads(out)
    assert op['path'] == '/v1/user'
    assert op['method'] == 'GET'
    assert op['schemas']['UserGetResp']['properties']  # definitions are inlined, not just names


def test_show_ambiguous_method_errors(run_cli):
    code, _, err = run_cli('schema', 'show', '/v1/user')
    assert code == 1
    assert 'GET' in json.loads(err)['detail'] and 'PATCH' in json.loads(err)['detail']


def test_show_with_method_disambiguates(run_cli):
    code, out, _ = run_cli('schema', 'show', '/v1/user', '-X', 'GET')
    assert code == 0
    assert json.loads(out)['method'] == 'GET'


def test_show_unknown_ref_errors(run_cli):
    code, _, err = run_cli('schema', 'show', '/does/not/exist')
    assert code == 1
    assert json.loads(err)['error'] == 'error'

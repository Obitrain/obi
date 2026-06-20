from importlib.metadata import version


def test_version_matches_package_metadata(run_cli):
    code, out, _ = run_cli('version')
    assert code == 0
    assert out.strip() == version('obitrain')

from mpyflow import build
from test_mpyflow.utils import get_config_file, raises


def test_app():
    graph = build(get_config_file('app1'), ['app', 'config'])
    wired_controllers= graph['app'].controllers

    assert {'http', 'bluetooth'} == set(wired_controllers)

    from test_mpyflow.mockapp import BluetoothController, HttpController
    assert isinstance(wired_controllers['http'], HttpController)
    assert isinstance(wired_controllers['bluetooth'], BluetoothController)

    assert graph['config'] == wired_controllers['http'].config
    assert graph['config'] == wired_controllers['bluetooth'].config


def test_import_cycle():
    with raises(ValueError, match="Import cycle detected"):
        build(get_config_file('import-cycle'), ['node1', 'node2'])



if __name__ == '__main__':
    test_app()
from upyflow.flow import build
from test_upyflow.utils import get_config_file, raises


def test_app():
    graph = build(get_config_file('app1'), ['app', 'config'])
    wired_controllers = graph['app'].controllers

    assert {'http', 'bluetooth'} == set(wired_controllers)

    from test_upyflow.mockapp import BluetoothController, HttpController
    assert isinstance(wired_controllers['http'], HttpController)
    assert isinstance(wired_controllers['bluetooth'], BluetoothController)

    assert graph['config'] == wired_controllers['http'].config
    assert graph['config'] == wired_controllers['bluetooth'].config


def test_import_cycle():
    with raises(ValueError, match="Import cycle detected"):
        build(get_config_file('import-cycle'), ['node1', 'node2'])


def test_missing_param():
    with raises(TypeError, match="missing 1 required positional argument: 'config'"):
        build(get_config_file('param-errors'), ['controllers'])


if __name__ == '__main__':
    try:
        import pytest
        pytest.main(['-v', __file__])
    except ImportError:
        test_app()
        test_import_cycle()

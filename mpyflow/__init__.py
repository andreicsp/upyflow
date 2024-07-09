from mpyflow.measure import PerformanceContext, ACTION_IMPORT


def build(config_file: str, keys: list):
    """
    Builds the dependency injection graph from the given configuration
    file and for the given root keys.

    :param config_file: The configuration file to read.
    :param keys: The keys in the graph that should be resolved.
        Dependencies of these nodes are automatically resolved first.
    """
    with PerformanceContext("mpyflow", action=ACTION_IMPORT, capture_mem=True):
        from mpyflow.flow import build as build_impl

    return build_impl(config_file=config_file, keys=keys)

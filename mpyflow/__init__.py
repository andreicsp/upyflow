from mpyflow.measure import PerformanceContext


def build(config_file: str, root_keys: list):
    """
    Builds the dependency injection graph from the given configuration
    file and for the given root keys.

    :param config: The configuration file to read.
    :param root_keys: The keys in the graph that should be resolved.
        Dependencies of these nodes are automatically resolved first.
    """
    with PerformanceContext("Loading mpyflow", capture_mem=True):
        from mpyflow.flow import build as build_impl
        return build_impl(config_file=config_file, root_keys=root_keys)

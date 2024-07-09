# Title: MPYFlow - MicroPython Workflow Engine
# Copyright: (c) 2024 Andrei Dumitrache
# License: MIT License
"""
MPYFlow - MicroPython Workflow Engine

Module for building and executing a dependency injection graph from a JSON configuration file.
"""
import builtins
import json
import sys

from mpyflow.measure import PerformanceContext, ACTION_IMPORT
from mpyflow.runtime import getLogger
from collections import namedtuple

_logger = getLogger(__name__)

_config_file_stack = []

NodeCallable = namedtuple("NodeCallable", ["action", "target", "impl", "silent"])


def import_module(name):
    """Imports a module by name and measures the time and memory cost of the import"""
    if name not in sys.modules:
        with PerformanceContext(name, action=ACTION_IMPORT, capture_mem=True):
            __import__(name)

    return sys.modules[name]


def get_callable(path):
    """
    Resolves a callable object from a string

    :param path: The string representing the callable object.
        Module-level functions are represented as "module.function"
        Class constructors are represented as "module.Class"
        Class methods are represented as "module.Class::method"

    :return: The callable object
    """
    callable_parts = path.rsplit(".", 1)
    if len(callable_parts) == 1:
        func_name = callable_parts[0]
        module = builtins
    else:
        module_name, func_name = callable_parts
        module = import_module(module_name)

    func_refs = func_name.split("::", 1)
    module_attr = func_refs[0]
    if not hasattr(module, module_attr):
        raise ValueError(f"Module {module} does not have attribute {module_attr}")

    func = getattr(module, module_attr)
    if len(func_refs) > 1:
        for ref in func_refs[1:]:
            func = getattr(func, ref)
    return func


def ref(graph: dict, node_path: str, to_parent=False):
    """Resolves a node reference from a dot-separated path in the graph."""
    keys = node_path.split(".")
    ref_key = keys[-1]
    keys = keys[:-1] if to_parent else keys
    for key in keys:
        graph = graph[key]

    return graph, ref_key


def is_ref(key):
    """Returns True if the key is a reference key."""
    return key.endswith("!ref")


def get_ref_key(key):
    return key[:-4]


def _update_node_value(graph: dict, path: str, value=None, delete=False):
    graph, key = ref(graph, path, to_parent=True)
    if delete:
        del graph[key]
    else:
        graph[key] = value


def _extract_node_action(node: dict):
    """
    Extracts the Action information from computed nodes

    :param node: The node to extract the Action description from.
    :return: Action performed by the node
    """
    attributes = tuple((attribute for attribute in node if attribute.endswith("@")))
    if not attributes:
        return None
    if len(attributes) > 1:
        raise ValueError(f"Multiple callables found in node: {attributes}")

    action, target = attributes[0][:-1], node.pop(attributes[0])
    if action == "build":
        return NodeCallable(
            action=action,
            target=target,
            silent=False,
            impl=lambda keys: build(config_file=target, keys=keys))
    elif action == "call":
        return NodeCallable(action=action, target=target, silent=False, impl=get_callable(target))
    elif action == "contains":
        return NodeCallable(action=action, target=target, silent=True, impl=lambda collection: target in collection)
    elif action == "getattr":
        return NodeCallable(action=action, target=target, silent=True, impl=lambda obj: getattr(obj, target))
    else:
        raise ValueError(f"Invalid callable action: {action}")


def process_node(graph: dict, node: dict, path: str):
    """
    Processes a node in the graph by resolving references and calling the buildable nodes.
    The references are expected to be resolved before the node is processed.
    After processing, the node is updated in the graph.

    :param graph: The dependency injection graph
    :param node: The node to process
    :param path: The path of the node in the graph
    """
    is_included = node.pop("if@", True)
    if not is_included:
        _logger.info(f"Conditionally excluded node: {path}")
        _update_node_value(graph, path=path, delete=True)
        return

    # Process references
    for key, value in list(node.items()):
        if is_ref(key):
            node.pop(key)
            node[get_ref_key(key)] = ref(graph, value)[0]

    node_callable = _extract_node_action(node)
    if node_callable:
        with PerformanceContext(
                node_callable.target, action=node_callable.action,
                capture_mem=True, silent=node_callable.silent
        ):
            node = node_callable.impl(**node)
        _update_node_value(graph, path=path, value=node)


def get_ordered_nodes(graph: dict, root_keys: list):
    """
    A generator that yields the nodes in the graph in the order they should be processed.
    The order is determined by the references between the nodes.

    :param graph: The dependency injection graph
    :param root_keys: The keys in the graph that should be resolved.
        Dependencies of these nodes are automatically resolved first.
    """
    paths = [(parent_key, graph[parent_key]) for parent_key in root_keys]
    visited_paths = {root_keys[-1]}

    fully_processed = []

    while paths:
        current_path, current_node = paths[-1]  # Peek at the top of the stack, but don't remove it
        all_children_processed = True

        for key, value in current_node.items():
            if isinstance(value, dict):
                child_path, child_node = f"{current_path}.{key}", value
            elif is_ref(key):
                child_path, child_node = value, ref(graph, value)[0]
            else:
                continue

            if child_path not in visited_paths:
                if child_path in paths:
                    raise ValueError(f"Cycle detected: {child_path} referenced by {current_path}")
                visited_paths.add(child_path)
                paths.append((child_path, child_node))
                all_children_processed = False
                break  # Exit the loop as soon as we find a child that hasn't been processed

        if all_children_processed:
            # All children have been processed, so we can add the current_path to keys_to_process
            paths.pop()  # Remove the current_path from the paths stack
            if current_path not in fully_processed:
                fully_processed.append(current_path)
                yield current_path, current_node


def build(config_file: str, keys: list):
    """
    Reads a JSON configuration file and builds a dependency injection graph from it.


    :param config_file: The path to the JSON configuration file.
        It should contain a dictionary with keys representing the nodes in the graph.
    :param keys: The keys in the configuration file that should be resolved.
        Dependencies of these nodes are automatically resolved.
    """
    if config_file in _config_file_stack:
        raise ValueError(f"Import cycle detected: {config_file}")

    _logger.info(f"Building runtime from {config_file}")
    with open(config_file, "r") as f:
        graph = json.load(f)

    _config_file_stack.append(config_file)

    keys = keys or list(graph.keys())
    for path, node in get_ordered_nodes(graph, keys):
        process_node(graph, node, path)

    # Remove all keys that are not needed
    delete_keys = set(graph.keys()) - set(keys)
    for key in delete_keys:
        del graph[key]

    _config_file_stack.pop()
    _logger.info(f"Built graph from [{config_file}]. Keys: {keys}")
    return graph

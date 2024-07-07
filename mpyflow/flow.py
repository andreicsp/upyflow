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

from mpyflow.measure import PerformanceContext
from mpyflow.runtime import getLogger

_logger = getLogger(__name__)

_config_file_stack = []


def attrval(obj, attr, default=None):
    """Returns the value of an attribute of an object, or a default value if the attribute does not exist."""
    return getattr(obj, attr, default)

def contains(obj, elem):
    """Returns True if the element is in the object."""
    return elem in obj

def import_module(name):
    """Imports a module by name and measures the time and memory cost of the import"""
    if name not in sys.modules:
        with PerformanceContext(f"Importing module {name}", logger=_logger, capture_mem=True):
            __import__(name)

    return sys.modules[name]


def get_callable(callable_str):
    """
    Resolves a callable object from a string

    :param callable_str: The string representing the callable object.
        Module-level functions are represented as "module.function"
        Class constructors are represented as "module.Class"
        Class methods are represented as "module.Class::method"

    :return: The callable object
    """
    callable_parts = callable_str.rsplit(".", 1)
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

def get_class(name):
    """Resolves a class from a string in the form "module.MyClass
    
    :param name: The class type
    """
    module_name, class_name = name.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, class_name)


def ref(graph: dict, node_path: str):
    """Resolves a node reference from a dot-separated path in the graph."""
    keys = node_path.split(".")
    for key in keys:
        graph = graph[key]
    return graph


def is_ref(key): 
    """Returns True if the key is a reference key."""
    return key.endswith("!ref")


def get_ref_key(key): return key[:-4]

def _set_node_value(graph: dict, path: str, value):
    keys = path.split(".")
    for key in keys[:-1]:
        graph = graph[key]
    graph[keys[-1]] = value

def _del_node_value(graph: dict, path: str):
    keys = path.split(".")
    for key in keys[:-1]:
        graph = graph[key]
    del graph[keys[-1]]

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
        _del_node_value(graph, path)
        return 
    
    # Process references
    calc_func_ref = node.pop("call@", None)
    for key, value in list(node.items()):
        if is_ref(key):
            node.pop(key)
            key = get_ref_key(key)
            node[key] = ref(graph, value)

    if calc_func_ref:
        calc_func = get_callable(calc_func_ref)
        with PerformanceContext(f"Calling {calc_func_ref}", logger=_logger, capture_mem=True):
            node = calc_func(**node)
        
        _set_node_value(graph, path, node)

def get_ordered_nodes(graph: dict, root_keys: list):
    """
    A generator that yields the nodes in the graph in the order they should be processed.
    The order is determined by the references between the nodes.

    :param graph: The dependency injection graph
    :param root_keys: The keys in the graph that should be resolved. 
        Dependencies of these nodes are automatically resolved first.
    """
    paths = [(parent_key, graph[parent_key]) for parent_key in root_keys]
    visited_paths = set([root_keys[-1]])

    fully_processed = []

    while paths:
        current_path, current_node = paths[-1]  # Peek at the top of the stack, but don't remove it
        all_children_processed = True

        for key, value in current_node.items():
            if isinstance(value, dict):
                child_path, child_node = f"{current_path}.{key}", value
            elif is_ref(key):
                child_path, child_node = value, ref(graph, value)
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

        
def build(config_file: str, root_keys: list):
    """
    Reads a JSON configuration file and builds a dependency injection graph from it.


    :param config_file: The path to the JSON configuration file. 
        It should contain a dictionary with keys representing the nodes in the graph.
    :param root_keys: The keys in the configuration file that should be resolved. 
        Dependencies of these nodes are automatically resolved.
    """
    if config_file in _config_file_stack:
        raise ValueError(f"Import cycle detected: {config_file}")
    
    _logger.info(f"Building runtime from {config_file}")
    with open(config_file, "r") as f:
        graph = json.load(f)

    _config_file_stack.append(config_file)

    root_keys = root_keys or list(graph.keys())
    for path, node in get_ordered_nodes(graph, root_keys):
        process_node(graph, node, path)

    # Remove all keys that are not needed
    delete_keys = set(graph.keys()) - set(root_keys)
    for key in delete_keys:
        del graph[key]

    _config_file_stack.pop()
    _logger.info(f"Runtime built [{config_file}]. Root keys: {root_keys}")
    return graph

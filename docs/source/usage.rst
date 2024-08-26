Usage
=====

upyflow reads a JSON configuration file and builds a graph of nodes that can be used to represent the 
components of an application, or blocks of static configuration.

The graph is built by resolving references between nodes and calling buildable nodes once their respective 
dependencies are resolved.


Flow Configuration
------------------
* The dependency configuration flow is defined in a JSON file.
* The JSON file needs to contain a nested dictionary of nodes
* Each dictionary - except for the root level - represents a node in the graph.

Example of a JSON file showing three nodes (node1, node2, and node2.parent):

    .. code-block:: json

        {
            "node1": {
                "key1": "value1",
                "key2": "value2"
            },
            "node2": {
                "key1": "value1",
                "key2": "value2",
                "parent": {
                    "key1": "value1"
                    "key2": "value2"
                }
            }
        }

Nodes
-----
* A node is a dictionary of properties that can define a buildable application element, or a block of static configuration.
* A node is uniquely identified by its path: a dot-separated string that combines the keys of the nested dictionaries leading to the node.
* Node properties can contain static values, references to other nodes, or definitions for other nodes (dictionaries)
* Nodes cannot be defined at the root level of the JSON file as they need to be part of a parent dictionary to get their unique path.

References
----------
Node properties can be references to other nodes in the graph:

    * Reference property keys end with `!ref`
    * Reference property values represent the dot-separated path to the referenced node.
    * The graph builder will order the nodes so that the referenced nodes are processed before the nodes that reference them.

Example of a reference:
    .. code-block:: json

        {
            "parent_node": {
                "value": 10
            },
            "child_node": {
                "parent!ref": "parent_node"
            }
        }


Buildable Nodes
---------------
* Nodes that contain a `call@` key are considered to be buildable
* The value of the `call@` key is a string representing a callable object in the form `module.submodule.function`
* The callable object is resolved and called with the remaining attributes of the node as keyword arguments.
* The result of the callable is assigned to the node. 
* Any references to the node will resolve to the result of the call

Conditional Nodes
-----------------
* Nodes can be conditionally included in the graph by providing an `if@` key.
* The value of the `if@` key is a boolean expression that determines if the node should be included.
* If the value is False, the node is removed from the graph.
* The expression can also be defined as a buildable node that returns a boolean value.

Example configuration file
--------------------------

.. code-block:: json

    {
        "controllers": {
            "http": {
                "call@": "app.controllers.HttpController",
                "if@": {
                    "call@": "upyflow.flow.contains",
                    "obj!ref": "config.active_controllers",
                    "elem": "http"
                }
            },
            "bluetooth": {
                "call@": "app.controllers.BluetoothController",
                "if@": {
                    "call@": "upyflow.flow.contains",
                    "obj!ref": "config.active_controllers",
                    "elem": "bluetooth"
                }
            }
        },
        "config": {
            "active_controllers": {
                "call@": "app.config.get_active_controllers"
            }
        },
        "app": {
            "call@": "app.App",
            "controllers!ref": "controllers" 
        }
    }


Executing the flow
------------------

The flow is executed by calling the `build` function in the `upyflow.flow` module.
This takes the path to the JSON configuration file and a list of root nodes to build.
Dependencies of the root nodes are resolved and built implicitly.

The return value is a dictionary of the root nodes with their resolved values, including references and buildable nodes.

.. code-block:: python

    from upyflow.flow import build

    result = build("config.json", ["app"])

    print(result["app"])
    # {"controllers": {"http": <HttpController>, "bluetooth": <BluetoothController>}}

    print(result["controllers"]["http"])
    # <HttpController>

    print(result["controllers"]["bluetooth"])
    # <BluetoothController>

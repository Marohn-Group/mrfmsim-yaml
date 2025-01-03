"""Load and dump configuration files for experiment and jobs."""

import importlib
import yaml
import types
from numba.core.registry import CPUDispatcher
import numpy as np
from mrfmsim import Node, Graph, Experiment, ExperimentGroup
import networkx as nx


### Loader ###


def import_object(path):
    """Load object from the path.

    The path is split by the rightmost '.' and the module is imported.
    If the module is not found, the path is split by the next rightmost dot
    and the module is imported. This is repeated until the module is found.
    Otherwise, a ModuleNotFoundError is raised.

    :param str path: dotpath for importing
    """

    maxsplit = 1
    num_dots = path.count(".")
    while True:
        try:  # try split by the rightmost dot
            module, *obj_attrs = path.rsplit(".", maxsplit=maxsplit)
            obj = importlib.import_module(module)
            for attrs in obj_attrs:
                obj = getattr(obj, attrs)
            return obj
        except ModuleNotFoundError:
            maxsplit += 1

            if maxsplit > num_dots:
                raise ModuleNotFoundError(f"No module named {repr(path)}")


def import_multi_constructor(loader, tag_suffix, node):
    """Parse the "!import:" multi tag into an object with parameters.

    The node is parsed as a dictionary.
    """
    obj = import_object(tag_suffix)
    params = loader.construct_mapping(node, deep=True)
    return obj(**params)


def import_constructor(loader, node):
    """Parse the "!import" tag into an object."""

    path = loader.construct_scalar(node)
    return import_object(path)


def graph_multi_constructor(loader, tag_suffix, node):
    """Parse the "!Graph" tag into Graph object.

    The node is listed as a dictionary of the node name and object.
    The design is for a clearer view of nodes. To change this
    behavior, change the graph_constructor.
    """
    param_dict = loader.construct_mapping(node, deep=True)

    graph = Graph(name=tag_suffix)

    grouped_edges = param_dict.pop("grouped_edges")
    graph.add_grouped_edges_from(grouped_edges)

    node_objects = param_dict.pop("node_objects")

    for node_object in node_objects:
        graph.set_node_object(node_object)

    # add additional attributes to the graph
    graph.graph.update(param_dict)
    return graph


def experiment_multi_constructor(loader, tag_suffix, node):
    """Parse the "!Experiment" tag into Experiment object."""

    param_dict = loader.construct_mapping(node, deep=True)

    return Experiment(name=tag_suffix, **param_dict)


def group_multi_constructor(loader, tag_suffix, node):
    """Parse the "!Collection" tag into ExperimentCollection object."""

    param_dict = loader.construct_mapping(node, deep=True)

    return ExperimentGroup(name=tag_suffix, **param_dict)


def func_multi_constructor(loader, tag_suffix, node):
    """Load the "!func:" tag from yaml string.

    The constructor parses !func:function "lambda a, b: a + b".
    In the example, the name of the function is set to "function",
    the function is the lambda expression. The doc is None, set
    doc at the node level.
    """
    node = loader.construct_scalar(node)

    func = eval(node)
    func.__name__ = tag_suffix
    func.__doc__ = node
    func.__expr__ = node

    return func


def nodes_constructor(loader, node):
    """Load the "!Nodes" tag from yaml string.

    The constructor parses !Nodes. For an easier view of the nodes,
    the nodes are listed as a dictionary of the node name and the value is
    a dictionary of the rest of the node properties.
    """
    node_dict = loader.construct_mapping(node)
    nodes = []
    for name, node_dict in node_dict.items():
        nodes.append(Node(name=name, **node_dict))

    return nodes


def yaml_loader(constructors_dict):
    """Create a yaml loader with special constructors.

    :param dict constructor_dict: dictionary of constructors
    :returns: yaml loader class
    """

    class Loader(yaml.SafeLoader):
        pass

    for key, value in constructors_dict["constructor"].items():
        Loader.add_constructor(key, value)
    for key, value in constructors_dict["multi_constructor"].items():
        Loader.add_multi_constructor(key, value)
    return Loader


DEFAULT_CONSTRUCTORS = {
    "constructor": {
        "!import": import_constructor,
        "!Nodes": nodes_constructor,
    },
    "multi_constructor": {
        "!import:": import_multi_constructor,
        "!func:": func_multi_constructor,
        "!Graph:": graph_multi_constructor,
        "!Experiment:": experiment_multi_constructor,
        "!ExperimentGroup:": group_multi_constructor,
    },
}

MrfmSimLoader = yaml_loader(DEFAULT_CONSTRUCTORS)


### Dumper ###


class BlockList(list):
    """Force yaml dumper to represent list as block list."""

    ...


class NodeList(list):
    """Node list object for easier loading and dumping."""

    ...


def func_representer(dumper, func):
    """Represent function scalar."""

    # lambda function
    if hasattr(func, "__expr__"):
        return dumper.represent_scalar(f"!func:{func.__name__}", func.__expr__)

    module = func.__module__
    if module == "__main__":
        raise ValueError("cannot represent functions defined in __main__")
    elif hasattr(func, "metadata"):  # modifier
        # if function is a nested closure, extract the parent name
        # otherwise __qualname__ is the same as __name__
        func_name = func.__qualname__.split(".<locals>")[0]
        return dumper.represent_mapping(
            f"!import:{func.__module__}.{func_name}", func.kwargs
        )
    else:
        dotpath = f"{func.__module__}.{func.__name__}"
        return dumper.represent_scalar("!import", dotpath)


def ufunc_representer(dumper, func):
    """Represent numpy ufunc.

    Numpy ufunc does not have a __module__ attribute. The dotpath is
    numpy.func_name.
    """

    dotpath = f"numpy.{func.__name__}"
    return dumper.represent_scalar("!import", dotpath)


def list_representer(dumper, data):
    """Represent list of dictionaries."""
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


def blocklist_representer(dumper, data):
    """Parse ModelBlockList object into yaml string."""

    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=False)


def graph_multi_representer(dumper, graph):
    """Parse Graph object into yaml string."""

    graph_dict = {
        "grouped_edges": BlockList(graph.grouped_edges),
        "node_objects": NodeList(nx.get_node_attributes(graph, "node_object").values()),
    }

    graph_dict.update(graph.graph)
    graph_dict.pop("name", None)  # remove name from graph_dict

    return dumper.represent_mapping(
        f"!Graph:{graph.name}", graph_dict, flow_style=False
    )


def experiment_multi_representer(dumper, experiment):
    """Parse Experiment object into yaml string."""

    expt_dict = experiment.edit_dict
    name = expt_dict.pop("name")

    return dumper.represent_mapping(f"!Experiment:{name}", expt_dict, flow_style=False)


def experiemnt_group_multi_representer(dumper, group):
    """Parse ExperimentCollection object into yaml string."""


    group_dict = group.edit_dict
    group_dict["node_objects"] = NodeList(group_dict["node_objects"])

    name = group_dict.pop("name")
    for recipe in group_dict["experiment_recipes"].values():
        edges = recipe["grouped_edges"]
        recipe["grouped_edges"] = BlockList(edges)

    return dumper.represent_mapping(
        f"!ExperimentGroup:{name}", group_dict, flow_style=False
    )


def nodes_representer(dumper, nodes):
    """Parse Node object into yaml string."""
    nodes_dict = {}
    for node in nodes:
        node_dict = node.edit_dict
        name = node_dict.pop("name")
        nodes_dict[name] = node_dict
    return dumper.represent_mapping("!Nodes", nodes_dict, flow_style=False)


def yaml_dumper(representers_list):
    """Create a yaml dumper with special representers."""

    class Dumper(yaml.SafeDumper):
        """Yaml dumper with special representers."""

    for type_, representer in representers_list:
        Dumper.add_representer(type_, representer)
    return Dumper


DEFAULT_REPRESENTERS = [
    (types.FunctionType, func_representer),
    (types.BuiltinFunctionType, func_representer),
    (CPUDispatcher, func_representer),  # numba
    (np.ufunc, ufunc_representer),  # numpy ufunc
    (Graph, graph_multi_representer),
    (BlockList, blocklist_representer),
    (NodeList, nodes_representer),
    (list, list_representer),
    (Experiment, experiment_multi_representer),
    (ExperimentGroup, experiemnt_group_multi_representer),
]

MrfmSimDumper = yaml_dumper(DEFAULT_REPRESENTERS)

from mrfmsim_yaml.configuration import (
    import_object,
    MrfmSimLoader,
    MrfmSimDumper,
    yaml_dumper,
    func_representer,
    ufunc_representer,
    list_representer,
    BlockList,
    blocklist_representer,
)
import pytest
import yaml
from textwrap import dedent
import numpy as np
from types import SimpleNamespace as SNs
import math
import types
import operator
import numba as nb


### YAML TEST STRINGS ###


@pytest.fixture
def graph_yaml_str():
    graph_yaml = """\
    !Graph:test_graph
    grouped_edges:
    - [add, [subtract, power, log]]
    - [[subtract, power], multiply]
    node_objects: !nodes
        add:
            func: !func:add 'lambda a, h: a + h'
            output: c
        subtract:
            func: !import '_operator.sub'
            inputs: [c, d]
            output: e
        power:
            func: !import 'math.pow'
            inputs: [c, f]
            output: g
        log:
            func: !import 'math.log'
            inputs: [c, b]
            output: m
        multiply:
            func: !import 'numpy.multiply'
            inputs: [e, g]
            output: k
            output_unit: m^2
    graph_type: mrfmsim
    """
    return dedent(graph_yaml)


@pytest.fixture
def expt_yaml_str():
    """Return an experiment yaml string.

    The content matches the experiment fixture.
    """

    expt_yaml = """\
    !Experiment:test_experiment_plain
    graph: !Graph:test_graph
        grouped_edges:
        - [add, [subtract, power, log]]
        - [[subtract, power], multiply]
        node_objects: !nodes
            add:
                func: !func:add 'lambda a, h: a + h'
                output: c
            subtract:
                func: !import '_operator.sub'
                inputs: [c, d]
                output: e
            power:
                func: !import 'math.pow'
                inputs: [c, f]
                output: g
            log:
                func: !import 'math.log'
                inputs: [c, b]
                output: m
            multiply:
                func: !import 'numpy.multiply'
                inputs: [e, g]
                output: k
                output_unit: m^2
        graph_type: mrfmsim
    param_defaults:
        h: 2
    """
    return dedent(expt_yaml)


@pytest.fixture
def expt_mod_yaml_str():
    """Return an experiment yaml string.

    The content matches the experiment_mod fixture.
    """

    expt_yaml = """\
    !Experiment:test_experiment
    graph: !Graph:test_graph
        grouped_edges:
        - [add, [subtract, power, log]]
        - [[subtract, power], multiply]
        node_objects: !nodes
            add:
                func: !func:add 'lambda a, h: a + h'
                output: c
            subtract:
                func: !import '_operator.sub'
                inputs: [c, d]
                output: e
            power:
                func: !import 'math.pow'
                inputs: [c, f]
                output: g
            log:
                func: !import 'math.log'
                inputs: [c, b]
                output: m
            multiply:
                func: !import 'numpy.multiply'
                inputs: [e, g]
                output: k
                output_unit: m^2
        graph_type: mrfmsim
    components:
        replace_obj: [[a, a1], [b, b1]]
    modifiers: [!import:mmodel.modifier.loop_input {parameter: d}]
    doc: Test experiment with components.
    param_defaults:
        h: 2
    """
    return dedent(expt_yaml)


@pytest.fixture
def expt_file(tmp_path, expt_mod_yaml_str):
    """Create a custom module for testing."""

    module_path = tmp_path / "expt.yaml"
    module_path.write_text(expt_mod_yaml_str)
    return module_path


@pytest.fixture
def group_yaml_str():
    """Return a group yaml string."""

    yaml_str = """\
    !ExperimentGroup:test_group
    doc: Test group object.
    node_objects: !nodes
        add:
            func: !func:add 'lambda a, h: a + h'
            output: c
        subtract:
            func: !import '_operator.sub'
            output: e
            inputs: [c, d]
        power:
            func: !import 'math.pow'
            output: g
            inputs: [c, f]
        multiply:
            func: !import 'numpy.multiply'
            output: k
            inputs: [e, g]
            output_unit: m^2
        log:
            func: !import 'math.log'
            output: m
            inputs: [c, b]
    experiment_recipes:
        test1:
            grouped_edges:
            - [add, [subtract, power, log]]
            - [[subtract, power], multiply]
            returns: [k]
        test2:
            grouped_edges:
            - [add, [subtract, power, log]]
            doc: Shortened graph.
            returns: [c, m]
    experiment_defaults:
        components:
            replace_obj: [[a, a1], [b, b1]]
        doc: Global docstring.
        param_defaults:
            h: 2
    """
    return dedent(yaml_str)


### Test Loader ###


def test_import_object():
    """Load the function from the user module using dot path."""

    func = import_object("operator.add")
    assert func.__name__ == "add"
    assert func(1, 2) == 3

    func = import_object("numpy.emath.power")
    assert func.__name__ == "power"
    assert np.array_equal(func([2, 4], 2), [4, 16])


def test_import_object_error():
    """Test if it raises an error when the object is not found."""

    with pytest.raises(ModuleNotFoundError, match="No module named 'module.addition'"):
        import_object("module.addition")


def test_graph_constructor(experiment, graph_yaml_str):
    """Test the graph constructor parsing the graph correctly.

    If the node function is a lambda, skip the function comparison because
    the functions are not the same.
    """

    graph = yaml.load(graph_yaml_str, MrfmSimLoader)

    # Check if the two graphs are the same
    # however the function is directly parsed. Therefore
    # we can only check if the function names are the same.

    assert graph.name == "test_graph"
    assert graph.graph["graph_type"] == "mrfmsim"
    assert list(graph.nodes) == list(experiment.graph.nodes)
    assert graph.edges == graph.edges

    for node, attrs in graph.nodes.items():
        node_obj = attrs["node_object"]
        config_dict = node_obj.__dict__
        parsed_dict = node_obj.edit_dict
        exp_node_obj = experiment.graph.nodes[node]["node_object"]
        expt_dict = exp_node_obj.edit_dict

        if isinstance(config_dict["func"], types.LambdaType):

            parsed_dict.pop("func")
            expt_dict.pop("func")
            assert config_dict["doc"] == "lambda a, h: a + h"

        assert parsed_dict == expt_dict


def test_lambda_func_constructor():
    """Test if it can load lambda function correctly."""

    lambda_yaml = """\
    !func:test "lambda a, b: a + b"
    """

    lambda_func = yaml.load(dedent(lambda_yaml), MrfmSimLoader)
    assert lambda_func(1, 2) == 3
    assert lambda_func.__name__ == "test"
    assert lambda_func.__expr__ == "lambda a, b: a + b"
    assert lambda_func.__doc__ == "lambda a, b: a + b"


def test_import_multi_obj_constructor():
    """Test import_multi_constructor that returns a SimpleNamespace instance."""

    dataobj_str = """
    !import:types.SimpleNamespace
    a: 1
    b: 'test'
    """

    dataobj = yaml.load(dataobj_str, MrfmSimLoader)
    assert dataobj.a == 1
    assert dataobj.b == "test"


def test_parse_yaml_file(expt_file):
    """Test if the YAML file is parsed correctly."""

    with open(expt_file) as f:
        expt = yaml.load(f, MrfmSimLoader)

    assert expt.name == "test_experiment"
    assert expt.doc == "Test experiment with components."
    assert expt.graph.name == "test_graph"
    assert expt(replace_obj=SNs(a1=1, b1=2), d_loop=[1, 2], f=2) == [
        (18, math.log(3, 2)),
        (9, math.log(3, 2)),
    ]
    assert expt(replace_obj=SNs(a1=1, b1=2), d_loop=[1, 2], f=2, h=3) == [
        (48, 2),
        (32, 2),
    ]
    assert expt.param_defaults == {"h": 2}  # check default is an int
    # assert expt.get_node_object("add").doc == "Add a and h."
    assert expt.get_node_object("add").__name__ == "add"
    func = expt.get_node_object("add")._base_func
    assert func.__name__ == "add"
    assert func.__doc__ == "lambda a, h: a + h"


def test_group_constructor(group_yaml_str):
    """Test if the group is loaded correctly."""

    group = yaml.load(group_yaml_str, MrfmSimLoader)

    assert group.name == "test_group"
    assert group.doc == "Test group object."
    assert list(group.nodes.keys()) == [
        "add",
        "subtract",
        "power",
        "multiply",
        "log",
    ]

    assert group.experiments["test1"].doc == "Global docstring."
    assert group.experiments["test1"](replace_obj=SNs(a1=1, b1=2), d=1, f=2) == 18

    assert group.experiments["test2"].doc == "Shortened graph."
    assert group.experiments["test2"](replace_obj=SNs(a1=1, b1=2), d=1, f=2) == (
        3,
        math.log(3, 2),
    )


### Test Dumper ###


def test_func_representer():
    """Test if the function is dumped correctly."""

    dumper = yaml_dumper(
        [
            (types.FunctionType, func_representer),
            (types.BuiltinFunctionType, func_representer),
        ]
    )

    func = lambda a, b: a + b
    yaml_str = yaml.dump(operator.add, Dumper=dumper)
    assert yaml_str == "!import '_operator.add'\n"


def test_func_representer_numba():
    """Test if the numba function is dumped correctly."""

    dumper = yaml_dumper([(nb.core.registry.CPUDispatcher, func_representer)])

    @nb.jit
    def add(a, b):
        return a + b

    yaml_str = yaml.dump(add, Dumper=dumper)
    # current module name would be the test module
    assert yaml_str == "!import 'tests.test_configuration.add'\n"


def test_ufunc_representer():
    """Test if the numpy ufunc is dumped correctly."""

    dumper = yaml_dumper([(np.ufunc, ufunc_representer)])

    func = np.add
    yaml_str = yaml.dump(func, Dumper=dumper)
    assert yaml_str == "!import 'numpy.add'\n"


def test_mixed_list_representation():
    """Test if the list is represented correctly."""

    dumper = yaml_dumper([(list, list_representer), (BlockList, blocklist_representer)])

    nested_rep = {"block": BlockList(["i", "j", "k"]), "list": ["i", "j", "k"]}

    yaml_str = """\
    block:
    - i
    - j
    - k
    list: [i, j, k]
    """

    yaml_dump_str = yaml.dump(nested_rep, Dumper=dumper)
    assert yaml_dump_str == dedent(yaml_str)


def test_graph_dumper(modelgraph, graph_yaml_str):
    """Test if the graph is dumped correctly."""

    yaml_dump_str = yaml.dump(
        modelgraph, Dumper=MrfmSimDumper, sort_keys=False, indent=4
    )
    assert yaml_dump_str == graph_yaml_str


def test_dumper(experiment, expt_yaml_str):
    """Test if the experiment is dumped correctly."""

    yaml_dump_str = yaml.dump(
        experiment, Dumper=MrfmSimDumper, sort_keys=False, indent=4
    )
    assert yaml_dump_str == expt_yaml_str


def test_dump_additional_info(experiment_mod, expt_mod_yaml_str):
    """Test if the experiment with additional information is dumped correctly."""

    yaml_dump_str = yaml.dump(
        experiment_mod, Dumper=MrfmSimDumper, sort_keys=False, indent=4
    )

    assert yaml_dump_str == expt_mod_yaml_str


def test_group_dumper(group_yaml_str):
    """Test if the group is dumped correctly."""

    group = yaml.load(group_yaml_str, MrfmSimLoader)

    yaml_dump_str = yaml.dump(group, Dumper=MrfmSimDumper, sort_keys=False, indent=4)

    assert yaml_dump_str == group_yaml_str

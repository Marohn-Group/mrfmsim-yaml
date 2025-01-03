mrfmsim-yaml
================

The *mrfmsim-unit* package is a part of the
`mrfmsim project <https://marohn-group.github.io/mrfmsim-docs/>`__,
that provides allows users to define experiment models using YAML files. 

Installation
------------

To install the package, run the following command:

    pip install .

Usage
-----

To define an experiment or experiment group with YAML files, the available tags are:
"!func", "!import", "!nodes", "!Graph", "!Experiment", and "!ExperimentGroup".

.. list-table::
   :widths: 10 40 40
   :header-rows: 1

   * - Tag
     - Usage
     - Description
   * - !func
     - !func:<name> '<expression>'
     - Define function object or expression.
   * - !import (function)
     - !import '<module>'
     - Import an object.
   * - !import (with applied arguments)
     - !import:<module> {<arg1>: <value1>, <arg2>: <value2>, ...}
     - Import an object and pass arguments to it.
   * - !nodes
     - !nodes name: {<node1>: {func: <value1>, output: <value2>, ...}, <node2>: ...}
     - Define a dictionary of node objects.
   * - !Graph
     - !Graph:<name> {grouped_edges: <value1>, node_objects: !nodes: <value2>, ...}
     - Define a graph object.
   * - !Experiment
     - !Experiment:<name> {graph: !Graph:<value1>, components: <value2>, ...}
     - Define an experiment object.
   * - !ExperimentGroup
     - !ExperimentGroup:<name> {node_objects: <value1>, ...}
     - A tag to define an experiment group object.


The following is an example of a YAML configuration file:

.. code-block:: YAML

    # experiment.yaml
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

To load the experiment:

.. code-block:: python

    from mrfmsim_yaml import MrfmSimLoader
    import yaml

    with open('experiment.yaml', 'r') as f:
        experiment = yaml.load(f, MrfmSimLoader)

    >>> print(experiment)
    test_experiment(d_loop, f, replace_obj, h=2)
    returns: (k, m)
    return_units: {'k': 'm^2'}
    graph: test_graph
    handler: MemHandler
    modifiers:
    - loop_input(parameter='d')
    components:
    - replace_obj: [['a', 'a1'], ['b', 'b1']]

    Test experiment with components.

Or to dump an experiment object to a YAML file:

.. code-block:: python

    from mrfmsim_yaml import MrfmSimDumper
    import yaml

    with open('experiment.yaml', 'w') as f:
        yaml.dump(experiment, f, Dumper=MrfmSimDumper)


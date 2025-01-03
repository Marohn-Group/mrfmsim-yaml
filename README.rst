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


# My first `nepi-ng` script

This directory showcases the use of `nepi-ng` to create the simplest possible
experiment:

* 2 nodes are involved (hardwired as `fit01` and `fit31`); one is a sender, and
  one is a receiver
* they are both accessible behind a gateway (`faraday.inria.fr`), that one is
  assumed to have ssh access to as a username that is also hardwired as
 `inria_r2lab.tutorial`

# Purpose

The experiment does not actually do anything on the nodes, just pretends to send
or receive, instead it writes files that we gather at the end. We want to
emphasize orchestration, and how to defer actual gory details to a shell script.

# 2 versions

The same script is implemented twice:

* once in `demo-v1.py` that creates `nepi-ng` objects through pure Python code
* a second time in `demo-v2.py` that is meant to have the exact same behaviour,
  but that showcases the use of a YAML file to define the same
  objects; this code loads `demo-v2.yaml.j2`

# Entry point

This requires a valid reservation at `r2lab.inria.fr`
The scripts use a hard-wired `slice` variable set to `inria_admin`, edit them
to use your slice name.

Once this is done you can run

```bash
python demo-v1.py
# or for the yaml-based version (see also demo-v2.yaml.j2)
python demo-v2.py
```

# Dependencies

Please note that `nepi-ng` is not a library per se, but more of a branding name;
in order to install it you would run (add `sudo if needed` )

```bash
pip install asynciojobs apssh
```

you will need at least apssh-0.23.1; to make sure you have the latest versions, do
```bash
pip install -U asynciojobs apssh
```

for producing graphic outputs you may need to install `graphviz` as well

# Logic

The code in `demo-v1.py` has a prelude that stores in `demo.dot` the sketch of this
scenario. Using `dot` (install with `brew install graphviz` or similar), you can
obtain a png file like this one, that depicts temporal relationships.

![automatically derived sketch](demo.png)

Note that on large scenarios, the scheduler can be instructed to use a maximal
number of active jobs at any given time - see `Scheduler.orchestrate(window=)`

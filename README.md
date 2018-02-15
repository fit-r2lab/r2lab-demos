# History

Prior to Jan. 2018, this contents was hosted as a subdirectory of the main R2lab repo at

https://github.com/parmentelat/r2lab

# Purpose

We expose here a few typical usages of the R2lab testbed

# Requirements

The demos occasionnally depend on the `r2lb-embedded` module; it is the case for example with the `openair` demo.

In order to fullful this requirement, you will need to git glone this repository, preferably at the same level as `r2lab-demos`, or directly under your homedir.

`git clone https://github.com/fit-r2lab/r2lab-embedded`

# What to expect

Mostly ready-to-use scripts; this almost always assumes though:

* that you have registered as an R2lab user, and have uploaded an ssh-key
* that you have a valid reservation when you run any of these demos; this is why you need to configure the slicename that the demo code uses to access the testbed, generally with a `--slice slicename` option for command-line experiments.

# More details

For more detailed explanations on how to use R2lab, make sure to start with the tutorial pages at

https://r2lab.inria.fr/tutorial.md

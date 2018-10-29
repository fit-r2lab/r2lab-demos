# pylint: disable=r0914

"""
The code for drawing the controlling dashboard in visumap

Was initially right in the notebook, but the added value has been
deemed minor compared to its relatively long contents; so we store it
in this module instead

The dasboard*() functions return a widget suitable
as a second argument to interactive_output
"""

from collections import OrderedDict

from ipywidgets import (Dropdown, Layout, HBox, VBox, Text,
                        IntSlider, SelectionSlider, SelectMultiple)
from IPython.display import display

# import a dictionary channel -> frequency
from datastore import naming_scheme
from channels import channel_options

from constants import CHOICES_INTERFERENCE

def to_python(x):
    return x if x == "None" else int(x)
INTERFERENCE_OPTIONS = OrderedDict(
    (x, to_python(x)) for x in CHOICES_INTERFERENCE)


def available_interference_options(datadir):
    """
    Compute which interferences are available in a given result dir
    Returns a dict suitable for a dropdown options attribute
    """
    return {
        str(interference): interference
        for interference in INTERFERENCE_OPTIONS.keys()
        if all(
            naming_scheme(run_name=datadir, protocol=protocol,
                          interference=interference,
                          autocreate=False).exists()
            for protocol in ('batman', 'olsr'))
    }


def _dashboard(datadir, on_nodes, *,
               continuous_sender=False,
               node_legend="node",
               node_key='node_id'):
    """
    some contorsions with ipywidgets to show controls in
    a compact way
    create and display a dashboard
    return a dictionary name->widget suitable for interactive_output

    """
    # dashboard pieces as widgets
    l100 = Layout(width='100%')
    l50 = Layout(width='50%')
    # all space
    w_datadir = Text(
        description="run name", value=datadir,
        layout=l50)
    interference_options = available_interference_options(datadir)
    w_interference = Dropdown(
        options=interference_options, value="None",
        description="Interference amplitude in % : ", layout=l50)
    w_node = SelectionSlider(
        description=node_legend,
        options=on_nodes,
        continuous_update=continuous_sender, layout=l100)
    mapping = dict(
        datadir=w_datadir,
        interference=w_interference)
    mapping[node_key] = w_node
    dashboard_widget = VBox([
        HBox([w_datadir, w_interference]),
        HBox([w_node]),
    ])

    def update_interferences(info):
        # info is a dict with fields like
        # 'old', 'new' and 'owner'
        new_datadir = info['new']
        w_interference.options = available_interference_options(new_datadir)
    w_datadir.observe(update_interferences, 'value')

    display(dashboard_widget)
    return mapping


def dashboard_source(datadir, on_nodes, *,
                     continuous_sender=False):
    return _dashboard(datadir, on_nodes,
                      continuous_sender=continuous_sender,
                      node_legend="sender",
                      node_key='source')

def dashboard_receiver(datadir, on_nodes, *,
                       continuous_sender=False):
    return _dashboard(datadir, on_nodes,
                      continuous_sender=continuous_sender,
                      node_legend="receiver",
                      node_key='receiver')

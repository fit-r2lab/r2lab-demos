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

from ipywidgets import (fixed, Dropdown, Layout, HBox, VBox, Text,
                        IntSlider, SelectionSlider, SelectMultiple)
from IPython.display import display

# import a dictionary channel -> frequency
from datastore import naming_scheme, receiver_nodes, sender_nodes
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



def _dashboard(datadir, *,
               show_node_slider,
               on_nodes=None,
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
    lines = [HBox([w_datadir, w_interference])]
    mapping = dict(
        datadir=w_datadir,
        interference=w_interference)

    if show_node_slider:
        w_node = SelectionSlider(
            description=node_legend,
            options=on_nodes,
            continuous_update=continuous_sender, layout=l100)
        lines.append(HBox([w_node]))
        mapping[node_key] = w_node

    def update_interferences(info):
        # info is a dict with fields like
        # 'old', 'new' and 'owner'
        new_datadir = info['new']
        w_interference.options = available_interference_options(new_datadir)
    w_datadir.observe(update_interferences, 'value')

    dashboard_widget = VBox(lines)
    display(dashboard_widget)
    return mapping


# we use sender_nodes() and receiver_nodes() to compute
# the choices that make sense; no slider is shown when only
# one node in that position (sender or receiver) is available
def dashboard_sender(datadir, *,
                     continuous_sender=False):
    nodes = [int(x) for x in sender_nodes(datadir)]
    show_node_slider = len(nodes) > 1
    variables = _dashboard(datadir,
                           show_node_slider=show_node_slider,
                           on_nodes=nodes,
                           node_legend="sender",
                           node_key='source',
                           continuous_sender=continuous_sender)
    if not show_node_slider:
        variables['sender'] = fixed(nodes[0])
    return variables

def dashboard_receiver(datadir, *,
                       continuous_sender=False):
    nodes = [int(x) for x in receiver_nodes(datadir)]
    show_node_slider = len(nodes) > 1
    variables = _dashboard(datadir,
                           show_node_slider=show_node_slider,
                           on_nodes=nodes,
                           node_legend="receiver",
                           node_key='receiver',
                           continuous_sender=continuous_sender)
    if not show_node_slider:
        variables['receiver'] = fixed(nodes[0])
    return variables
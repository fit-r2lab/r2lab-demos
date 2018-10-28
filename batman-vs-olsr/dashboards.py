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
from utils import naming_scheme

from channels import channel_options

ANTENNA_OPTIONS = OrderedDict([("1", 1), ("2", 3), ("3", 7)])

INTERFERENCE_OPTIONS = OrderedDict(
    (str(x), x) for x in
    (-13, -12, -11, -10, -9, -8, -7, "None",
     1, 2, 3, 4, 5, 6, 7))


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
              node_key='node_id',
              ):
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
        description="Interference power in dBm: ", layout=l50)
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

def dashboard_multiple(datadir, on_nodes, continuous_sender=False):
    """
    some contorsions with ipywidgets to show controls in
    a compact way
    create and display a dashboard
    return a dictionary name->widget suitable for interactive_output
    """
    # dashboard pieces as widgets
    l75 = Layout(width='75%')
    l50 = Layout(width='50%')
    l32 = Layout(width='32%')
    l25 = Layout(width='25%')
    # l10 = Layout(width='10%')
    # all space
    w_datadir = Text(
        description="run name", value=datadir,
        layout=l25)
    w_sender = SelectionSlider(
        description="sender node",
        options=on_nodes,
        continuous_update=continuous_sender, layout=l75)
    w_power = Dropdown(
        options=list(range(1, 15)),
        value=5, description="tx power in dBm", layout=l32)
    w_rate = Dropdown(
        options=[54], value=54,
        description="phy rate", layout=l32)
    # yeah, this is a little weird all right
    w_antenna_mask = Dropdown(
        options=ANTENNA_OPTIONS, value=1,
        description="number of antennas: ", layout=l50)
    w_channel = Dropdown(
        options=channel_options,
        value=10, description="channel", layout=l32)
    w_interference = Dropdown(
        options=INTERFERENCE_OPTIONS, value="None",
        description="Interference power in dBm: ", layout=l50)

    w_select_multiple = SelectMultiple(
        options=on_nodes,
        value=[3],
        description='Destinations: ',
        disabled=False)

    w_maxcount = Text(description="Max different data: ", value="5")

    # make up a dashboard

    dashboard_widget = VBox([
        HBox([w_datadir, w_sender]),
        HBox([w_power, w_rate, w_channel]),
        HBox([w_antenna_mask, w_interference]),
        HBox([w_select_multiple, w_maxcount],
             layout=Layout(width='100%',
                           display='inline-flex',
                           flex_flow='row wrap'))])
    display(dashboard_widget)

    return dict(datadir=w_datadir,
                tx_power=w_power, phy_rate=w_rate, channel=w_channel,
                antenna_mask=w_antenna_mask,
                interference=w_interference,
                source=w_sender,
                dests=w_select_multiple,
                maxdata=w_maxcount)

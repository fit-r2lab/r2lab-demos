"""
The code for drawing the controlling dashboard in visumap

Was initially right in the notebook, but the added value has been
deemed minor compared to its relatively long contents; so we store it
in this module instead

The dasboard() function returns a widget suitable 
as a second argument to interactive_output
"""

from collections import OrderedDict

from ipywidgets import (interactive_output, fixed,
                        IntSlider, Dropdown, Layout, HBox, VBox, Text)
from IPython.display import display


# import a dictionary channel -> frequency
from channels import channel_frequency, channel_options


def dashboard(datadir):
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

    # all space
    w_datadir = Text(description="run name", value=datadir,
                     layout=l25)
    w_sender = IntSlider(description="sender node",
                         min=1, max=37, step=1, value=21,
                         continuous_update=False, layout=l75)
    w_power = Dropdown(options=list(range(0, 16)),
                       value=14, description="tx power in dBm", layout=l32)
    w_rate = Dropdown(options=[1, 54], value=1,
                      description="phy rate", layout=l32)
    # yeah, this is a little weird all right
    w_antenna_mask = Dropdown(options=OrderedDict([("1", 1), ("2", 3), ("3", 7)]),
                              value=7,
                              description="number of antennas: ", layout=l50)
    w_channel = Dropdown(options=channel_options,
                         value=1, description="channel", layout=l32)
    w_rssi_rank = IntSlider(min=0, max=3, value=0,
                            description="RSSI rank: ", layout=l50)

    # update range for the rssi_rank widget from selected antenna_mask
    def update_rssi_rank_from_antennas(*args):
        w_rssi_rank.max = 3 if w_antenna_mask.value == 7\
            else 2 if w_antenna_mask.value == 3 \
            else 1
    w_antenna_mask.observe(update_rssi_rank_from_antennas, 'value')

    # make up a dashboard
    dashboard = VBox([HBox([w_datadir, w_sender]),
                      HBox([w_power, w_rate, w_channel]),
                      HBox([w_antenna_mask, w_rssi_rank])])
    display(dashboard)
    return dict(datadir=w_datadir, sender=w_sender,
                power=w_power, rate=w_rate, channel=w_channel,
                antenna_mask=w_antenna_mask,
                rssi_rank=w_rssi_rank)

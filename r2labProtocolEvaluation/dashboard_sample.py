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
                        IntSlider, Dropdown, Layout, HBox, VBox, Text, SelectionSlider)
from IPython.display import display


# import a dictionary channel -> frequency
from channels import channel_frequency, channel_options


def dashboard(datadir, onnodes,continuous_sender = False):
    """
    some contorsions with ipywidgets to show controls in 
    a compact way
    create and display a dashboard 
    return a dictionary name->widget suitable for interactive_output
    """
    # dashboard pieces as widgets
    l100 = Layout(width='100%')
    l75 = Layout(width='75%')
    l50 = Layout(width='50%')
    l32 = Layout(width='32%')
    l25 = Layout(width='25%')
    # all space
    w_datadir = Text(description="run name", value=datadir,
                     layout=l25)
    w_sender = SelectionSlider(description="sender node",
                            options = onnodes,
                            continuous_update=continuous_sender, layout=l75)
    w_power = Dropdown(options=list(range(1, 15)),
                       value=1, description="tx power in dBm", layout=l32)
    w_rate = Dropdown(options=[54], value=54,
                      description="phy rate", layout=l32)
    # yeah, this is a little weird all right
    w_antenna_mask = Dropdown(options=OrderedDict([("1", 1), ("2", 3), ("3", 7)]),
                              value=1,
                              description="number of antennas: ", layout=l50)
    w_channel = Dropdown(options=channel_options,
                         value=10, description="channel", layout=l32)
    w_interference = Dropdown(options = OrderedDict([("-12", -12),("-11", -11),("-10", -10)
                                                     ,("-9", -9),("-8", -8),("-7", -7)
                                                     ,("None", "None"), ("1", 1), ("2", 2)
                                                     , ("3", 3), ("4", 4)
                                                     , ("5", 5), ("6", 6)
                                                     , ("7", 7)]), value="None",
                            description="Interference power in dBm: ", layout=l50)
    w_sample = IntSlider(description = "sample number",
                         min=0, max=2000, step=1, value=1,
                         continuous_update=continuous_sender, layout = l100)
    # make up a dashboard
    dashboard = VBox([HBox([w_datadir, w_sender]),
                      HBox([w_power, w_rate, w_channel]),
                      HBox([w_antenna_mask, w_interference]),
                      HBox([w_sample])])
    display(dashboard)
    return dict(datadir=w_datadir,
                tx_power=w_power, phy_rate=w_rate, channel=w_channel,
                antenna_mask=w_antenna_mask,
                interference=w_interference,
                source=w_sender,
                sample=w_sample)

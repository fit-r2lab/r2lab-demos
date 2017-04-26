"""
Correspondance channel - frequency for WiFi
"""

# source
# http://www.radio-electronics.com/info/wireless/wi-fi/80211-channels-number-frequencies-bandwidth.php
from collections import OrderedDict

channel_frequency = OrderedDict([
    (1,   2412), (2,   2417), (3,   2422), (4,   2427),
    (5,   2432), (6,   2437), (7,   2442), (8,   2447),
    (9,   2452), (10,  2457), (11,  2462), (12,  2467),
    (13,  2472), (14,  2484),
    (36,  5180), (40,  5200), (44,  5220), (48,  5240),
    (52,  5260), (56,  5280), (60,  5300), (64,  5320),
    (100, 5500), (104, 5520), (108, 5540), (112, 5560),
    (116, 5580), (120, 5600), (124, 5620), (128, 5640),
    (132, 5660), (136, 5680), (140, 5700), (149, 5745),
    (153, 5765), (157, 5785), (161, 5805), (165, 5825),
])

##########
# same contents formatted for use in a ipywidget
channel_options = OrderedDict(
    ("ch. {}".format(ch), ch) for ch in channel_frequency.keys()
)

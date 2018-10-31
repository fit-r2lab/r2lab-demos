# the constant wireless conditions
WIRELESS_DRIVER = 'ath9k'
# the minimum for atheros cards
TX_POWER = 5
# the more ambitious, the more likely to create trouble
PHY_RATE = 54
# arbitrary
CHANNEL = 10
# only one antenna seems again the most fragile conditions
ANTENNA_MASK = 1

# usrp-2 and n210; we use uhd_siggen --sine with an amplitude
# e.g interference = 20 -> ushd_siggen --since --amplitude 0.20
CHOICES_INTERFERENCE = ["None", '10', '15', '20', '25', '30', ]
DEFAULT_INTERFERENCE = ["None"]

# focusing on n210 and usrp2:
# n210 = 12 15 27 30 31 36 37
# usrp2 = 5 13
CHOICES_SCRAMBLER_ID = [5, 12, 13, 15, 27, 30, 31, 36, 37]
DEFAULT_SCRAMBLER_ID = 5

# The 10 nodes selected by Farzaneh adapted
# replacing 15 with 14 as 15 exhibits some odd behaviour
DEFAULT_NODE_IDS = [1, 4, 12, 14, 19, 27, 31, 33, 37]
DEFAULT_SRC_IDS = [1]
DEFAULT_DEST_IDS = [37]

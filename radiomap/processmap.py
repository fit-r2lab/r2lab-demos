#!/usr/bin/env python3

# Compute average RSSI values for each node and fill values when missing with either RSSI_MIN or RSSI_MAX
# - input RSSI files "result-X.txt" obtained through tshark for each FIT "receiving" node contain RSSI values corresponding
# to ICMP ping packets sent by other FIT nodes. The number of RSSI values for each ping depends on the number of antennas 
# used. 
# - output RSSI files "rssi-X.txt" contain the average RSSI values received at node X.
# - output file RSSI.txt contains the overall RSSI information that will be used to plot the heatmap.
#
# TT 20/3/17


import os

RSSI_MAX = 0
RSSI_MIN = -100


# convenience
def fitname(id):
    return "fit{:02d}".format(id)

def mask_to_nb(mask):
    switcher = {
        1: 1,
        3: 2,
        7: 3,
    }
    return switcher.get(mask)

def save_RSSI(file_RSSI, node_max, RSSI):
    """
    write to file the overall RSSI values
    """
    [[file_RSSI.write(RSSI[s][r]) for r in range(1, node_max)] for s in range(1, node_max)]
    return 0

def store_missing_rssi(file_out, Nant, node, sender, receiver, RSSI):
    """
    write to the output file the missing  RSSI value for the couple sender, receiver 
    i.e., RSSI_MAX if the node itself is sending or else RSSI_MIN

    """
    if sender == node:
        value = RSSI_MAX
    else:
        value = RSSI_MIN
    output = "10.0.0.{:02d}\t10.0.0.{:02d}\t".format(sender, receiver)
    for i in range(Nant+1):
        output += "{}\t".format(value)
    output += "\n"
    file_out.write(output)
    RSSI[sender][receiver] = output
    return 0



def store_rssi(file_out, Nant, sender, receiver, sum_rssi, Nval, RSSI):
    """
    write to the output file constant RSSI values for the couple sender, receiver
    """
    output = "10.0.0.{:02d}\t10.0.0.{:02d}\t".format(sender, receiver)
    for i in range(Nant+1):
        output += "{0:.2f}\t".format(sum_rssi[i]/Nval)
    output += "\n"
    file_out.write(output)
#    print("{} {}".format(sender,receiver))
    RSSI[sender][receiver] = output
    return 0



def process(file_in, file_out, node, node_max, Nant, RSSI):
    """
    expects a FIT node number and the number of antennas and postprocess data
    lines of file_in for receiver Y are in the following format:
    10.0.0.X	10.0.0.Y	A,B,C,D
    where X is for sender, Y for receiver, A..D integer values for RSSI, 
    if Nant==1, only A and B, if Nant==3, A,B,C,D RSSI values are included
    """

    cur_sender = 0
    expected = 1

    for line in file_in:
        # Read RSSI values one line at a time
        sender = int(line.split()[0].split('.')[3])
        receiver = int(line.split()[1].split('.')[3])
        rssi  = [int(line.split()[2].split(',')[i]) for i in range(Nant+1)]

        if sender == cur_sender:
            # Yet another RSSI value for cur_sender to process
            sum_rssi = [sum_rssi[i]+rssi[i] for i in range(Nant+1)]
            Nval += 1
        else:
            # This sender is new (or an old one, not to take into account)
            if cur_sender:
                # only if not at beginning
                if sender > cur_sender:
                    # this check to ignore possible old sender...
                    # Store RSSI computed for cur_sender as no more data for it
                    store_rssi(file_out, Nant, cur_sender, receiver, sum_rssi, Nval, RSSI)
                    expected += 1
            while expected < sender:
                # handle the case when data is missing for some senders
                store_missing_rssi(file_out, Nant, node, expected, receiver, RSSI)
                expected += 1
            if sender > cur_sender:
                # At this point, sender is the one expected and it is the first RSSI value to store
                sum_rssi = rssi
                Nval = 1
                cur_sender = sender
    # At this point there is no more data in file
    # we need to store RSSI computed for the current sender
    # and handle the case when the current sender is not the last sender in the list
    if cur_sender:
        # Store RSSI computed for cur_sender as no more data for it, receiver==node
        store_rssi(file_out, Nant, cur_sender, receiver, sum_rssi, Nval, RSSI)
        expected += 1
    while expected < node_max:
        # handle the case when data is missing for some senders
        store_missing_rssi(file_out, Nant, node, expected, node, RSSI)
        expected += 1
    # we are done
             
    return 0



def main():
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    parser.add_argument("-m", "--max", default=5, type=int,
                        help="node number vary between 1 and this number")
    parser.add_argument("-a", "--ant-mask", default=1,type=int,choices = [1,3,7],
                        help="specify the mask of antennas for each node - default is 1")

    parser.add_argument("-v", "--verbose", action='store_true', default=False)
    parser.add_argument("-d", "--debug", action='store_true', default=False)
                        
    args = parser.parse_args()
    
    node_max = args.max+1
    ant_mask = args.ant_mask
    Nant = mask_to_nb(ant_mask)

    pos = [[0,0],[1,5],[1,4],[1,3],[1,2],[1,1],[2,5],[2,4],[2,3],[2,2],[2,1],[3,5],[3,4],[3,3],
           [3,2],[3,1],[4,5],[4,3],[4,2],[5,5],[5,4],[5,3],[5,2],[6,5],[6,3],[6,2],[7,5],[7,4],
           [7,3],[7,2],[7,1],[8,5],[8,4],[8,3],[8,2],[8,1],[9,2],[9,1]]
    RSSI = [["" for sender in range(1, node_max+1)] for receiver in range(1, node_max+1)]
    file_RSSI = open("RSSI.txt", "w")

    for node in range(1, node_max):
        filename_in = "result-{}.txt".format(node)
        filename_out = "rssi-{}.txt".format(node)
        file_in = open(filename_in, "r")
        file_out = open(filename_out, "w")
        process(file_in, file_out, node, node_max, Nant, RSSI)
        file_in.close()
        file_out.close()
    save_RSSI(file_RSSI, node_max, RSSI)
    file_RSSI.close()

    exit(0)

if __name__ == "__main__":main()

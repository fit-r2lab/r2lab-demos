#!/usr/bin/env python3

# input file names are assumed on the form "result-X.txt" where X corresponds to the FIT node number
# output file names will be on the form "rssi-X.txt"
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



def store_cte_rssi(file_out, Nant, sender, receiver, value):
    """
        write to the output file constant RSSI values for the couple sender, receiver
     """
    output = "10.0.0.{:02d}\t10.0.0.{:02d}\t".format(sender, receiver)
    for i in range(Nant+1):
        output += "{}\t".format(value)
    file_out.write(output+"\n")
    return 0



def store_rssi(file_out, Nant, sender, receiver, sum_rssi, Nval):
    """
    write to the output file constant RSSI values for the couple sender, receiver
    """
    output = "10.0.0.{:02d}\t10.0.0.{:02d}\t".format(sender, receiver)
    for i in range(Nant+1):
        output += "{0:.2f}\t".format(sum_rssi[i]/Nval)
    file_out.write(output+"\n")
    return 0



def process(file_in, file_out, node, node_max, Nant):
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
            # This sender is new
            if cur_sender:
                # Store RSSI computed for cur_sender as no more data for it
                store_rssi(file_out, Nant, cur_sender, receiver, sum_rssi, Nval)
                expected += 1
            while expected < sender:
                # handle the case when no data is there for senders
                if expected == node:
                    # RSSI is max when the node itself is sender
                    store_cte_rssi(file_out, Nant, expected, receiver, RSSI_MAX)
                else:
                    # this case occurs when all the pings fail with this expected sender
                    store_cte_rssi(file_out, Nant, expected, receiver, RSSI_MIN)
                expected += 1
            # At this point, sender is the one expected and it is the first RSSI value to store
            sum_rssi = rssi
            Nval = 1
            cur_sender = sender
    # At this point there is no more data in file
    # we need to store RSSI computed for the current sender
    # and handle the case when the current sender is not the last sender in the list
    if cur_sender:
        # Store RSSI computed for cur_sender as no more data for it, receiver==node
        store_rssi(file_out, Nant, cur_sender, receiver, sum_rssi, Nval)
        expected += 1
    while expected < node_max:
        # data are missing for some senders
        if expected == node:
            # RSSI is max when the node itself is sender                                                            
            store_cte_rssi(file_out, Nant, expected, node, RSSI_MAX)
        else:
            # this case occurs when all the pings fail with this expected sender                                    
            store_cte_rssi(file_out, Nant, expected, node, RSSI_MIN)
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

    for node in range(1, node_max):
#
# Following does not work, so the tshark processing step should be done by running the pprocess.sh script before 
# 
#    node = 1
#    command = "tshark -2 -r fit"+str(node)+".pcap  -R \"ip.dst==10.0.0."+str(node)+" -Tfields -e \"ip.src\" -e \"ip.dst\" -e \"radiotap.dbm_antsignal\" >> result-"+str(node)+".txt"
##    command = 'tshark -2 -r fit'+str(node)+'.pcap  -R "ip.dst==10.0.0.'+str(node)+' -Tfields -e "ip.src" -e "ip.dst" -e "radiotap.dbm_antsignal" >> result-'+str(node)+'.txt'
#    print("command is {}".format(command))
#    os.system(command)
        filename_in = "result-{}.txt".format(node)
        filename_out = "rssi-{}.txt".format(node)
        file_in = open(filename_in, "r")
        file_out = open(filename_out, "w")
        process(file_in, file_out, node, node_max, Nant)
        file_in.close()
        file_out.close()

    exit(0)

if __name__ == "__main__":main()

#!/usr/bin/env python3
from r2labmap import dict_to_xyz


def read_rssi(filename, sender, rssi_rank):
    '''
    read a RSSI file and, given a sender node and 
    an rssi_rank, returns a dictionary 
    node_number -> value
    '''

    node_number_to_value = {}
    try:
        with open(filename) as input:
            for line in input:
                ip_snd, ip_rcv, *values = line.split()
                *_, n_snd = ip_snd.split('.')
                *_, n_rcv = ip_rcv.split('.')
                n_snd = int(n_snd)
                n_rcv = int(n_rcv)
                if n_snd != sender:
                    continue
                node_number_to_value[n_rcv] = values[rssi_rank]
    except IOError as e:
        print("Cannot open file {}: {}" .format(filename, e))
        return
    except Exception as e:
        print("Ooops {}: {}".format(type(e), e))
        return

    return node_number_to_value

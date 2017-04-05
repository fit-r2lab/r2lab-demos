#!/usr/bin/env python3                                                                                                
'''
Plot RSSI values on nodes for one target sender with the R2lab space 
'''

from r2labmap import dict_to_xyz

def read_rssi(filename, sender, rssi_rank):
    data = {}
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
                data[n_rcv] = values[rssi_rank]
    except IOError as e:
        print("Cannot open file {}: {}" .format(filename, e))
        return
    except Exception as e:
        print("Ooops {}: {}".format(type(e), e))
        return

    # return a triplet X, Y, Z
    return dict_to_xyz(data)

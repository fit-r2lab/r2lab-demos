### harware map
# the python code for interacting with sidecar is too fragile for now
# to be invoked every time; plus, it takes time; so:
def hardwired_hardware_map():
    return {
        'E3372-UE': (2, 26),
        'OAI-UE':  (6, 8, 19),
        'OAI-ENB': (16, 23, 25),
    }

# build our hardware map: we compute the ids of the nodes
# that have the characteristics that we want
def probe_hardware_map():
    # import here so depend on websockets only if needed
    from r2lab import SidecarSyncClient
    import ssl
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.CERT_NONE
    with SidecarSyncClient(ssl=ssl_context) as sidecar:
        nodes_hash = sidecar.nodes_status()

    if not nodes_hash:
        print("Could not probe testbed status - exiting")
        exit(1)

    # debug
    #for id in sorted(nodes_hash.keys()):
    #    print(f"node[{id}] = {nodes_hash[id]}")

    # we search for the nodes that have usrp_type == 'e3372'
    e3372_ids = [id for id, node in nodes_hash.items()
                 if node['usrp_type'] == 'e3372']
    # and here the ones that have a b210 with a 'for UE' duplexer
    oaiue_ids = [id for id, node in nodes_hash.items()
                 if node['usrp_type'] in {'b205', 'b210'}
                 and 'ue' in node['usrp_duplexer'].lower()]
    oaienb_ids = [id for id, node in nodes_hash.items()
                 if node['usrp_type'] in {'b205', 'b210'}
                 and 'enb' in node['usrp_duplexer'].lower()]

    return {
        'E3372-UE' : e3372_ids,
        'OAI-UE' :  oaiue_ids,
        'OAI-ENB' : oaienb_ids,
    }


def show_hardware_map(hw_map):
    print("Nodes that can be used as E3372 UEs (suitable for -E/-e):",
          ', '.join([str(id) for id in sorted(hw_map['E3372-UE'])]))
    print("Nodes that can be used as OpenAirInterface UEs (suitable for -U/-u)",
          ', '.join([str(id) for id in sorted(hw_map['OAI-UE'])]))
    print("Nodes that can be used as OpenAirInterface eNBs (suitable for --ran)",
          ', '.join([str(id) for id in sorted(hw_map['OAI-ENB'])]))


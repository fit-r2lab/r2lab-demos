import os.path

from asynciojobs import Engine, Job, Sequence

from apssh.sshjobs import SshNode, SshJob, SshJobScript

def script(s):
    return os.path.join("../infra/user-env/", s)

includes = [ script(x) for x in [ "r2labutils.sh", "nodes.sh", "oai-common.sh"] ]

def run(gateway, hss, epc, enb):
    """
    expects e.g.
    gateway : s.t like onelab.inria.oai.oai_build@faraday.inria.fr
    hss : 23
    epc : 16
    enb : 19
    """
    
    gwuser, gwhost = gateway.split('@')
    gwnode = SshNode(hostname = gwhost,
                     username = gwuser)

    hssname, epcname, enbname = [ "fit{:02d}".format(str(x).replace('fit','')) for x in hss, epc, enb ]
    
    hssnode, epcnode, enbnode = [
        SshNode(gateway = gwnode,
                hostname = hostname)
        or hostname in hssname, epcname, enbname
    ]

    load_infra = SshJob(
        node = gwnode,
        commands = [
            [ "rhubarbe", "load", "-i", "u16-oai-gw", hssname, epcname ],
            [ "rhubarbe", "wait", "-t",  120, hssname, epcname ],
        ],
        label = "load and wait HSS and EPC nodes",
    )

    load_enb = SshJob(
        node = gwnode,
        commands = [
            [ "rhubarbe", "load", "-i", "u16-oai-enb", enbname ],
            [ "rhubarbe", "wait", "-t", 120, enbname ],
        ]
        label = "load and wait ENB")
    )
        
    #    run_hss = Sequence(
    #        JobScript(node = hssnode,
    #                  command = [ "../infra/user-env/", "xxx" ])
    #        )

    run_enb = JobScript(
        node = enbnode,
        command =
        [ script("oai-enb.sh"), "run-enb", epc ],
        label = "run softmodem on ELB",
        requires = [ load_infra, load_enb ],
    )

    e = Engine(run_enb, load_enb, load_infra)
    if not e.orchestrate():
        print("KO")
        e.debrief()
    else:
        print("OK")

run("root@faraday.inria.fr", hss=23, epc=16, enb=11)

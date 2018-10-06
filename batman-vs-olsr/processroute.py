# pylint: disable=c0111, r0914, r1702, r0912, r0915
"""
    Class to parse routing table of olsr and
    routing table of batman.
    Will be called at the end of one_run to generate
    a file containing the paths from the
    different nodes selected to do the pings from
"""

from utils import time_line

class ProcessRoutes:
    def __init__(self, run_root, exp_nodes, node_ids):
        self.run_root = run_root
        self.exp_nodes = exp_nodes
        self.node_ids = node_ids
        self.all_routes = {
            (source, destination): 0
            for source in node_ids
            for destination in node_ids
            if source != destination
        }

    def reset(self):
        self.all_routes = {
            (source, destination): 0
            for source in self.node_ids
            for destination in self.node_ids
            if source != destination
        }
    def run(self):
        #Generating Src,Dest : next_hop  table
        time_line("Generation global routing map")
        for source_id in self.node_ids:
            file_name = self.run_root / f"ROUTE-TABLE-{source_id:02d}"
            time_line(f"creating {file_name}")
            with file_name.open() as file_routes:
                for line in file_routes:
                    #Batman has another way to display routes
                    #since we cannot use route -n
                    line = line.replace("via", "")
                    dest_ip, hop_ip, *_ = line.split()
                    if hop_ip == "dev":
                        hop_ip = dest_ip
                    dest_id = int(dest_ip.split(".")[-1])
                    hop_id = int(hop_ip.split(".")[-1])
                    self.all_routes[source_id, dest_id] = hop_id

        #generate route map file for each selected nodes:
        time_line("Creating files with routes summary - one per exp node")
        for exp_node in self.exp_nodes:
            result_name = self.run_root / f"ROUTES-{exp_node:02d}"
            line_start = "{} --".format(exp_node)
            time_line(f"creating {result_name}")
            with result_name.open("w") as result_file:
                for dest in self.node_ids:
                    line_to_write = line_start
                    src = exp_node
                    if dest != exp_node:
                        loop_detector = 0
                        while src != 0 and self.all_routes[src, dest] != dest:
                            next_hop = self.all_routes[src, dest]
                            line_to_write += " {} --".format(next_hop)
                            src = next_hop
                            loop_detector = loop_detector + 1
                            if loop_detector > len(self.node_ids):
                                #time_line(result_name)
                                #time_line("SAMPLE {}".format(sample))
                                #time_line(" dest : {}".format( dest))
                                #time_line("LOOP")
                                hops = line_to_write.split("--")
                                hops.remove('')
                                read_hops = []

                                for hop in hops:
                                    if int(hop) not in read_hops:
                                        read_hops.append(int(hop))
                                    else:
                                        read_hops.append(int(hop))
                                        #log_line(read_hops)
                                        line_to_write = "{} --".format(exp_node)
                                        read_hops.remove(read_hops[0])
                                        for i in read_hops:
                                            line_to_write += " {} --".format(i)
                                        line_to_write += " {} --".format("-1")
                                        #log_line(line_to_write)
                                        break
                                break
                        line_to_write += " {}".format(dest)
                        result_file.write(line_to_write+ "\n")


    def run_sampled(self):
        #Generating Src,Dest : next_hop  table
        time_line("Generation global sampled routing map")
        newdir = self.run_root / "SAMPLES"
        newdir.mkdir(parents=True, exist_ok=True)
        sample_num = -1
        goto_next_sample = False
        dict_maps = {0 : self.all_routes.copy()}
        for source_id in self.node_ids:
            file_name = self.run_root / f"ROUTE-TABLE-{source_id:02d}-SAMPLED"
            sample_num = -1
            time_line(f"Creating {file_name}")
            with file_name.open() as file_routes:
                for line in file_routes:
                    #time_line(line)
                    #time_line(file_name)
                    if "SAMPLE" in line:
                        if sample_num >= 0:
                            dict_maps[sample_num] = self.all_routes.copy()
                        sample_num = sample_num +1
                        goto_next_sample = False
                        try:
                            self.all_routes = dict_maps[sample_num].copy()
                        except KeyError:
                            self.reset()
                            dict_maps[sample_num] = self.all_routes.copy()
                    else:
                        #Batman has another way to display routes
                        #since we cannot use route -n
                        if not goto_next_sample:
                            try:
                                line = line.replace("via", "")
                                #log_line(sample_num)
                                #log_line(line)
                                dest_ip, hop_ip, *_ = line.split()
                                if hop_ip == "dev":
                                    hop_ip = dest_ip
                                dest_id = int(dest_ip.split(".")[-1])
                                hop_id = int(hop_ip.split(".")[-1])
                                self.all_routes[source_id, dest_id] = hop_id
                            except ValueError:
                                goto_next_sample = True
                dict_maps[sample_num] = self.all_routes.copy()
                #log_line(self.all_routes)

        #get sample num and write routing parsed to file sample num -1


        for exp_node in self.exp_nodes:
            result_name = (self.run_root / "SAMPLES"
                           / f"ROUTES-{exp_node:02d}-SAMPLE")
            line_start = "{} --".format(exp_node)
            time_line(f"Creating {result_name}")
            with result_name.open("w") as result_file:
                for sample in range(0, sample_num):
                    result_file.write("SAMPLE {}".format(sample) + "\n")
                    for dest in self.node_ids:
                        line_to_write = line_start
                        src = exp_node
                        if dest != exp_node:
                            loop_detector = 0
                            while src != 0 and dict_maps[sample][src, dest] != dest:
                                next_hop = dict_maps[sample][src, dest]
                                #log_line("------------------------------------")
                                #log_line("Source : {}".format(exp_node))
                                #time_line"Sample : {}".format(sample))
                                #time_lineresult_name)
                                #log_line("src : {} dest : {}".format(src, dest))
                                #time_line"next hop: {}".format(next_hop))
                                #time_line"------------------------------------")
                                line_to_write += " {} --".format(next_hop)
                                src = next_hop
                                loop_detector = loop_detector + 1
                                if loop_detector > len(self.node_ids):
                                    #log_line(result_name)
                                    #log_line("SAMPLE {}".format(sample))
                                    #log_line(" dest : {}".format( dest))
                                    #log_line("LOOP")
                                    hops = line_to_write.split("--")
                                    hops.remove('')
                                    read_hops = []

                                    for hop in hops:
                                        if int(hop) not in read_hops:
                                            read_hops.append(int(hop))
                                        else:
                                            read_hops.append(int(hop))
                                            #log_line(read_hops)
                                            line_to_write = "{} --".format(exp_node)
                                            read_hops.remove(read_hops[0])
                                            for i in read_hops:
                                                line_to_write += " {} --".format(i)
                                            line_to_write += " {} --".format("-1")
                                            #log_line(line_to_write)
                                            break
                                    break

                            line_to_write += " {}".format(dest)
                            result_file.write(line_to_write+ "\n")

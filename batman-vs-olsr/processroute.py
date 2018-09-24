# pylint: disable=c0111, r0914, r1702, r0912, r0915
"""
    Class to parse routing table of olsr and
    routing table of batman.
    Will be called at the end of one_run to generate
    a file containing the paths from the
    different nodes selected to do the pings from
"""

class ProcessRoutes:
    def __init__(self, run_root, exp_nodes, node_ids):
        self.run_root = run_root
        self.exp_nodes = exp_nodes
        self.node_ids = node_ids
        self.all_routes = {
            (source, destination): 0
            for source in node_ids for destination in node_ids if source != destination
        }

    def reset(self):
        self.all_routes = {
            (source, destination): 0
            for source in self.node_ids for destination in self.node_ids if source != destination
        }
    def run(self):
        #Generating Src,Dest : next_hop  table
        print("Generation global routing map")
        for source_id in self.node_ids:
            file_name = self.run_root / "ROUTE-TABLE-{:02d}".format(source_id)
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
        #print(self.all_routes)

        #generate route map file for each selected nodes:
        print("Creating files with routes summary for each selected experiment nodes")
        for exp_node in self.exp_nodes:
            result_name = self.run_root / "ROUTES-{:02d}".format(exp_node)
            line_start = "{} --".format(exp_node)
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
                                #print (result_name)
                                #print ("SAMPLE {}".format(sample))
                                #print(" dest : {}".format( dest))
                                #print("LOOP")
                                hops = line_to_write.split("--")
                                hops.remove('')
                                read_hops = []

                                for hop in hops:
                                    if int(hop) not in read_hops:
                                        read_hops.append(int(hop))
                                    else:
                                        read_hops.append(int(hop))
                                        #print (read_hops)
                                        line_to_write = "{} --".format(exp_node)
                                        read_hops.remove(read_hops[0])
                                        for i in read_hops:
                                            line_to_write += " {} --".format(i)
                                        line_to_write += " {} --".format("-1")
                                        #print (line_to_write)
                                        break
                                break
                        line_to_write += " {}".format(dest)
                        result_file.write(line_to_write+ "\n")


    def run_sampled(self):
        #Generating Src,Dest : next_hop  table
        print("Generation global routing map")
        print("Creating files with routes summary for each selected experiment nodes")
        newdir = self.run_root / "SAMPLES"
        newdir.mkdir(parents=True, exist_ok=True)
        sample_num = -1
        goto_next_sample = False
        dict_maps = {0 : self.all_routes.copy()}
        for source_id in self.node_ids:
            file_name = self.run_root / "ROUTE-TABLE-{:02d}-SAMPLED".format(source_id)
            sample_num = -1
            with file_name.open() as file_routes:
                for line in file_routes:
                    #print(line)
                    #print (file_name)
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
                                # print (sample_num)
                                #print(line)
                                dest_ip, hop_ip, *_ = line.split()
                                if hop_ip == "dev":
                                    hop_ip = dest_ip
                                dest_id = int(dest_ip.split(".")[-1])
                                hop_id = int(hop_ip.split(".")[-1])
                                self.all_routes[source_id, dest_id] = hop_id
                            except ValueError:
                                goto_next_sample = True
                dict_maps[sample_num] = self.all_routes.copy()
                #print(self.all_routes)

        #get sample num and write routing parsed to file sample num -1


        for exp_node in self.exp_nodes:
            result_name = (self.run_root / "SAMPLES"
                           / "ROUTES-{:02d}-SAMPLE".format(exp_node))
            line_start = "{} --".format(exp_node)
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
                                #print("------------------------------------")
                                #print("Source : {}".format(exp_node))
                                #print ("Sample : {}".format(sample))
                                #print (result_name)
                                #print("src : {} dest : {}".format(src, dest))
                                #print ("next hop: {}".format(next_hop))
                                #print("------------------------------------")
                                line_to_write += " {} --".format(next_hop)
                                src = next_hop
                                loop_detector = loop_detector + 1
                                if loop_detector > len(self.node_ids):
                                    #print (result_name)
                                    #print ("SAMPLE {}".format(sample))
                                    #print(" dest : {}".format( dest))
                                    #print("LOOP")
                                    hops = line_to_write.split("--")
                                    hops.remove('')
                                    read_hops = []

                                    for hop in hops:
                                        if int(hop) not in read_hops:
                                            read_hops.append(int(hop))
                                        else:
                                            read_hops.append(int(hop))
                                            #print (read_hops)
                                            line_to_write = "{} --".format(exp_node)
                                            read_hops.remove(read_hops[0])
                                            for i in read_hops:
                                                line_to_write += " {} --".format(i)
                                            line_to_write += " {} --".format("-1")
                                            #print (line_to_write)
                                            break
                                    break

                            line_to_write += " {}".format(dest)
                            result_file.write(line_to_write+ "\n")

"""
    Class to parse routing table of olsr and
    routing table of batman.
    Will be called at the end of onerun to generate
    a file containing the paths from the
    different nodes selected to do the pings from
"""
class ProcessRoutes:
    def __init__(self, run_root, exp_nodes, node_ids):
        self.run_root=run_root
        self.exp_nodes=exp_nodes
        self.node_ids=node_ids
        self.Allroutes = {
            (source, destination): 0
            for source in node_ids for destination in node_ids if source != destination
        }

    def reset(self):
        self.Allroutes = {
            (source, destination): 0
            for source in self.node_ids for destination in self.node_ids if source != destination
        }
    def run(self):
        #Generating Src,Dest : next_hop  table
        print ("Generation global routing map")
        for source_id in self.node_ids:
            file_name= self.run_root / "ROUTE-TABLE-{:02d}".format(source_id)
            with file_name.open() as file_routes:
                for line in file_routes:
                    #Batman has another way to display routes
                    #since we cannot use route -n
                    line=line.replace("via", "")
                    dest_ip, hop_ip, *other= line.split()
                    if hop_ip == "dev":
                        hop_ip=dest_ip
                    dest_id = int(dest_ip.split(".")[-1])
                    hop_id = int(hop_ip.split(".")[-1])
                    self.Allroutes[source_id, dest_id]= hop_id
        #print(self.Allroutes)

        #generate route map file for each selected nodes:
        print("Creating files with routes summary for each selected experiment nodes")
        for e in self.exp_nodes:
            result_name= self.run_root / "ROUTES-{:02d}".format(e)
            line_start= "{} --".format(e)
            with result_name.open("w") as result_file:
                for dest in self.node_ids:
                    line_to_write = line_start
                    src = e
                    if dest != e:
                        loop_detector = 0
                        while( src !=0 and self.Allroutes[src, dest] != dest ):
                            next_hop = self.Allroutes[src, dest]
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
                                        line_to_write = "{} --".format(e)
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
        print ("Generation global routing map")
        print("Creating files with routes summary for each selected experiment nodes")
        newdir = self.run_root / "SAMPLES"
        newdir.mkdir(parents= True, exist_ok = True)
        sampleNum= -1
        goToNextSample = False
        dict_maps = {0 : self.Allroutes.copy()}
        for source_id in self.node_ids:
            file_name= self.run_root / "ROUTE-TABLE-{:02d}-SAMPLED".format(source_id)
            sampleNum = -1
            with file_name.open() as file_routes:
                for line in file_routes:
                    #print(line)
                    #print (file_name)
                    if "SAMPLE" in line:
                        if sampleNum >= 0:
                            dict_maps[sampleNum] = self.Allroutes.copy()
                        sampleNum = sampleNum +1
                        goToNextSample = False
                        try:
                            self.Allroutes = dict_maps[sampleNum].copy()
                        except KeyError:
                            self.reset()
                            dict_maps[sampleNum] = self.Allroutes.copy()
                    else:
                        #Batman has another way to display routes
                        #since we cannot use route -n
                        if not goToNextSample:
                            try:
                                line=line.replace("via", "")
                                # print (sampleNum)
                                #print( line)
                                dest_ip, hop_ip, *other= line.split()
                                if hop_ip == "dev":
                                    hop_ip=dest_ip
                                dest_id = int(dest_ip.split(".")[-1])
                                hop_id = int(hop_ip.split(".")[-1])
                                self.Allroutes[source_id, dest_id]= hop_id
                            except ValueError:
                                goToNextSample = True
                dict_maps[sampleNum] = self.Allroutes.copy()
                #print(self.Allroutes)

        #get sample num and write routing parsed to file sample num -1
        
        
            
        for e in self.exp_nodes:
            result_name= self.run_root / "SAMPLES" /"ROUTES-{:02d}-SAMPLE"\
                .format(e)
            line_start= "{} --".format(e)
            with result_name.open("w") as result_file:
                for sample in range(0, sampleNum):
                    result_file.write("SAMPLE {}".format(sample) + "\n")
                    for dest in self.node_ids:
                        line_to_write = line_start
                        src = e
                        if dest != e:
                            loop_detector = 0
                            while( src !=0 and dict_maps[sample][src, dest] != dest ):
                                next_hop = dict_maps[sample][src, dest]
                                #print("------------------------------------")
                                #print("Source : {}".format(e))
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
                                            line_to_write = "{} --".format(e)
                                            read_hops.remove(read_hops[0])
                                            for i in read_hops:
                                                line_to_write += " {} --".format(i)
                                            line_to_write += " {} --".format("-1")
                                            #print (line_to_write)
                                            break
                                    break
                        
                            line_to_write += " {}".format(dest)
                            result_file.write(line_to_write+ "\n")



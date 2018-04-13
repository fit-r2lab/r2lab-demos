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
                        while( src !=0 and self.Allroutes[src, dest] != dest ):
                            next_hop = self.Allroutes[src, dest]
                            line_to_write += " {} --".format(next_hop)
                            src = next_hop
                        line_to_write += " {}".format(dest)
                        result_file.write(line_to_write+ "\n")


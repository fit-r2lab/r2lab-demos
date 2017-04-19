class Averager:
    """
    For each couple (receiver, sender) we gather
    a number of measurement points that must be averaged

    this is done through an instance of this Averager class
    all measurement points will contain one, two or three values
    depending on the number of antennas

    each measurement point is recorded, and at the end
    averages returns the right value(s)
    """
    def __init__(self, columns):
        self.number = 0
        self.columns = columns
        self.total = [0 for i in range(self.columns)]

    def record_point(self, values):
        """
        values should have as many measurements as columns
        """
        self.number += 1
        for i in range(self.columns):
            self.total[i] += values[i]

    def averages(self, default):
        if self.number == 0:
            return [ default for i in range(self.columns) ]
        else:
            return [ self.total[i]/self.number for i in range(self.columns)]

class Aggregator:

    # we could also count the ones in a binary form
    mask_to_number = { 1: 1, 3: 2, 7: 3, }

    RSSI_MAX = 0
    RSSI_MIN = -100

    def __init__(self, run_root, node_ids, antenna_mask):
        # a pathlib Path
        self.run_root = run_root
        self.node_ids = node_ids
        self.antenna_mask = antenna_mask
        self.nb_antennas = self.mask_to_number[antenna_mask]
        # internal result is a dicted hashed on
        # a sender, receiver tuple
        # value is a counter how_many, total
        self.RSSI = {
            (sender, receiver) : Averager(self.nb_antennas + 1)
            for sender in node_ids for receiver in node_ids
        }

    def run(self):
        for sender in self.node_ids:
            result_name = self.run_root / "result-{}.txt".format(sender)
            with result_name.open() as result_file:
                for line in result_file:
                    sender_ip, receiver_ip, comma_rssis = line.split()
                    sender_id = int(sender_ip.split('.')[-1])
                    receiver_id = int(receiver_ip.split('.')[-1])
                    rssis = [int(x) for x in comma_rssis.split(',')]
                    averager = self.RSSI[sender_id, receiver_id]
                    averager.record_point(rssis)
        
        # consolidated file is called RSSI.txt
        aggragate_name = self.run_root / "RSSI.txt"
        with aggragate_name.open("w") as aggregate_file:
            for (sender, receiver), averager in self.RSSI.items():
                default = self.RSSI_MAX if sender == receiver else self.RSSI_MIN
                avgs = averager.averages(default=default)
                line = "10.0.0.{:02d}\t10.0.0.{:02d}\t".format(sender, receiver)
                line += "\t".join("{0:.2f}".format(v) for v in avgs)
                aggregate_file.write(line + "\n")


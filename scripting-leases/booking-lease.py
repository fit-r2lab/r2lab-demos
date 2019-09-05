#!/usr/bin/env python3

import time
from datetime import datetime
from xmlrpc.client import ServerProxy

from argparse import ArgumentParser


# enter your credentials and details here

# use command line to set these
# account = "thierry.parmentelat@inria.fr"
# password = "your password here"
# slicename = "inria_r2lab.nightly"

# use command line to set these
# readable_from  = "2019-09-03T04:00:00"
# readable_until = "2019-09-03T05:00:00"

# end of editable part


#######

####### only utilities to use pretty timestamps instead of raw epochs

# epoch to and from readable timestamp
timeformat = "%Y-%m-%dT%H:%M:%S"

def readable_to_epoch(string):
    return int(datetime.strptime(string, timeformat).timestamp())

def epoch_to_readable(epoch):
    return f"{time.strftime(timeformat, time.localtime(epoch))}"


### 
r2lab_url = "https://r2labapi.inria.fr/PLCAPI/"

# where to send API calls
proxy = ServerProxy(r2lab_url, allow_none=True)

# expected by all API calls
def build_api_auth(account, password):
    return { 
        'Username' : account,
        'AuthString' : password,
        'AuthMethod' : 'password',
    }

def print_future_leases(account, password):

    auth = build_api_auth(account, password)
    
    leases = proxy.GetLeases(auth, {'day': 0})

    for lease in leases:
        print(f"{epoch_to_readable(lease['t_from'])} "
              f"→ {epoch_to_readable(lease['t_until'])} "
              f" by slice {lease['name']}")


def book_lease(account, password, slicename, t_from, t_until):

    auth = build_api_auth(account, password)

    retcod = proxy.AddLeases(
        auth,
        'faraday.inria.fr',  # only one node on R2lab
        slicename,
        t_from,   # must be an integer epoch
        t_until, # ditto
    )
    if retcod['errors']:
        print(retcod['errors'])
    else:
        print(f"new lease (id={retcod['new_ids'][0]}) OK")


def main():
    parser = ArgumentParser()

    # mode: show current leases or book a new one
    parser.add_argument(
        "-g", "--get-leases", dest='get', action='store_true', default=False,
        help="use this option to display current leases; default if none of -g or -b are given")
    parser.add_argument(
        "-b", "--book-lease", dest='book', action='store_true', default=False,
        help="use this option to book a lease; from, until and slicename required")

    # required for booking
    parser.add_argument(
        "-f", "--from", dest='t_from',
        help="start of lease to book, local time, format 2020-12-32T21:30:00")
    parser.add_argument(
        "-u", "--until", dest='t_until',
        help="end of lease to book, same format as --from")
    parser.add_argument(
        "-s", "--slice", dest='slicename',
        help="slicename to use when booking"
    )

    # mandatory
    parser.add_argument("account", 
                        help="your individual account name at r2lab")
    parser.add_argument("password", 
                        help="associated password on r2lab")

    args = parser.parse_args()
    
    # mode
    if not args.get and not args.book:
        args.get = True
        
    if args.get:
        print_future_leases(args.account, args.password)
        
    if args.book:
        book_lease(
            args.account, args.password, args.slicename, 
            readable_to_epoch(args.t_from),
            readable_to_epoch(args.t_until),
        )

if __name__ == '__main__':
    main()
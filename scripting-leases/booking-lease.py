#!/usr/bin/env python3

# enter your credentials and details here

account = "thierry.parmentelat@inria.fr"
password = "your password here"
slicename = "inria_r2lab.nightly"

readable_from  = "2019-09-03T04:00:00"
readable_until = "2019-09-03T05:00:00"

# end of editable part


#######

import time
from datetime import datetime
from xmlrpc.client import ServerProxy


####### only utilities to use pretty timestamps instead of raw epochs

# epoch to and from readable timestamp
timeformat = "%Y-%m-%dT%H:%M:%S"

def readable_to_epoch(string):
    return int(datetime.strptime(string, timeformat).timestamp())

def epoch_to_readable(epoch):
    return f"{time.strftime(timeformat, time.localtime(epoch))}"


### 
r2lab_url = "https://r2labapi.inria.fr/PLCAPI/"


# expected by all API calls
auth = { 
    'Username' : account,
    'AuthString' : password,
    'AuthMethod' : 'password',
}

# where to send API calls
proxy = ServerProxy(r2lab_url, allow_none=True)



def print_future_leases():

    leases = proxy.GetLeases(auth, {'day': 0})

    for lease in leases:
        print(f"{epoch_to_readable(lease['t_from'])} "
              f"→ {epoch_to_readable(lease['t_until'])} "
              f" by slice {lease['name']}")

print_future_leases()



def book_lease(t_from, t_until, slicename):

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
        print(f"new lease OK, id={retcod['new_ids'][0]}")

book_lease(
    readable_to_epoch(readable_from),
    readable_to_epoch(readable_until),
    slicename,
)
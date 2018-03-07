#!/usr/bin/env python3

"""
This is an extension to the argparse ecosystem

Purpose is to enable the creation of CLI options that would behave like
action=append, but with a check on choices

(*) accumulative : *dest* holds a list of strings - it's possible to use the type system as well
(*) restrictive : all elements in the list must be in *choices*
(*) optionnally resetable : it should be possible for add_argument to specify a non-void default
    and in this case we need a means for the CLI to explicitly void the value

In practical terms, we want to specify one or several values for a parameter
that is itself constrained, like an antenna mask that must be among '1', '3' and '7'

As of this writing at least, using 'append' as an action won't work
it is possible to write a code that uses
action=append, choices=['a', 'b', 'c'] and default=['a', 'b']
but then defaults are always returned...

Resetting:

The actual syntax offered by your CLI for actually resetting may vary from one need to another

e.g. my first use case is with phones in oai-scenario.py
first off, the code is written so that type=int, i.e. with dest=`phones` we constrain
args.phones to be a list of ints, and actually in the 1-2 range

So we'd like to have
* no option: phones = [1]
* -p 2:      phones = [2]
* -p 1 -p 2: phones = [1, 2]
* -p 0:      phones = []

It is not possible to adopt a convention where
* -p none    would mean phones = []
because we have this type = int setting to add_argument, which causes none to be rejected
as an input; and it feels wrong to have to change all the code using `phones`
"""

import argparse


class ListOfChoices(argparse.Action):

    """
    The generic class assumes there is a means_resetting method
    that is used to check for special incoming values that mean resetting

    Use with e.g.
        parser.add_argument(choices=('1', '2', '3', '4'), default=['1', '2'],
                            typeaction=ListOfChoices)
    """

    def __init__(self, *args, **kwds):
        # initialize list of arguments
        self.result = []
        # initialize superclass
        super().__init__(*args, **kwds)

    def means_resetting(self, value):
        """
        Override this method if you want special values to mean resetting
        """
        return False

    def __call__(self, parser, namespace, value, option_string=None):
        # check if this means resetting
        if self.means_resetting(value):
            self.result = []
        else:
            self.result.append(value)
        # in any case
        setattr(namespace, self.dest, self.result)


class ListOfChoicesNegativeReset(ListOfChoices):

    """
    Use with e.g.
        parser.add_argument(choices=(1, 2, 3, 0), type=int,
                            default=[1],
                            typeaction=ListOfChoicesNegativeReset)
    and then run with -p 0 to reset
    """
    def means_resetting(self, value):
        return value <= 0


# unit test
if __name__ == '__main__':
    def test1():
        """
        ListOfChoices micro-test
        """
        def new_parser():
            parser=argparse.ArgumentParser(
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
            parser.add_argument("-a", "--antenna-mask", default=['1', '1'],
                                choices=['1', '3', '7', '11'],
                                action=ListOfChoices,
                                help="specify antenna mask for each node")
            return parser

        print(new_parser().parse_args())
        print(new_parser().parse_args([]))
        print(new_parser().parse_args(['-a', '1']))
        print(new_parser().parse_args(['-a', '1', '-a', '3']))
        print(new_parser().parse_args(['-a', '1', '-a', '3', '-a', '11']))

    def test2():
        """
        ListOfChoices micro-test for phones
        """
        def new_parser():
            parser=argparse.ArgumentParser(
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
            parser.add_argument("-p", "--phones", default=[1],
                                choices=(1, 2, 3, 0),
                                type=int,
                                action=ListOfChoicesNegativeReset,
                                help="specify phones")
            return parser

        print(new_parser().parse_args())
        print(new_parser().parse_args([]))
        print(new_parser().parse_args(['-p', '1']))
        print(new_parser().parse_args(['-p', '1', '-p', '2']))
        print(new_parser().parse_args(['-p', '1', '-p', '3']))
        print(new_parser().parse_args(['-p', '0']))

    test1()
    test2()

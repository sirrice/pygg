# This isn't safe at all.  __init__.py is loaded when
# you do an import pygg.  Are you trying to automatically
# bring in all of the individual symbols?  If so, that's not a good
# idea in general.  Let's discuss but disabling now
# from pygg import *

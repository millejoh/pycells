#!/usr/bin/env python

"""
PyCells Tutorials, part two: Observers

In this tutorial I'll extend the Model with Observers, which are bits
of code that get called when the Model is updated. Observers can be
set to run when the whole Model updates, when a specific Cell updates,
or when a value matches a given condition.
"""

import cells
# I'm just going to grab the Rectangle from part one:
from basic import Rectangle, GOLDEN

# Now, we can use one of cells.Model's class methods, observer, to add
# an observer to the Rectangle:
@Rectangle.observer()		# Without arguments, this Observer attaches to
				# the whole Model. It will be run whenever any
				# Cell in the Model updates
def rectangle_observer(self):	# 'self' here refers to the Rectangle instance
    print "The rectangle updated!"

# As I said, Observers may be attached to specific Cell attributes:
@Rectangle.observer(attrib="ratio")
def ratio_obs(self):
    # Note, here, that observers have access to the Model instance
    # just like a Rule Cell does
    print "The ratio of the rectangle is now", self.ratio

# One more like the ratio observer, but with the area:
@Rectangle.observer(attrib="area")
def area_obs(self):
    print "The area of the rectangle is now", self.area

# We can also act on the model with Observers, with some caveats.
# Let's say we want to reset the ratio to the default (the golden
# ratio) if it's set to a value below 0. We can do this with an
# observer. First, I'll make a function to test for below-zeroness:
def subzero(value):		# The signature for value tests is
				# f(value) (depending on what the test
				# is attached to, this could be the
				# out-of-date or up-to-date value for the cell.
    return value < 0	        # It returns a boolean to say whether the 
				# observer should run on this cell

# Now I'll add another observer, looking for an attribute named
# "ratio" and an up-to-date value which passes the subzero test:
@Rectangle.observer(attrib="ratio", newvalue=subzero)
def zeroratio_observer(self):	# and if it's run
    print "Woah, that's not a legal ratio! Resetting to default."
    self.ratio = GOLDEN		# reset the ratio to the golden ratio

# So, in order to show the problems with the observer method, I'll
# need to run an instance of the Rectangle:
if __name__ == "__main__":
    print "Making a new Rectangle"
    r = Rectangle()		# makes a new Rectangle instance.
    # This will trigger the whole-model observer and the ratio & area observers:
    #    >>> from observers import Rectangle
    #    >>> r = Rectangle()
    #    The rectangle updated!
    #    The area of the rectangle is now 1.618
    #    The ratio of the rectangle is now 1.618    

    print "Setting ratio to 4"
    # Now, let's test the default-ratio observer:
    r.ratio = 4
    # This will not pass the subzero test, so that observer won't fire:
    #    >>> r.ratio = 4
    #    The rectangle updated!
    #    The area of the rectangle is now 4.0

    print "Setting ratio to -3"
    r.ratio = -3
    # This will pass the subzero test, firing the observer:
    #     >>> r.ratio = -3
    #     The rectangle updated!
    #     Woah, that's not a legal ratio! Resetting to default.
    #     The area of the rectangle is now -3.0
    #     The rectangle updated!
    #     The area of the rectangle is now 1.618
    
    # It worked ... but the area changed to -3.0 before the ratio
    # reset!  What the heck? Well, in order to preserve the integrity
    # of an update, they happen atomically -- so, each assignment to
    # an InputCell matches up with a single update to the cells
    # environment. When the observer sets the rectangle's ratio to the
    # golden ratio, that set is deferred until the current update to
    # -3 is finished. The -3 propgation makes the area change to -3,
    # firing area's observer. After that propgation finishes, the set
    # back to the golden ratio happens and the model propgates that
    # change through the system.

    # So observers changing cells may lead to somewhat unexpected
    # behavior. Make sure you know what's going on in your system
    # before you start adding observers that change the Model they
    # observe.

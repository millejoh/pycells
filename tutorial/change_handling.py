#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

# So automatically running functions and updating values is all well
# and good, but sometimes we need to fire off external events. Enter
# observers.  First, we build another model object, same as before:
class Rectangle(cells.ModelObject):
    @cells.fun2cell()
    def length(self, prev): return self.width * 2
    
    width = cells.makecell(name="width")

    def _widthcalc(self, prev): return self.length / 2

    def __init__(self, width=_widthcalc, *args, **kwargs):
        cells.ModelObject.__init__(self, width=width, *args, **kwargs)

# now we can attach an observer to the length cell. Whenever length
# changes, this observer will fire. The ModelObject.observer class
# method takes the name of the cell for the observer to be attached
# to:
@Rectangle.observer("length")
# The observers have a specific signature. `modelobj` is a reference
# to the modelobject instance this observer's cell is embedded in;
# `new` is the new value of the cell; `old` is the old value of the
# cell; `bound` is a boolean stating whether the cell was bound
# previously.
def len_observer(modelobj, new, old, bound):
    global GUI_TOLD                     # we'll just reset some external var
    GUI_TOLD = True                     # to show this is firing appropriately
    
class Test(unittest.TestCase):
    testnum = "01b"

    def runTest(self):
        # First, set up the environment:
        global GUI_TOLD
        GUI_TOLD = False
        rect = Rectangle(length=42)     # we're overriding the length cell again

        # since the length changed (from uninitialized to
        # initialized), the observer should have fired, and the
        # previous behavior for width remains:
        self.failUnless(GUI_TOLD)
        self.failUnless(rect.width == 21)

        # Okay, it happened on init ... but will it happen again?
        GUI_TOLD = False

        # Set length again ...
        rect.length = 1000
        self.failUnless(rect.length == 1000)

        # and (surprise!) the observer fired again.
        self.failUnless(GUI_TOLD)
        self.failUnless(rect.width == 500)

if __name__ == "__main__":
    # if we're running as a main, rather than a test, we can use a
    # slightly chattier observer. Note that this is another observer,
    # rather than a replacement observer, on the length cell.
    @Rectangle.observer("length")
    def another_len_observer(new, old, bound):
        print "Tell GUI about", str(new), str(old), str(bound)

    rect = Rectangle(length=42)
    rect.length = 42                    # --> Tell GUI about 42 None False
    rect.length = 1000                  # --> Tell GUI about 1000 42 True


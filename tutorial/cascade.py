#!/usr/bin/env python

import unittest, sys, math
sys.path += "../"
import cells

MAIN = False

# So far, the dependency graphs have been fairly simple. Width
# depended on length, full stop. What if we build something a bit
# harder? In this case, we have a dependency graph whose depth is
# larger than one, and which has multiple paths:
#
# (Please note:
#  a <-- b means a depends on b, or a's function calls b)
#
# brightness <-- area <-- width <-- len
#                  ^-----------------/
class Rectangle(cells.ModelObject):
    @cells.fun2cell()
    def length(self, prev):
        return 2 * self.width
    
    @cells.fun2cell()
    def width(self, prev):
        return math.floor(self.length / 2)

    @cells.fun2cell()
    def area(self, prev):
        return self.length * self.width

    @cells.fun2cell()
    def brightness(self, prev):
        return math.floor(self.lumens / self.area)

    def __init__(self, *args, **kwargs):
        self.lumens = 1000000
        cells.ModelObject.__init__(self, *args, **kwargs)

        
class Test(unittest.TestCase):
    testnum = "01c"

    def runTest(self):
        # So hopefully we can just make an instance of our model
        if MAIN: print "Instantiating a Rectangle w/ length 100"
        rect = Rectangle(length=100)
        if MAIN:
            print "width:", rect.width
            print "area:", rect.area
            print "brightness:", rect.brightness

        # And test it like before
        self.failUnless(rect.width == 50)
        self.failUnless(rect.area == 5000)
        self.failUnless(rect.brightness == 200)

        if MAIN: print "Setting Rectangle's length to 1000"
        rect.length = 1000
        if MAIN:
            print "width:", rect.width
            print "area:", rect.area
            print "brightness:", rect.brightness

        # And everything should propogate as we expect it to...
        self.failUnless(rect.length ==  1000)
        self.failUnless(rect.width == 500)
        self.failUnless(rect.area ==  500000)
        self.failUnless(rect.brightness == 2)
        # The fact that area only calculated once, even though it was
        # told it needed to twice (once by length's change, once by
        # width's change), won't be proved here. (Later, we will prove
        # this property.)

if __name__ == "__main__":
    MAIN = True
    Test().runTest()

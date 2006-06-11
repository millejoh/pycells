#!/usr/bin/env python

import unittest, sys
sys.path += "../"
import cells

class Rectangle(cells.ModelObject):
    @cells.fun2cell()
    def length(self, prev):
        return 2 * self.width

    @cells.fun2cell()
    def width(self, prev):
        return self.length / 2

    @cells.fun2cell()
    def area(self, prev):
        return self.length * self.width

    @cells.fun2cell()
    def brightness(self, prev):
        return self.lumens / self.area

    def __init__(self, *args, **kwargs):
        self.lumens = 1000000
        cells.ModelObject.__init__(self, *args, **kwargs)

        
class Test(unittest.TestCase):
    testnum = "01c"

    def runTest(self):
        rect = Rectangle(length=100)
        self.failUnless(rect.width == 50)
        self.failUnless(rect.area == 5000)
        self.failUnless(rect.brightness == 200)

        rect.length = 1000
        self.failUnless(rect.length == 1000)
        self.failUnless(rect.area == 500000)
        self.failUnless(rect.brightness == 2)


if __name__ == "__main__":
    print "Instantiating a Rectangle w/ length 100"
    rect = Rectangle(length=100)
    print "width:", rect.width
    print "area:", rect.area
    print "brightness:", rect.brightness

    print "Setting Rectangle's length to 1000"
    rect.length = 1000
    print "width:", rect.width
    print "area:", rect.area
    print "brightness:", rect.brightness

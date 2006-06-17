#!/usr/bin/env python

import unittest, sys, math
sys.path += "../"
import cells

MAIN = False
runlog = []

class Point(object):
    """Silly little point structure"""
    def __init__(self, x, y):
        self.x, self.y = x, y

    def inside(self, box):
        """Returns true if this Point is inside passed Box"""
        return (box.left <= self.x and box.right > self.x and
                box.bottom <= self.y and box.top > self.y)

    def __eq__(self, point):
        return (self.x == point.x) and (self.y == point.y)


class Box(object):
    """Silly little box structure"""
    def __init__(self, l, t, r, b):
        self.left, self.right, self.top, self.bottom = l, r, t, b

    def __eq__(self, box):
        return ((box.left == self.left) and (box.right == self.right) and
                (box.top == self.top) and (box.bottom == self.bottom))

    def __str__(self):
        return str((self.left, self.top, self.right, self.bottom))

        
class Rectangle(cells.ModelObject):
    click = cells.makecell(name="click", type=cells.EphemeralCell)
    bounding_box = cells.makecell(name="bounding_box")

    @cells.fun2cell(type=cells.EphemeralCell)
    def clicked(self, prev):
        # figure out if the clicked point is in the bounding_box
        return self.click.inside(self.bounding_box)

    
@Rectangle.observer("click")
def click_observer(modelobj, new, old, oldbound):
    if new:
        if MAIN: print "Resetting bounding box!"
        modelobj.set_with_integrity("bounding_box",
                                    Box(-1000, 1000, 1000, -1000))

@Rectangle.observer("clicked")
def clicked_observer(modelobj, new, old, oldbound):
    if new:
        if MAIN: print "The Rectangle was clicked!"
        global runlog    
        runlog.append("clicked")

def rect_props(rect):
    buff = "Rectangle Properties:\n"
    buff += "Bounding box: " + str(rect.bounding_box)
    buff += "\n"
    return buff
    
class Test(unittest.TestCase):
    testnum = "03"
    def runTest(self):
        global runlog

        if MAIN: print "Building rectangle"
        rect = Rectangle(bounding_box=Box(10, 10, 20, 20))
        runlog = []
        if MAIN:
            print rect_props(rect)
            print "run log: ", str(runlog)

        if MAIN: print "Clicking in rectangle"
        rect.click = Point(0, 0)
        if MAIN:
            print rect_props(rect)
            print "run log: ", str(runlog)
        
        self.failIf(Point(0, 0).inside(Box(10, 10, 20, 20)))
        self.failUnless(Point(0, 0).inside(rect.bounding_box))
        self.failIf("clicked" in runlog)


if __name__ == "__main__":
    MAIN = True
    t = Test()
    t.runTest()

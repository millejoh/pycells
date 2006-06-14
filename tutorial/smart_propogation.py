#!/usr/bin/env python

import unittest, sys, math
sys.path += "../"
import cells

runlog = []
MAIN = False

class Rectangle(cells.ModelObject):
    @cells.fun2cell()
    def length(self, prev):
        runlog.append("length")
        return 2 * self.width

    @cells.fun2cell()
    def width(self, prev):
        runlog.append("width")
        return math.floor(self.length / 2)

    @cells.fun2cell()
    def padded_width(self, prev):
        runlog.append("padded_width")
        return self.width + 10

def rect_attribs(rect):
    buff = "Rectangle attributes:\n" 
    buff += "       Width = "+ str(rect.width)
    buff += "\n      Length = "+ str(rect.length)
    buff += "\nPadded Width = "+ str(rect.padded_width)
    buff += "\nRun Log:"+ str(runlog)
    return buff


class Test(unittest.TestCase):
    testnum = "02"
    
    def runTest(self):
        global runlog
        
        # add an observer which will fail the test if width's old == new
        @cells.observer(Rectangle, "width")
        def width_observer(modelobj, new, old, wasbound):
            global runlog
            self.failIf(new == old)
            if MAIN: print "Observing width. Is", str(new) + ", was", str(old)
            runlog.append("width_observer")

        # and a plain-old observer on length
        @cells.observer(Rectangle, "length")
        def length_observer(modelobj, new, old, wasbound):
            global runlog
            runlog.append("length_observer")

        # instantiate the Rectangle
        if MAIN: print "Instantiating Rectangle"
        rect = Rectangle(length=42)
        self.failUnless(rect.width == 21)
        if MAIN: print rect_attribs(rect)

        # check setting a cell doesn't propogate needlessly:
        runlog = []
        rect.length = 42                  # length doesn't change
        if MAIN:
            print "Setting length to 42\n"
            print rect_attribs(rect)
        
        self.failUnless(rect.width == 21) # width doesn't either
        # the following set should not have been recalc'd by that:
        uncalcd = [ "length_observer", "width", "width_observer",
                    "padded_width" ]
        for it in uncalcd:
            if MAIN: print it, "should not have been run"
            self.failIf(it in runlog)

        # check setting a cell doesn't propogate needlessly if intermediate
        # values don't change:
        runlog = []
        rect.length = 43                  # length changes
        if MAIN:
            print "Setting length to 43\n"
            print rect_attribs(rect)

        self.failUnless(rect.width == 21) # but width doesn't (floor truncates)
        # the following set should not have been recalc'd by that:
        uncalcd = [ "width_observer", "padded_width" ]
        for it in uncalcd:
            if MAIN: print it, "should not have been run"
            self.failIf(it in runlog)
        # the following set should have been recalc'd by that:
        calcd = [ "width", "length_observer" ]
        for it in calcd:
            if MAIN: print it, "should have been run"
            self.failIf(it not in runlog)

        # check setting a cell that should recalc does:
        runlog = []
        rect.length = 44                  # length changes
        if MAIN:
            print "Setting length to 44\n"
            print rect_attribs(rect)

        self.failUnless(rect.width == 22) # but width doesn't (floor truncates)
        # the following set should have been recalc'd by that:
        calcd = [ "length_observer", "width", "width_observer", "padded_width" ]
        for it in calcd:
            if MAIN: print it, "should have been run"
            self.failIf(it not in runlog)

            
if __name__ == "__main__":
    MAIN = True
    t = Test()
    t.runTest()

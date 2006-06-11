import unittest, sys

sys.path += "../"

import cells, math

class Circle(cells.ModelObject):
    @cells.fun2cell()
    def circumference(self, prev):
        return self.radius * 2

    @cells.fun2cell()
    def radius(self, prev):
        return self.circumference / 2

    @cells.fun2cell()
    def area(self, prev):
        return math.floor(math.pi * (self.radius ** 2))


class Test(unittest.TestCase):
    testnum = "01b"

    def runTest(self):
        c = Circle()
        c.circumference = 6

        self.failUnless(c.radius == 3)
        self.failUnless(c.area == math.floor(math.pi * 9))

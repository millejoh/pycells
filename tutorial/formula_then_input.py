#!/usr/bin/env python

import unittest, sys, math
sys.path += "../"
import cells

MAIN = False
db = {}

def get_age(id):
    return db[id].age

class Person(object):
    def __init__(self, name, age): self.name, self.age = name, age
    def __str__(self):
        return " ".join(("Name:", self.name, "Age:", str(self.age)))


class RyanView(cells.ModelObject):
    @cells.fun2cell(type=cells.RuleThenValueCell)
    def age(self, prev):
        return get_age("Ryan") - self.grecian_formula_amt

    grecian_formula_amt = cells.makecell(name="grecian_formula_amt", value=7)
    
        
class Test(unittest.TestCase):
    testnum = "04"

    def runTest(self):
        db["Ryan"] = Person("Ryan Forsythe", 27)
        db["Ken"] = Person("Ken Tilton", 54)
        if MAIN:
            print "Database:\n", "\n".join([ ": ".join((key, str(value))) for
                                             key, value in db.iteritems() ])
            
        rv = RyanView()
        if MAIN: print "RyanView's age is", rv.age
        self.failUnless(20 == rv.age)

        if MAIN: print "Attempting to look younger by upping grecian formula..."
        rv.grecian_formula_amt = 10
        if MAIN: print "But RyanView's age is still", rv.age
        self.failUnless(20 == rv.age)

        if MAIN:
            print "Then October 17 rolls around, and Ryan gets a little older"
        rv.age += 1
        if MAIN: print "RyanView's age is", rv.age
        self.failUnless(21 == rv.age)
        

if __name__ == "__main__":
    MAIN = True
    Test().runTest()
    

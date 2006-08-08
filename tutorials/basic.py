#!/usr/bin/env python

"""
PyCells Tutorials, part one: The Basics

I'm just going to do a really basic cells application here,
introducing the syntax of PyCells and some of the concepts you'll need
to keep in mind while using cells.

I'll build a model of a rectangle which will take a width and an
aspect ratio, and make available the calculated length and area.
"""

# First, we'll import cells:
import cells

GOLDEN = 1.618

# The next step is building the model. It's a normal class, but
# extends cells.Model. cells.Model.__init__ will take care of building
# all the support structures within the model for the model's cells to
# work properly:
class Rectangle(cells.Model):
    # Now let's add a cell to our model. This will be an Input cell,
    # which can be set from outside the Model:
    width = cells.makecell(value=1)
    # I didn't specify an InputCell (though I could have);
    # cells.makecell will create an InputCell if it gets a value
    # argument.

    # Similarly, we can make the aspect ratio cell:
    ratio = cells.makecell(value=GOLDEN)

    # Now, I make the cell which gives the calculated length. It's
    # called a Rule cell, and I can make it like this:
    @cells.fun2cell()
    def length(self, prev):
	# The signature of the rule which defines a RuleCell's value
	# must be f(self, prev); self will be passed an instance of
	# this Model (just like you'd expect), and prev will be passed
	# the cell's previous (aka out-of-date) value.

	# For this Rule I'm going to be ignoring the previous value,
	# and just using this instance's ratio and width to get the
	# new length:
	return float(self.width) * float(self.ratio)

    # There's another way to make RuleCells. We can pass anonymous
    # functions to the cells.makecell function:
    area = cells.makecell(rule=lambda self, p:
			  float(self.length) * float(self.width))

# So now we've got our Model. Let's test it out:
if __name__ == "__main__":
    r = Rectangle()
    # Note that we use cells, no matter what type, by retrieving them
    # like attributes:
    print "By default, the rectangle's width is", r.width
    print "And its length is", r.length
    print "And its area is", r.area

    v = 2.5
    print "Now I'll change the width to", v
    # Also note that to set an InputCell's value, we simply set the
    # attribute:
    r.width = v
    print "The length is now", r.length
    print "And the area has changed to", r.area

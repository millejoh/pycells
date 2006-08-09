#!/usr/bin/env python

"""
PyCells Tutorials, part three: Cell Varieties

There's a number of different types of cells. In this tutorial I'll
talk about them.
"""

import cells

# In the basic tutorial, I showed the two most common cell types:
# Input cells and Rule cells. Now let's look at the more exotic Cells.

# First, the DictCell, which propogates changes to its dictionary. An
# ordinary InputCell won't, since dictionaries are mutable. An example:

# We'd like an address book. We'd like to set the entries as a
# dictionary of names and email addresses:
class AddressBook(cells.Model):
    entries = cells.makecell(value={})
    names = cells.makecell(rule=lambda s,p: s.entries.keys())

# and use it like this:
if __name__ == "__main__":
    a = AddressBook()
    print "Created an AddressBook. I'll add Truman and Bob's addresses to it."
    a.entries["Truman Capote"] = "capote@example.net"
    a.entries["Robert Sullivan"] = "ratguy@example.net"

    print "Your address book includes the following folks:", repr(a.names)
    print

# Yeah, that doesn't work at all. Why? Because the dictionary doesn't
# propogate the changes. A default Cell simply asks if the old value
# == the new value; when a dictionary has entries altered, it still ==
# its pre-change value. But if we specify a DictCell, we get the
# propgation we expect here:
class WorkingAddressBook(AddressBook):
    entries = cells.makecell(value={}, celltype=cells.DictCell)

if __name__ == "__main__":
    a = WorkingAddressBook()
    print "Created a WorkingAddressBook, now I'll add Truman and Bob to it."
    a.entries["Truman Capote"] = "capote@example.net"
    a.entries["Robert Sullivan"] = "ratguy@example.net"

    print "Your address book includes the following folks:", repr(a.names)
    print

# Sometimes a Model needs a cell whose value is determined by a
# function, but afterwards acts like an input cell. Let's say we want
# to pull the address book's entries from a pickle, if it exists, on
# cell init, but then allow the entries be modified as before.
import pickle, os.path

class StorableAddressBook(WorkingAddressBook):
    entry_file = cells.makecell(value="./addresses.pickle")

    # We'll build this autoloading entry db with a RuleThenInputCell:
    @cells.fun2cell(celltype=cells.RuleThenInputCell)
    def entries(self, prev):
	# These are written like RuleCells. First we'll look for an
	# extant entry file:
	if not os.path.isfile(self.entry_file):
	    # And if it doesn't exist, we'll just return an empty dictionary.
	    return {}
	else:
	    # If there is a file there, we'll load it into memory
	    # using the pickle module.
	    return pickle.load(open(self.entry_file, 'r'))
	
# What a RuleThenInputCell does is run the rule, which should generate
# a value for the cell, then transform into an InputCell which may be
# altered. In this case, it loads the previous address book dictionary
# or makes a new, empty one. Let's watch it work:
if __name__ == "__main__":
    a = StorableAddressBook()
    print "Created a StorableAddressBook. Adding new entries..."
    # Now we should have a new, empty address book, providing there's
    # no pickle file where StorableAddressBook's init looked.
    print "Address book is", repr(a.entries)
    print "Altering address book..."
    # Let's change the names ...
    a.entries = { "Truman Capote": "capote@example.net",
		  "Robert Sullivan": "ratguy@example.net" }
    # to see that it's now acting like an InputCell:
    print "Address book is", repr(a.entries)

    # Okay, let's test the unpickling. First, we'll pickle a couple of
    # entries:
    print "Writing some new entries out to the file"
    new_entries = { "David Sedaris": "dave@example.net",
		    "Michael Chabon": "chabon@example.net" }
    pickle.dump(new_entries, open(a.entry_file, 'w'))

    # now we'll make a new StorableAddressBook object, which, upon
    # init, will unpickle those entries
    b = StorableAddressBook()
    print "Created another StorableAddressBook."
    print "This new address book is", repr(b.entries)
    print

# Another variety of cell is an ephemeral cell. Ephemerals --
# InputCells with the ephemeral flag turned "on" -- propgate their
# changes and then return their value to None. For example, suppose we
# want to add entries to the address book by placing a tuple of name &
# email into an input cell:
import copy

class AlternateInputAddressBook(WorkingAddressBook):
    # I'll add an ephemeral input cell to take the tuple
    entry = cells.makecell(value=None, ephemeral=True)

    # and a RuleCell to build a dictionary with the entries
    @cells.fun2cell()
    def entries(self, prev):
	d = copy.copy(prev)	# prevent the old == new dict issue
	if not d:
	    d = {}

	if self.entry:
	    d[self.entry[0]] = self.entry[1]
	return d

@AlternateInputAddressBook.observer(attrib="entry")
def entry_obs(self):
    if self.entry:
	print "New entry:", repr(self.entry)

@AlternateInputAddressBook.observer(attrib="entries")
def entries_obs(self):
    if self.entries:
	print "The address book is now:", repr(self.entries)

if __name__ == "__main__":    
    print "Creating an AlternateInputAddressBook, then adding an entry."
    a = AlternateInputAddressBook()
    a.entry = ("Frank Miller", "frank.miller@example.net")
    print "The entry cell is now:", repr(a.entry)
    print

# The last class of cell I'll talk about in this tutorial is the lazy
# cell. There are several varieties of lazy cells, but I'll just talk
# about the vanilla lazy cell, an AlwaysLazyCell. Lazy cells are
# variants of RuleCells which only update when they are queried,
# instead of when one of their dependencies updates. An example should
# clear that up:

# Let's say I want a flag to show if a person is available. It's an
# expensive calculation, requiring a query out to the very slow
# security system to see which offices have had movement in them in
# the last 30 seconds. Because of this, I don't want to make the call
# every time I change the entries in my address book -- I only want to
# make it when I want that bit of info.
import random

class MonitoringAddressBook(WorkingAddressBook):
    # So we'll make a RuleCell-looking thing, but specify it should be
    # lazy:
    @cells.fun2cell(celltype=cells.AlwaysLazyCell)
    def isthere(self, prev):
	d = {}
	print "Querying security system"
	for person in self.names:
	    # here's where my expensive calculation goes...
	    d[person] = random.choice([True, False])

	return d

# And, again, let's see it in action
if __name__ == "__main__":
    print "Creating a monitoring address book..."
    c = MonitoringAddressBook()
    print "Address book is", repr(dict(c.entries))
    print "Adding a couple of entries..."
    c.entries["David Foster Wallace"] = "dfw@example.com"
    c.entries["Joyce Carol Oates"] = "jco@example.com"
    print "Address book is", repr(c.entries)

    # So now we'll see that the lazy cell's rule only runs when it's queried
    print "Let's see who's around..."
    result = c.isthere["David Foster Wallace"]
    # "Querying security system" will print here
    print "DFW is in?", result
    # But it's still a cell, and needless calculations won't happen:
    result = c.isthere["Joyce Carol Oates"]
    # Nothing prints here, as the lazy rule cell doesn't need to update
    print "JCO is in?", result

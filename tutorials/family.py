#!/usr/bin/env python

"""
PyCells Tutorials, part four: The Family

Some applications depend on large, or indeterminant, numbers of
similar objects coordinated by another, enclosing object. To ease the
creation of Models in this structure, there exists the Family
object. It's a Model subclass with a number of conveniences which I'll
describe in this tutorial.  """

import cells

# Instead of just one address book, I want to be able to have as many
# as I want. (This example is pretty contrived. Sorry.) An
# AddressBooks class, which inherits from Family, will coordinate
# access to the address books, which will be put in Adressbooks' kids
# list.

# First, let's get an idea of what each adress book needs to look like:
class NamedAddressBook(cells.Family):
    name = cells.makecell(value="Anonymous")
    entries = cells.makecell(value={}, celltype=cells.DictCell)
    names = cells.makecell(rule=lambda s,p: s.entries.keys())

@NamedAddressBook.observer(attrib="entries")
def entry_obs(model):
    if model.entries:
        print "Added a new name to the '" + model.name + "' address book"

# Now we'll specify that class in the AdressBooks class as the
# kid_slots attribute. The class in this slot acts as a mixin to any
# class passed to the make_kid method. Confusing? Yeah. Pretty useful
# in some situations, though, so watch it in action:
class AddressBooks(cells.Family):
    # Note that kid_slots is just a cell. It could be any type of cell
    # so long as the value it produced was a class.
    kid_slots = cells.makecell(value=NamedAddressBook)

    # I'd like to be able to get all of the names and emails from all
    # of the address books:
    @cells.fun2cell()
    def entries(self, prev):
        d = {}
        for model in self.kids:
            d.update(model.entries)

        return d

    # And also get all the names:
    names = cells.makecell(rule=lambda s,p: s.entries.keys())

    # Let's also get all the address book names & indexes
    @cells.fun2cell()
    def booknames(self, prev):
        d = {}
        for model in self.kids:
            # I'll use one of the Family convenience methods, position
            d[model.name] = model.position()

        return d

# And, so we can easily see what's happening I'll add some observers
# to the AddressBooks model:
@AddressBooks.observer(attrib="entries")
def entries_obs(model):
    print "AddressBooks' entries changed"

@AddressBooks.observer(attrib="names")
def names_obs(model):
    if model.names:
        print "All names, in all address books:", repr(model.names)

@AddressBooks.observer(attrib="booknames")
def booknames_obs(model):
    if model.booknames:
        print "Your address books are:", repr(model.booknames)

# That should do it. Let's see it in action:
if __name__ == "__main__":
    print "Creating a set of address books"
    a = AddressBooks()
    print "Adding an address book to the set"
    a.make_kid(NamedAddressBook)
    print "Naming that new address book 'Work'"
    a.kids[0].name = "Work"
    print "Now doing the same for 'Friends'"
    a.make_kid(NamedAddressBook)
    a.kids[1].name = "Friends"

    print
    print "Now I'll add some people to my address books..."
    a.kids[0].entries["Big Boss"] = "big.boss@example.net"
    a.kids[0].entries["Cow Orker"] = "cow.orker@example.net"
    a.kids[1].entries["Dr. Inkin G. Buddy"] = "inkin@example.net"

    print 
    # We can add any Model to the kids list, and PyCells will ensure
    # that the enclosing Family class will override the desired
    # methods, as defined in kid_slots. For instance:

    class SomeContainer(cells.Family):
        entries = cells.makecell(value=[], celltype=cells.ListCell)
        size = cells.makecell(rule=lambda s,p: len(s.entries))

    # SomeContainer has one cell which is named the same as a cell in
    # AddressBooks' kid_slots Model, NamedAddressBook:
    # entries. However, since it's incompatible with the rest of
    # NamedAddressBook's cells -- it's a list rather than a dictionary
    # -- AddressBooks will override SomeContainer.entries with the
    # cell definition from NamedAddressBook. However, SomeContainer
    # has another cell which doesn't appear in NamedAddressBook:
    # size. It will survive being pushed into the kids list, and
    # continue to work properly. Watch:

    a.make_kid(SomeContainer)
    a.kids[2].name = "Family"   # It was given the 'name' attribute,
    a.kids[2].entries["Dad"] = "dad@example.net" # and 'entries' was overridden,
    # but unique attribs are kept.
    print "Size of new address book:", a.kids[2].size 
    

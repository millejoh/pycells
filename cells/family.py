# PyCells: Automatic dataflow management for Python
# Copyright (C) 2006, Ryan Forsythe

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# See LICENSE for the full license text.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
Family, a specialized C{L{Model}} for networks of C{L{Model}}s.

@var DEBUG: Turns on debugging messages for the cellattr module.
"""

DEBUG = False

import cells
from model import Model, ModelMetatype
from cellattr import CellAttr
from cell import ListCell

def _debug(*msgs):
    """
    debug() -> None

    Prints debug messages.
    """
    msgs = list(msgs)
    msgs.insert(0, "family".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

class Family(Model):
    """
    Family
    
    A specialized C{L{Model}} which has C{kids}, C{kid_slots}, and a
    number of convenience functions for traversing the parent/child
    graph.

    @ivar kids: A list of Models which are guaranteed to have the
        attribute overrides defined in C{L{kid_slots}}

    @ivar kid_slots: An override definition for the Cells inserted
        into the C{L{kids}} list. The attributes overridden are every
        attribute defined in the class in C{kid_slots} minus the
        attributes defined in every Model.
    """
    kids = cells.makecell(celltype=ListCell, kid_overrides=False)
    kid_slots = cells.makecell(value=Model, kid_overrides=False)

    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)

    def kid_instance(self, klass=None):
        """
        kid_instance(self, klass) -> Cell
        
        Creates a new instance of a Cell based on the passed class (in
        C{klass}) and the overrides defined in C{kid_slots}.

        @param klass: The base type for the new kid instance
        """
	if not klass:
	    klass = self.kid_slots
        _debug("making an instance of", str(klass))
        # first, find the attributes the kid_slots attrib actual wants to
        # define:
        override_attrnames = []
        for attrname in dir(self.kid_slots):
            cvar = getattr(self.kid_slots, attrname)
            # if it's a cell attribute, check to see if it's one of
            # the "special", non-overriding slots (eg kids)
            if isinstance(cvar, CellAttr):
                if cvar.kid_overrides:
                    # and if it isn't, add it to the list of overrides
                    override_attrnames.append(attrname)
            # if it's a normal attribute, override only if it doesn't
            # exist in the base class
            else:                
                if attrname not in dir(cells.Family):
                    override_attrnames.append(attrname)
                    
        # now, do the overrides, bypassing normal getattrs
        for attrib_name in override_attrnames:
            _debug("overriding", attrib_name, "in", str(klass))
            setattr(klass, attrib_name, self.kid_slots.__dict__[attrib_name])

        # add any observers the kid_slots class defines:
        klass._observernames.update(self.kid_slots._observernames)

        # XXX: should we memoize all that work here?
        
        # finally, return an instance of that munged class with this obj set
        # as its parent:
        i = klass(parent=self)
        return i
    
    def make_kid(self, klass):
        """
        make_kid(self, klass) -> None

        Adds a new instance of a Cell based on the passed class (in
        C{klass}) and the overrides defined in C{kid_slots} into the
        C{kids} list

        @param klass: the base type for the new kid instance
        """
	_debug("make_kid called with", str(klass))
        self.add_kid(self.kid_instance(klass))

    def add_kid(self, kid):
        """
        add_kid(self, kid) -> None

        Inserts the kid into this Family's C{kids} list

        @param kid: the Model instance to insert
        """
        kid.parent = self
        self.kids.append(kid)

    def position(self):
        """
        position(self) -> int

        Returns this instance's position in the enclosing Family's
        C{kids} list. Returns -1 if there is no enclosing Family.

        @raise FamilyTraversalError: Raises if there is no enclosing Family
        """
        if self.parent:
            return self.parent.kids.index(self)
        raise FamilyTraversalError("No enclosing Family")
        
    def previous_sib(self):
        """
        previous_sib(self) -> Model

        Returns the Model previous to this Model in the enclosing
        Family's C{kids} list

        @raise FamilyTraversalError: Raises if there is no enclosing Family
        """
        if self.parent and self.position() > 0:
            return self.parent.kids[self.position() - 1]
        raise FamilyTraversalError("No enclosing Family")
    
    def next_sib(self):
        """
        previous_sib(self) -> Model

        Returns the Model subsequent to this Model in the enclosing
        Family's C{kids} list

        @raise FamilyTraversalError: Raises if there is no enclosing Family
        """
        if self.parent and self.position() < len(self.parent.kids) - 1:
            return self.parent.kids[self.position() + 1]
        raise FamilyTraversalError("No enclosing Family")
        
    def grandparent(self):
        """
        grandparent(self) -> Model

        Returns enclosing Family instance's enclosing Family instance,
        or None if no such object exists.
        """
        # raise or just return None?
        if self.parent:
            if self.parent.parent:
                return self.parent.parent
        return None

class FamilyTraversalError(Exception):
    """
    Raised when there's some sort of error in C{L{Family}}'s traversal
    methods.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

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
CellAttr, a wrapper for C{L{Cell}} objects within C{L{Models}}

@var DEBUG: Turns on debugging messages for the cellattr module.
"""

import cells
from cell import Cell, RuleCell, InputCell

DEBUG = False

def debug(*msgs):
    """
    debug() -> None

    Prints debug messages.
    """
    msgs = list(msgs)
    msgs.insert(0, "cell attr".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)


class CellAttr(object):
    """
    CellAttr

    A descriptor which auto-vivifies a new Cell in each instance of a
    Model, and which does the hiding of C{Cell.L{get}()} and
    C{Cell.L{set}()}.
    """
    # kid_overrides is essentially internal, so it's hidden from the
    # documentation
    def __init__(self, kid_overrides=True, *args, **kwargs):
        """
        __init__(self, rule=None, value=None, unchanged_if=None, celltype=None)

        Sets the parameters which will be used as defaults to build a
        Cell when the time comes. 

        @param rule: Define a rule which backs this cell. You must
            only define one of C{rule} or C{value}. Lacking C{celltype},
            this creates a L{RuleCell}.  This must be passed a
            callable with the signature C{f(self, prev) -> value},
            where C{self} is the model instance the cell is in and
            C{prev} is the cell's out-of-date value.

        @param value: Define a value for this cell. You must only
            define one of C{rule} or C{value}. Lacking C{celltype}, this
            creates an L{InputCell}.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. The signature for the passed function
            is C{f(old, new) -> bool}.
            
        @param celltype: Set the cell type to generate. You must pass
            C{rule} or C{value} correctly. Refer to L{cells.cell} for
            available types.
        """
        self.kid_overrides = kid_overrides
        self.args = args
        self.kwargs = kwargs

	if kwargs.has_key("rule"):
	    self.__doc__ = kwargs['rule'].__doc__

    def __set__(self, owner, value):
        """
        __set__(self, owner, value) -> None

        Runs C{L{set}(value)} on the Cell in C{owner}.

        @param owner: The Model instance in which to look for the Cell
            to run C{L{set}()} on.

        @param value: The value to set
        """
        self.getcell(owner).set(value)
        
    def __get__(self, owner, ownertype):
        """
        __get__(self, owner, ownertype) -> value

        Runs C{L{get}()} on the Cell in C{owner}, if C{owner} is
        passed. Otherwise, return C{self}.

        @param owner: The Model instance in which to look for the Cell
            to run C{L{get}()} on .

        @param ownertype: (unused)
        """
        if not owner: return self

        cell = self.getcell(owner)
        if isinstance(cell, (cells.cell.ListCell, cells.cell.DictCell)):
            return cell
        else:
            # return the value in owner.myname
            return cell.getvalue()

    def getkwargs(self, owner):
	"""
	getkwargs(owner) -> dict

	Returns the keyword arguments for the target cell, taking into
	account any overrides which exist in the passed owner model
	"""
	newkwargs = self.kwargs.copy()
	override = owner._initregistry.get(self.name)
	if override:
	    newkwargs.update(override)

	return newkwargs
	
        
    def getcell(self, owner):
        """
        getcell(owner) -> Cell

        Return the instance of this CellAttr's Cell in C{owner}. If an
        instance of the CellAttr's Cell doesn't exist in C{owner},
        first insert an instance into C{owner}, then return it. To
        build it, first examine the C{owner} for runtime overrides of
        this cell, and use those (if they exist) as parameters to
        C{L{buildcell}}.

        @param owner: The Model instance in which to look for the Cell.
        """
        # if there isn't a value in owner.myname, make it a cell
        debug("got request for cell in", self.name)
        if self.name not in owner.__dict__.keys():
	    debug(self.name, "not in owner. Building a new cell in it.")
	    newcell = self.buildcell(owner, *self.args, **self.getkwargs(owner))
            owner.__dict__[self.name] = newcell

            # observers have to be run *after* the cell is embedded in the
            # instance!
            owner._run_observers(newcell)

        debug("finished getting", self.name)
        return owner.__dict__[self.name]

    def buildcell(self, owner, *args, **kwargs):
        """
        buildcell(self, owner, rule=None, value=None, celltype=None,
        unchanged_if=None) -> Cell

        Builds an instance of a Cell into C{owner}. Will automatically
        create the right type of Cell given the keyword arguments if
        C{celltype} is not passed

        @param owner: The Model instance in which to build the Cell.
        
        @param rule: Define a rule which backs this cell. You must
            only define one of C{rule} or C{value}. Lacking C{celltype},
            this creates a L{RuleCell}.  This must be passed a
            callable with the signature C{f(self, prev) -> value},
            where C{self} is the model instance the cell is in and
            C{prev} is the cell's out-of-date value.

        @param value: Define a value for this cell. You must only
            define one of C{rule} or C{value}. Lacking C{celltype}, this
            creates an L{InputCell}.

        @param unchanged_if: Sets a function to determine if a cell's
            value has changed. The signature for the passed function
            is C{f(old, new) -> bool}.
            
        @param celltype: Set the cell type to generate. You must pass
            C{rule} or C{value} correctly. Refer to L{cells.cell} for
            available types.
        """
        
        """Creates a new cell of the appropriate type"""
        debug("Building cell: owner:", str(owner))
        debug("                name:", self.name)
        debug("                args:", str(args))
        debug("              kwargs:", str(kwargs))
        # figure out what type the user wants:
        if kwargs.has_key('celltype'):    # user-specified cell
            celltype = kwargs["celltype"]
        elif kwargs.has_key('rule'):      # it's a rule-cell.
            celltype = RuleCell
        elif kwargs.has_key('value'):     # it's a value-cell
            celltype = InputCell
        else:
            raise Exception("Could not determine target type for cell " +
                            "given owner: " + str(owner) +
                            ", name: " + self.name +
                            ", args:" + str(args) +
                            ", kwargs:" + str(kwargs))

        kwargs['name'] = self.name

        return celltype(owner, *args, **kwargs)



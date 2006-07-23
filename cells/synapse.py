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
Synapses, cell variants which exist only within C{L{RuleCell}}s and
which mediate the propogation of another cell's value. For instance, a
cell C{a} could use cell C{b}'s value, but only if it had changed more
than 5% since the last time C{a} used it.

@var DEBUG: Turns on debugging messages for the synapse module.
"""

import cells, cell

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "synapse".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

class Synapse(cell.Cell):
    """
    A very specialized Cell variant. Synapses are filters for
    Cells. They can be applied to any type of Cell, and they simply
    process the cell to build a value which is provided to dependent
    cells as the filtered cell's value. They live within the cell
    which defines them, and as such are only referenceable in that
    rule.
    """
    initialized = False
    
    def __new__(cls, owner, name=None, **kwargs):
        """
        Create a new synapse instance within the calling Cell, if
        neccessary.

        @param cls: Class this synapse is being called from.
        
        @param owner: Model instance this synapse is being created in
            / retrieved from

        @param name: Name of the synapse to retrieve; used as a lookup
            on the enclosing Cell's synapse space.

        @param kwargs: standard C{L{Cell}} keyword arguments.
        """
        # first, check to see if there's already a synapse with this name in
        # the owner Cell
        if not owner.synapse_space.has_key(name): # and if there isn't
            # make one in the owner
            debug("building new synapse '" + name + "' in", str(owner))
            owner.synapse_space[name] = cell.Cell.__new__(cls, owner,
                                                           name=name, **kwargs)

        # finally, return the owner's synapse
        return owner.synapse_space[name]

    def __init__(self, owner, name=None, **kwargs):
        """
        Initialize the synapse Cell, if neccessary.

        @param owner: The model instance to pass to this synapse's rule

        @param name: This synapse's name

        @param kwargs: Standard C{L{Cell}} keyword arguments
        """
        # at this point we're guaranteed to have a Synapse in the
        # owner, and self points at that Synapse. We don't know if
        # it's been initialized, though. so:
        if not self.initialized:
            debug("(re)initializing", name)
            cell.Cell.__init__(self, owner, name=name, **kwargs)
            self.initialized = True
        
    def __call__(self):
        """
        Run C{L{Cell.get}(self)} when a synapse is called as a function.
        """
        return self.get()

    def run(self):
        """
        Slightly modified version of C{L{Cell.run}()}.
        """
        debug(self.name, "running")
        # call stack manipulation
        oldcurr = cells.cellenv.curr
        cells.cellenv.curr = self

        # the rule run may rewrite the dep graph; prepare for that by nuking
        # c-b links to this cell and calls links from this cell:
        for cell in self.calls_list():
            debug(self.name, "removing c-b link from", cell.name)
            cell.remove_cb(self)
        self.reset_calls()

        self.dp = cells.cellenv.dp                     # we're up-to-date
        newvalue = self.rule(self.owner, self.value)   # run the rule
        self.bound = True
        
        # restore old running cell
        cells.cellenv.curr = oldcurr

        # return changed status
        if self.unchanged_if(self.value, newvalue):
            debug(self.name, "unchanged.")
            return False
        else:
            debug(self.name, "changed.")
            self.last_value = self.value
            self.value = newvalue
            
            return True

    def rule(self, owner, oldvalue):
        return None

class ChangeSynapse(Synapse):
    """A very simple filter. Only returns the new value when it's
    changed by the passed delta
    """
    def __init__(self, owner, name=None, read=None, delta=None, **kwargs):
        debug("init'ing ChangeSynapse")
        if not self.initialized:
            self.readvar, self.delta = read, delta            
        Synapse.__init__(self, owner, name=name, **kwargs)
        self.rule = self.synapse_rule

    def synapse_rule(self, owner, oldvalue):
        debug("running ChangeSynapse rule")
        newval = self.readvar.get()
        if not oldvalue or abs(newval - oldvalue) > self.delta:
            debug("returning new value", str(newval))
            return newval
        else:
            debug("returning old value", str(oldvalue))
            return oldvalue

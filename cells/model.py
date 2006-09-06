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
Support for the C{L{Model}} object, an object in which C{L{CellAttr}}s
may be embedded.

@var DEBUG: Turns on debugging messages for the model module.
"""

import cells
from cell import Cell, EphemeralCellUnboundError
from cellattr import CellAttr
from observer import Observer, ObserverAttr

DEBUG = False

def debug(*msgs):
    """
    debug() -> None

    Prints debug messages.
    """
    msgs = list(msgs)
    msgs.insert(0, "model".rjust(cells._DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(( str(msg) for msg in msgs))

class ModelMetatype(type):
    def __init__(klass, name, bases, dikt):
        # copy over inherited registries of observers and non-cell attributes
        klass._observernames = set([])
        klass._noncells = set([])
        
        for cls in bases:
            obsnames = getattr(cls, "_observernames", None)
            noncellnames = getattr(cls, "_noncells", None)
            if obsnames:
                klass._observernames.update(obsnames)
            if noncellnames:
                klass._noncells.update(noncellnames)

        # do some work on various attributes of this class:
        for k,v in dikt.iteritems():
            debug("metaclass inspecting", k)
            if isinstance(v, CellAttr):
                debug("metaclass adding name field to", k)
                v.name = k

            elif isinstance(v, ObserverAttr):
                debug("registering observer", k)
                klass._observernames.add(k)

            else:                       # non-cell, non-observer attrib
                debug("registering noncell", k)
                klass._noncells.add(k)
                
                      
class Model(object):
    """
    A class in which CellAttrs may be used. Models automatically bring
    their cells up-to-date at C{L{__init__}}-time. Cells may be
    altered at runtime by passing C{attrname=value}, or
    C{attrname=hash} to the constructor.

    @ivar model_name: A cell holding The name of this Model. By
        default, None.

    @ivar model_value: A cell holding the value of this Model. By
        default, None.

    @ivar parent: A cell for C{L{Family}} graph traversal. By default,
        None.
    """
    __metaclass__ = ModelMetatype

    _initialized = False

    model_name = cells.makecell(value=None, kid_overrides=False)
    model_value = cells.makecell(value=None, kid_overrides=False)
    parent = cells.makecell(value=None, kid_overrides=False)

    def __init__(self, *args, **kwargs):
        """
        __init__(self, [<attrname>=<value, rule or dict>], ...) -> None

        Initialize a Model with optional overrides. By passing a
        parameter with the same name as a cell attribute, you may
        override that cell attribute. For example:

            >>> class A(cells.Model):
            ...     x = cells.makecell(value=1)
            ... 
            >>> a1 = A()
            >>> a1.x
            1
            >>> a2 = A(x="blah")
            >>> a2.x
            'blah'

        This override can be arbitrarily complex; for instance, you
        can make a RuleCell into a ValueCell, change a attribute's
        celltype ... In short, anything you can do at Model defintion
        time you can alter at instantiation time:

            >>> class B(cells.Model):
            ...     x = cells.makecell(rule=lambda s,p: 3 * s.y)
            ...     y = cells.makecell(value=2)
            ... 
            >>> b = B()
            >>> b.x
            6
            >>> b.y = 1
            >>> b.x
            3
            >>> b = B(y=10)
            >>> b.x
            30
            >>> b.y
            10
            >>> b = B(x={'celltype': cells.RuleThenInputCell})
            >>> b.x
            6
            >>> b.y
            2
            >>> b.x = 5
            >>> b.x
            5
            >>> b.y = 1
            >>> b.x
            5

        @param attrname: The name of the attribute you wish to
            override. If this is set to a callable, it will override
            the rule for the cell. If it's set to a dictionary with
            one or more of 'rule', 'value', or 'celltype', those
            attributes will be overridden in the cell. Otherwise, it
            will override the value of the target cell.
        """
        self._initregistry = {}
        klass = self.__class__

        # do automagic overriding:
        for k,v in kwargs.iteritems():       # for each keyword arg
            if k in dir(klass):       # if there's a match in my class
                # normalize the input
                if callable(v):
                    cellinit = {'rule': v}
                elif 'keys' in dir(v):
                    # kinda ran out of synonyms/shortened versions of
                    # keys, here. I just want to see if any of 'rule',
                    # 'value', or 'celltype' are in the keys of the
                    # dict in v:
                    quays = v.keys()
                    for qui in ('rule', 'value', 'celltype'):
                        if qui in quays:
                            cellinit = v
                            break
                else:
                    cellinit = {'value': v}

		if not cellinit:
		    raise BadInitError("A cell initialization dictionary was not built. Try wrapping your value or rule assignment in a dictionary.")
                    
                # set the new init in the registry for this cell name; to be
                # read at cell-build time
                self._initregistry[k] = cellinit

        # turn the observer name registry into a list of real Observers
        self._observers = []
        for name in self._observernames:
            self._observers.append(getattr(self, name))
	self._prioritize_observers()

        # do initial equalizations
        debug("INITIAL EQUALIZATIONS START")
        for name in dir(self):
            try:
		# look for always-lazy cells, and skip 'em
		if not isinstance(self.__dict__[name], cells.AlwaysLazyCell):
		    getattr(self, name) # will run observers by itself
            except EphemeralCellUnboundError, e:
                debug(name, "was an unbound ephemeral")
        debug("INITIAL EQUALIZATIONS END")

        # run observers on non-cell attributes
        for key in self._noncells:
            self._run_observers(getattr(self, key))

        # and now we're initialized. lock the object down.
        self._initialized = True

    def __setattr__(self, key, value):
	"""
	Per KT's spec, Models may not set non-cell attributes after
	__init__.

	@raise NonCellSetError: If you try to set a non-cell attribute
	"""
         # always set Cells
        if isinstance(self.__dict__.get(key), Cell):
                object.__setattr__(self, key, value)
        # we can set noncells before init
        elif not self._initialized:     
            if key not in self._noncells: # make sure it's registered, though
                self._noncells.add(key)
            object.__setattr__(self, key, value) # and then set it
        # we can set anything we've not seen, too
        elif key not in self.__dict__.keys():
            object.__setattr__(self, key, value)
        # but the only thing left is non-cells we've seen, which is verboten
        else:
            raise NonCellSetError, "Setting non-cell attributes of models " + \
                  "after init is disallowed"
        
    def _run_observers(self, attribute):
        """Runs each observer in turn. There's some optimization that
        could go on here, if it turns out to be neccessary.
        """
        debug("model running observers -- ", str(len(self._observers)),
              "to test")
        for observer in self._observers:
            observer.run_if_applicable(self, attribute)

    def _buildcell(self, name, *args, **kwargs):
        """
        
        """
        debug("Building cell: owner:", str(self))
        debug("                name:", name)
        debug("                args:", str(args))
        debug("              kwargs:", str(kwargs))
        # figure out what type the user wants:
        if kwargs.has_key('celltype'):
            celltype = kwargs["celltype"]
        elif kwargs.has_key('rule'):  # it's a rule-cell.
            celltype = cells.RuleCell
        elif kwargs.has_key('value'):     # it's a value-cell
            celltype = cells.InputCell
        else:
            raise Exception("Could not determine target type for cell " +
                            "given owner: " + str(self) +
                            ", name: " + name +
                            ", args:" + str(args) +
                            ", kwargs:" + str(kwargs))
        
        kwargs['name'] = name
        return celltype(self, *args, **kwargs)

    def _prioritize_observers(self):
	"""
	_prioritize_observers(self) -> none

	(re)Sorts the observer list by priorities
	"""
	self._observers.sort(cmp=lambda x, y: cmp(x.priority, y.priority),
			     reverse=True)

    @classmethod
    def observer(klass, attrib=None, oldvalue=None, newvalue=None,
		 priority=None):
        """
        observer(attrib=None, oldvalue=None, newvalue=None, priority=Non) -> decorator

        A classmethod to add an observer attribute to a Model. The
        observer may be set to fire on any change in the model, any
        change in an attribute, or when a function testing the new or
        old value of a cell returns true.

	    >>> import cells
	    >>> class A(cells.Model):
	    ...     x = cells.makecell(value=4)
	    ... 
	    >>> @A.observer(attrib="x", newvalue=lambda a: a % 2)
	    ... def odd_x_obs(model):
	    ...     print "New value of x is odd!"
	    ... 
	    >>> a = A()
	    >>> a.x
	    4
	    >>> a.x = 5
	    New value of x is odd!
	    >>> a.x = 42
	    >>> a.x = 11
	    New value of x is odd!

        @param attrib: An attribute name to attach the observer to

        @param oldvalue: A function to run on the now-out-of-date
            value of a cell which changed in this datapulse; if the
            function returns True, the observer will fire. The
            signature for the function must be C{f(val) -> bool}

        @param newvalue: A function to run on up-to-date value; if the
            function returns True, the observer will fire. The
            signature for the function must be C{f(val) -> bool}

        @param priority: When this observer should be run compared to
            the other observers on this model. Observers have a
            priority of None by default. Observers with larger
            priorities are run first, None last. Observers with the
            same priority are run in arbitrary order.

        """
        def observer_decorator(func):
            klass._observernames.add(func.__name__)
            setattr(klass, func.__name__, ObserverAttr(func.__name__, attrib,
                                                       oldvalue, newvalue,
                                                       func))
        return observer_decorator


class NonCellSetError(Exception):
    """
    You may not set a non-cell Model attribute after initialization.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BadInitError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

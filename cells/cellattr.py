from cell import Cell, RuleCell, ValueCell, EphemeralCell

DEBUG = False

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "   cell attr > ")
    if DEBUG:
        print " ".join(msgs)


class CellAttr(object):
    """A descriptor for a Cell attribute in a ModelObject"""
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.observers = []

    def buildcell(self, owner, name, observers, *args, **kwargs):
        """Creates a new cell of the appropriate type"""
        debug("Building cell: owner:", str(owner))
        debug("                name:", name)
        debug("           observers:", str(observers))
        debug("                args:", str(args))
        debug("              kwargs:", str(kwargs))
        # figure out what type the user wants:
        if kwargs.has_key('type'):
            celltype = kwargs["type"]
        elif kwargs.has_key('function'):  # it's a rule-cell.
            celltype = RuleCell
        elif kwargs.has_key('value'):     # it's a value-cell
            celltype = ValueCell
        else:
            pass                          # can't figure it out? fail noisily.

        return celltype(owner, self.name, observers=observers, *args, **kwargs)
        
    def getcell(self, owner):
        # if there isn't a value in owner.myname, make it a cell
        debug("got request for cell in", self.name)
        if self.name not in owner.__dict__.keys():
            # first, find out if this object has overrides on this cell's init
            override = owner._initregistry.get(self.name)            
            if override:                # it does, use the override
                newcell = self.buildcell(owner, self.name, self.observers,
                                         **override)
            else:                       # it doesn't, use class's default
                newcell = self.buildcell(owner, self.name, self.observers,
                                         *self.args, **self.kwargs)
                
            owner.__dict__[self.name] = newcell

        debug("finished getting", self.name)
        return owner.__dict__[self.name]
        
    def __get__(self, owner, ownertype):
        if not owner: return self
        # return the value in owner.myname
        return self.getcell(owner).get()

    def __set__(self, owner, value):
        debug("Setting", self.name, "=", str(value))
        cell = self.getcell(owner)  # get the cell in owner.myname        
        cell.set(value)      # and push a value into it
        debug("Finished setting", self.name, "=", str(value))

        # if there's nothing currently running, then a perturbation has finished
        # propogating. since a setattr is a recursive call, we can just pull the
        # first item off the set queue, if there is one, and run it.
        if owner._curr:
            debug(owner._curr.name, "currently running")
        if not owner._curr:
            debug("nothing running")
            if owner._setqueue:                
                name, value = owner._setqueue.pop(0)
                debug("set queue has an item: ", name, "=", str(value))
                setattr(owner, name, value)

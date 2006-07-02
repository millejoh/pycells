from cell import Cell, RuleCell, InputCell

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

    def buildcell(self, owner, name, *args, **kwargs):
        """Creates a new cell of the appropriate type"""
        debug("Building cell: owner:", str(owner))
        debug("                name:", name)
        debug("                args:", str(args))
        debug("              kwargs:", str(kwargs))
        # figure out what type the user wants:
        if kwargs.has_key('type'):
            celltype = kwargs["type"]
        elif kwargs.has_key('rule'):  # it's a rule-cell.
            celltype = RuleCell
        elif kwargs.has_key('value'):     # it's a value-cell
            celltype = InputCell
        else:
            raise Exception("Could not determine target type for cell " +
                            "given owner: " + str(owner) +
                            ", name: " + name +
                            ", args:" + str(args) +
                            ", kwargs:" + str(kwargs))

        return celltype(owner, self.name, *args, **kwargs)
        
    def getcell(self, owner):
        # if there isn't a value in owner.myname, make it a cell
        debug("got request for cell in", self.name)
        if self.name not in owner.__dict__.keys():
            # first, find out if this object has overrides on this cell's init
            override = owner._initregistry.get(self.name)            
            if override:                # it does, use the override
                newcell = self.buildcell(owner, self.name, **override)
            else:                       # it doesn't, use class's default
                newcell = self.buildcell(owner, self.name, *self.args,
                                         **self.kwargs)
                
            owner.__dict__[self.name] = newcell

        debug("finished getting", self.name)
        return owner.__dict__[self.name]
        
    def __get__(self, owner, ownertype):
        if not owner: return self
        # return the value in owner.myname
        return self.getcell(owner).get()

    def __set__(self, owner, value):
        self.getcell(owner).set(value)

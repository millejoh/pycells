"""
Cell

Cell, and subclasses of Cell.
TODO: More here.
"""

DEBUG = False

import cells
from model import Model, ModelMetatype

def debug(*msgs):
    msgs = list(msgs)
    msgs.insert(0, "family".rjust(cells.DECO_OFFSET) + " > ")
    if DEBUG or cells.DEBUG:
        print " ".join(msgs)

class FamilyMeta(ModelMetatype):
    def __init__(klass, name, bases, dikt):        
        ModelMetatype.__init__(klass, name, bases, dikt)
        klass._kid_slots = cells.makecell(value=klass)
        klass._kid_slots.name = "_kid_slots"

class Family(Model):
    __metaclass__ = FamilyMeta
    
    _kids = cells.makecell(type=cells.RuleThenInputCell,
                           rule=lambda s,p: [])

    def __getattr__(self, key):
        # shortstop the default cells
        if key in ("model_name", "model_value", "parent", "kids", "kid_slots"):
            # and if they don't exist in this object
            if key not in dir(self):
                # copy the default over
                debug("copying default", key, "into this Model")
                object.__setattr__(self, key,
                                   object.__getattribute__(self, "_" + key))

        return object.__getattribute__(self, key)

    def kid_instance(self, klass):
        debug("making an instance of", str(klass))
        # first, find the attributes the kid_slots attrib actual wants to
        # define:
        ks_attrs = set(dir(self.kid_slots)) # has a lot of default Family attrs
        md_attrs = set(dir(cells.Family))   # is only default Family attrs
        ks_attrs = ks_attrs.difference(md_attrs)

        # now, do the overrides, bypassing normal getattrs
        for attrib_name in ks_attrs:
            debug("overriding", attrib_name, "in", str(klass))
            setattr(klass, attrib_name, self.kid_slots.__dict__[attrib_name])

        # add any observers the kid_slots class defines:
        klass._observernames.update(self.kid_slots._observernames)

        # XXX: should we memoize all that work here?
        
        # finally, return an instance of that munged class with this obj set
        # as its parent:
        i = klass()
        i.parent = self
        return i
    
    def make_kid(self, klass):
        self.kids.append(self.kid_instance(klass))

    def add_kid(self, kid):
        kid.parent = self
        self.kids.append(kid)

    def position(self):
        if self.parent: return self.parent.kids.index(self)
        return None
        
    def previous_sib(self):
        if self.parent and self.position() > 0:
            return self.parent.kids[self.position() - 1]
        return None
    
    def next_sib(self):
        if self.parent and self.position() < len(self.parent.kids) - 1:
            return self.parent.kids[self.position() + 1]
        return None
        
    def grandparent(self):
        if self.parent:
            if self.parent.parent:
                return self.parent.parent
        return None

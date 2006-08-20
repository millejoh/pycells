import cells
import Tkinter

class BasicTkinterObject(cells.Family):
    container = cells.makecell(value=None)
    widget = cells.makecell(value=None)

class Container(BasicTkinterObject):
    pass
    
class Row(Container):
    @cells.fun2cell()
    def container(self, prev):
	print "Row.container"
	if not self.parent:
	    return None
	widget = self.parent.widget
	if isinstance(widget, Tkinter.Frame):
	    return widget
	return self.parent.container

class Label(BasicTkinterObject):
    def __init__(self, *args, **kwargs):
	BasicTkinterObject.__init__(self, *args, **kwargs)
	self.stringvar = Tkinter.StringVar(self.container)
	self.widget = Tkinter.Label(self.container, textvariable=self.stringvar)
	self.widget.pack()
	
    stringvar = cells.makecell(value=None)
    update_on = cells.makecell(value="none")
    
    @cells.fun2cell()
    def container(self, prev):
	print "Entry.container"
	return self.parent.widget


class Entry(BasicTkinterObject):
    def __init__(self, *args, **kwargs):
	BasicTkinterObject.__init__(self, *args, **kwargs)
	self.stringvar = Tkinter.StringVar(self.container)
	self.stringvar.trace("u", self.text_copier)
	self.widget = Tkinter.Entry(self.container, textvariable=self.stringvar)
	self.widget.pack()
	
    text = cells.makecell(value=None)
    stringvar = cells.makecell(value=None)
    update_on = cells.makecell(value="none")

    def text_copier(self, *args):
	print "updating text", repr(args), "field is", self.stringvar.get()
	self.text = self.stringvar.get()
    
    @cells.fun2cell()
    def container(self, prev):
	print "Entry.container"
	return self.parent.widget

@Entry.observer(attrib="stringvar")
def sv_tracer(model):
    if model.stringvar and model.update_on == "write":
	model.stringvar.trace("w", model.text_copier)    

class Window(Container):
    @cells.fun2cell(celltype=cells.RuleThenInputCell)
    def widget(self, prev):
	print "Window.widget"
	f = Tkinter.Frame(self.container)
	return f

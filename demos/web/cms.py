#!/usr/bin/env python

import cells, BaseHTTPServer, ConfigParser, glob, os, re

CellCMSConfig = ConfigParser.ConfigParser()
CellCMSConfig.read('cms.cfg')

# the general idea for this thing is that there be a thin shell of
# "normal" python to set up & feed the models which will do the heavy
# lifting & responses.

# let's build the models.
class Page(cells.Model):
    """A model to hold a single page, from request to page generation."""
    # Non-Cells
    cleanpath = re.compile(r"(/([A-Za-z0-9]+\.)*([A-Za-z0-9]*))*(\?.*)?")
    
    # INPUT CELLS
    request = cells.makecell(value=None)
    config = cells.makecell(value=None)

    # RULE CELLS
    @cells.fun2cell()
    def cleaned_path(self, prev):
        if not self.cleanpath.match(self.request.path):
            print "Illegal path request:", self.request.path
            return "/"
        return self.request.path
    
    @cells.fun2cell()
    def output(self, prev):
        """Outputs the final, rendered version of this Page"""
        if not self.request: return

        if glob.glob(self.config.get('directories', 'static') +
                     self.cleaned_path):
            # TODO: actual content-type exam here
            return open(self.config.get('directories', 'static') +
                        self.cleaned_path).read()
        # TODO: Look for generated content
        else:
            return "No such file"

@Page.observer(attrib="request")
def pagelog_observer(self):
    """Each time a Page is created or modified, log."""
    if self.request:
        print self.request.client_address[0] + ":", str(self.request.path), \
              "-- created Page"

class RequestHandler(cells.Model):
    """A model which turns GET requests into formatted content
    
    The idea for this thing is that we build a model for every
    request, then store them in the pages slot. 
    """
    def __init__(self):
        cells.Model.__init__(self)
        self.pages = {}

    # NONCELLS
    special = ('/stats',)
        
    # INPUT CELLS
    config = cells.makecell(value=None)  # handle to the ConfigParser object    
    request = cells.makecell(value=None) # the input for the model
    pages = cells.makecell(value=None)   # Page model storage

    # RULE CELLS
    @cells.fun2cell()
    def request_key(self, prev):
        """Takes a BaseHTTPRequestHandler and makes a page key out of it"""
        if self.request:
            req = self.request
            return (req.client_address[0], req.command, req.path)
        return None

    @cells.fun2cell()
    def output(self, prev):
        """Outputs the requested page, rendered and ready for the browser."""
        if not self.request_key: return
        
        if self.request.path == '/stats':
            buff = ["Cell CMS Statistics",
                    "Number of stored Pages: " + str(len(self.pages.keys())),
                    str([str(key) for key in self.pages.keys()])]
            return "\n".join(buff)
            
        return self.pages[self.request_key].output

@RequestHandler.observer(attrib="request")
def handlerlog_observer(self):
    """Each time a request is recieved, log"""
    if self.request:
        print self.request.client_address[0] + ":", str(self.request.path), \
              "-- got request"
        
    
@RequestHandler.observer(attrib="request_key")
def request_key_obs(self):
    """Builds the Request-to-Page dictionary"""
    # TODO: pages_registry management -- it grows forever, now.
    if not self.request_key: return
    if self.request.path in self.special: return
    
    page = self.pages.get(self.request_key, None)
    if not page:                    # build a Page if one doesn't exist for
        page = Page(config=self.config, request=self.request) # this request
        self.pages[self.request_key] = page

    
handler = RequestHandler() # make a new cellular handler
handler.config = CellCMSConfig # and give it its configuration
    
# now let's build the shell. I'm going to use the BaseHTTPServer to
# process the raw requests, and a subclass of the base request handler
# will pass things into the model
class Request(object):
    """Just a container for the RequestHandler's current request data"""
    def __init__(self, request):
        self.client_address = request.client_address
        self.command = request.command
        self.path = request.path
        self.request_version = request.request_version
        self.headers = request.headers
        self.rfile = request.rfile
        self.wfile = request.wfile
                                                  
class CellRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        handler.request = Request(self) # build a new request object
        print >>self.wfile, handler.output

# Finally, set it moving:
print "Starting server at", CellCMSConfig.get('server', 'address'), "on port", \
      CellCMSConfig.get('server', 'port')
server_address=(CellCMSConfig.get('server', 'address'),
                CellCMSConfig.getint('server', 'port'))
httpd = BaseHTTPServer.HTTPServer(server_address, CellRequestHandler)
print "... server started."
httpd.serve_forever()


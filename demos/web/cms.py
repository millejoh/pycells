#!/usr/bin/env python

import cells, BaseHTTPServer, ConfigParser, glob, os, re, time, datetime

# BIG props to Yuri Takhteyev for markdown.py. 
import markdown

CellCMSConfig = ConfigParser.ConfigParser()
CellCMSConfig.read('cms.cfg')

# the general idea for this thing is that there be a thin shell of
# "normal" python to set up & feed the models which will do the heavy
# lifting & responses.

# let's build the models.
class Template(cells.Model):
    """A model which takes some HTML and adds a template around it"""
    # this could probably be done with one regex. I'm too lazy to figure it out.
    includetag1 = re.compile(r"\<\s*include_resource\s*name\s*=\s*" +\
                             r"'(?P<resource>[^']+)'\s*\/\>")
    includetag2 = re.compile(r'\<\s*include_resource\s*name\s*=\s*' +\
                             r'"(?P<resource>[^"]+)"\s*\/\>')
    
    def __init__(self, pagecache, *args, **kwargs):
        self.pagecache = pagecache
        cells.Model.__init__(self, *args, **kwargs)
    
    # INPUT CELLS
    source = cells.makecell(value="")
    template = cells.makecell(value="default.tmpl")

    # RULE CELLS
    @cells.fun2cell()
    def output(self, prev):
        print "Running template.output with", repr(self.source[:10])
        rendered = ""
        
        # do resource insertion        
        for line in open(self.template).readlines():
            # by looking for resource inclusion tags
            m = self.includetag1.search(line)
            if not m:
                m = self.includetag2.search(line)

            # loop over the line while we find them
            while m:
                # if the requested resource is "__body__", insert the source
                if m.group(1) == "__body__":
                    replacement = self.source

                # otherwise, just pull from the page cache (which may build
                # another Page)
                else:
                    replacement = self.pagecache[m.group(1)]

                line = line[:m.span()[0]] + replacement + line[m.span()[1]:]
                            
                # look for more resource inclusion tags
                m = self.includetag1.search(line)
                if not m:
                    m = self.includetag2.search(line)

            rendered += line

        return rendered

    
class Page(cells.Model):
    """A model to hold a single page, from request to page generation."""
    # Non-Cells
    cleanpath = re.compile(r"(/([A-Za-z0-9]+\.)*([A-Za-z0-9]*))*(\?.*)?")
    def __init__(self, pagecache, *args, **kwargs):
        self.pagecache = pagecache
        cells.Model.__init__(self, *args, **kwargs)
    
    # INPUT CELLS
    request = cells.makecell(value=None) # the Request object which builds this
    config = cells.makecell(value=None)  # a ConfigParser object
    built = cells.makecell(value=0)      # when this Page was last (re)built
    
    @cells.fun2cell(type=cells.RuleThenInputCell)
    def template(self, prev):
        t = Template(pagecache=self.pagecache)
        return t
    
    @cells.fun2cell(type=cells.RuleThenInputCell)
    def modified(self, prev):
        """When the data this cell depends on last changed"""
        path = self.source_info['path']
        if path:
            return os.stat(self.source_info['path'])[9]
        else:
            return 0.0

    # RULE CELLS
    @cells.fun2cell()
    def cleaned_path(self, prev):
        if not self.cleanpath.match(self.request.path):
            print "Illegal path request:", self.request.path
            return "/"
        return self.request.path

    @cells.fun2cell()
    def source_info(self, prev):
        """Returns some metadata about the source file for this Page"""
        response = { 'static': True,
                     'directory': True,
                     'path': None,
                     'valid': True }
        if glob.glob(self.config.get('directories', 'static') +
                     self.cleaned_path):
            staticpath = self.config.get('directories', 'static') + \
                         self.cleaned_path
            response['path'] = staticpath
            if os.path.isdir(staticpath):
                return response
            else:
                response['directory'] = False
                return response
        if glob.glob(self.config.get('directories', 'storage') + 
                     self.cleaned_path):
            fullpath = self.config.get('directories', 'storage') + \
                       self.cleaned_path
            response['static'] = False
            response['directory'] = False
            response['path'] = fullpath
            return response
        else:                           # error!
            response['valid'] = False
            return response

    @cells.fun2cell()
    def source(self, prev):
        """Holds the unrendered source data for this Page"""
        if not self.source_info['valid']:
            return "No such file"

        # all we need to do is depend on self.modified and the source
        # will be updated whenever the modification-time is
        # changed. I'm pretty sure this test will always fail.
        if self.modified <= self.built:
            return prev
        
        if self.source_info['static'] and self.source_info['directory']:
            currdir = os.getcwd()     # save old dir
            os.chdir(self.source_info['path']) # change to the requested dir
            out = ["Directory listing:", "------------------------------"]
            out += glob.glob("*")   # get the files here
            os.chdir(currdir)       # change back to the original dir
            return "\n".join(out)

        if self.source_info['static'] and not self.source_info['directory']:
            return open(self.source_info['path']).read()
        
        if not self.source_info['static']:
            return open(self.source_info['path']).read()

        else:
            return "Weird..."

    @cells.fun2cell()
    def templatized(self, prev):
        """Runs the source through a templating system"""
        # we only want to templatize dynamic content:
        if self.source_info['static'] or not self.source_info['path']: return ""
        # get the templatized page back
        return self.template.output
        
    @cells.fun2cell()
    def output(self, prev):        
        """Outputs the final, rendered version of this Page"""
        print "Page.output running on", repr(self.source_info['path'])
        out = ""
        if self.source_info['static']:
            out += self.source            
        else:
            out += self.templatized
            time = datetime.datetime.fromtimestamp(self.modified).ctime()
            out += "\nResource last changed:" + time
        
        return out
        

@Page.observer(attrib="request")
def pagelog_observer(self):
    """Each time a Page is created or modified, log."""
    if self.request:
        print self.request.client_address[0] + ":", str(self.request.path), \
              "-- created Page"

@Page.observer(attrib="source")
def source_obs(self):
    """Each time a new source gets generated, update its built
    time and feed it to the Page's template
    """
    if self.source_info['path']:
        self.built = self.modified

        if not self.source_info['static']:
            # first, turn the source into html by running it through markdown
            print "Templatizing", self.source_info['path']
            rendered_source = markdown.markdown(self.source)
            # and now push the rendered source into the template
            self.template.source = rendered_source


class PageCache(cells.Model):
    """Holds the Page objects; builds them upon requests"""
    request_handler = None
    
    def __init__(self):
        self.cache = {}
        
    def __getitem__(self, key):
        page = self.cache.get(key, None)
        if page:                        # exists? update the page
            print "Page cache updating mod-time on", repr(key)
            page.modified = os.stat(page.source_info['path'])[9]
        else:                           # doesn't? make the page
            page = Page(config=self.request_handler.config,
                        request=self.request_handler.request,
                        pagecache=self)
            page.pagecache = self
            self.cache[key] = page

        return page

    def __setitem__(self, key, value):
        print "Adding page for", repr(key), "to cache (cache now has", \
              str(len(self.cache.keys())), "keys)"
        self.cache[key] = value

    
class RequestHandler(cells.Model):
    """A model which turns GET requests into formatted content"""
    # NONCELLS
    special = ('/stats',)
    cache = None
        
    # INPUT CELLS
    config = cells.makecell(value=None)  # handle to the ConfigParser object    
    request = cells.makecell(value=None) # the input for the model

    # RULE CELLS        
    @cells.fun2cell()
    def request_key(self, prev):
        """Takes a BaseHTTPRequestHandler and makes a page key out of it"""
        if self.request:
            req = self.request
            return req.path        # eventually, more would go in here
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
            
        return self.cache[self.request_key]

@RequestHandler.observer(attrib="request")
def handlerlog_observer(self):
    """Each time a request is recieved, log"""
    if self.request:
        print self.request.client_address[0] + ":", str(self.request.path), \
              "-- got request"
        
    
handler = RequestHandler()             # make a new cellular handler
handler.config = CellCMSConfig         # and give it its configuration

pcache = PageCache()                   # make a new page cache
pcache.request_handler = handler
handler.cache = pcache                 # and give it to the RequestHandler
    
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


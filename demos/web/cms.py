#!/usr/bin/env python

"""
Cells CMS
(calling this a CMS is like calling a model rocket a space ship)

This works by setting up a BaseHTTPServer, and a custom request
handler to access pages in the PageCache. The cache builds pages upon
request if they don't exist, or brings pages' source filetimes up to
date if they do. A Page extends cells.Model, and it's here the cool
stuff happens:

When page '/foo' gets rendered, its template may pull in other
resources -- my default page template pulls in a '__header__' and
'__footer__'. When those Pages' resources are read by rendering page,
they discover they must inform that new page when they change. This,
of course, happens just because of the basic cells functionality. So
if you later alter one of the resources a rendered page depends on, it
will be informed of the change and re-render itself
automatically. There's no need to check up-to-dateness of the
resources a given page uses; it all happens automatically.
"""

import cells, BaseHTTPServer, ConfigParser, glob, os, re, time, datetime, urllib
import markdown           # props to Yuri Takhteyev for markdown.py.  

CellCMSConfig = ConfigParser.ConfigParser()
CellCMSConfig.read('cms.cfg')

class PageCache(object):
    """Builds & stores Page models"""
    def __init__(self):
        self.cache = {}
        
    def __getitem__(self, request):
        # we don't actually want to use the whole request object as the
        # key, just the bits we care about:
        page = self.cache.get(request.path, None)
        
        if not page:           # and if it doesn't exist in the cache, build it
            page = Page(cache=self, request=request)
            self.cache[request.path] = page # and put it in the cache

        print request.path, "resetting ctime"
        if page.is_static:
            print request.path, "is static, setting modified to", \
                  str(os.stat(page.static_path)[9])
            page.modified = os.stat(page.static_path)[9]
        elif page.is_dynamic:
            print request.path, "is dynamic, setting modified to", \
                  str(os.stat(page.dynamic_path)[9])
            page.modified = os.stat(page.dynamic_path)[9]

        print "Cache has", repr(self.cache.keys())

        return page

    def remove(self, request):
        self.cache.pop(request.path, None)

    
class Page(cells.Model):
    """A number of representations of a given resource (eg, '/foo')"""
    def __init__(self, cache, *args, **kwargs):
        self.cache = cache
        self.config = CellCMSConfig
        cells.Model.__init__(self, *args, **kwargs)

    special = re.compile(r"/__.*__")
    cleanpath = re.compile(r"(/([A-Za-z0-9]+\.)*([A-Za-z0-9]*))*(\?.*)?") 
    
    # INPUT CELLS
    request = cells.makecell(value=None)
    modified = cells.makecell(value=0)
    built = cells.makecell(value=0)

    # RULE CELLS
    @cells.fun2cell()
    def dirty_path(self, prev):
        """The not-cleaned path from self.request"""
        if not self.request:
            return "/"
        return self.request.path
    
    @cells.fun2cell()
    def cleaned_path(self, prev):
        """A safe path which may be used for reading/writing to"""
        if not self.cleanpath.match(self.dirty_path):
            print "Illegal path request:", self.dirty_path
            return "/"
        return self.dirty_path

    @cells.fun2cell()
    def dynamic_path(self, prev):
        """The location, on-disk, of the requested resource if it's dynamic"""
        return (self.config.get('directories', 'storage') + self.cleaned_path)

    @cells.fun2cell()
    def static_path(self, prev):
        """The location, on-disk, of the requested resource if it's static"""
        return (self.config.get('directories', 'static') + self.cleaned_path)

    # these just figure out if the request is for a dynamic or static
    # resource
    is_dynamic = cells.makecell(rule=lambda s,p: glob.glob(s.dynamic_path))
    is_static = cells.makecell(rule=lambda s,p: glob.glob(s.static_path))

    @cells.fun2cell()
    def is_directory(self, prev):
        """Is the request for a directory?"""
        return os.path.isdir(self.static_path)

    @cells.fun2cell()
    def is_special(self, prev):
        """Is the request for a 'special' resource (eg, '__foo__')"""
        return self.special.match(self.cleaned_path)

    @cells.fun2cell()
    def is_valid(self, prev):
        """Is the resource available on-disk?"""
        return self.is_dynamic or self.is_static

    @cells.fun2cell()
    def raw_source(self, prev):
        """Holds the unrendered source data for this Page"""
        if not self.is_valid:
            return "Resource not found. You can edit it below."

        # all we need to do is depend on self.modified and the source
        # will be updated whenever the modification-time is
        # changed. I'm pretty sure this test will always fail.
        if self.modified < self.built:
            return prev
        
        if self.is_directory:           # implies is_static
            currdir = os.getcwd()       # save old dir
            os.chdir(self.static_path)  # change to the requested dir
            out = ["Directory listing:", "------------------------------"]
            out += glob.glob("*")       # get the files here
            os.chdir(currdir)           # change back to the original dir
            return "\n".join(out)

        if self.is_static:              # because of above test, not a dir.
            return open(self.static_path).read()
        
        if self.is_dynamic:
            return (open(self.dynamic_path).read())

        else:
            return "Should not have got here!"

    @cells.fun2cell()
    def source(self, prev):
        """Holds the rendered, untemplatized version of this Page"""
        if self.is_dynamic:
            return markdown.markdown(self.raw_source)
        else:
            return self.raw_source
    
    @cells.fun2cell()
    def template_file(self, prev):
        """Determines which template to apply to this Page depending
        on request type"""
        if self.is_special:
            return "templates/just_edit.tmpl"
        if self.is_directory:
            return "templates/directory.tmpl"
        if self.is_static:
            return "templates/static.tmpl"
        else:
            return "templates/full.tmpl"
        
    @cells.fun2cell()
    def templatized(self, prev):
        """Holds the rendered, templatized version of this Page"""
        if self.is_dynamic or self.is_directory or not self.is_valid:
            return Template(cache=self.cache,
                            page=self,
                            template=self.template_file).render()
        else:
            return self.raw_source

@Page.observer(attrib="source")
def source_obs(self):
    """Each time a new source gets generated, update its built-time
    """
    print "reset built-time"
    self.built = self.modified

@Page.observer(attrib="request")
def source_obs(self):
    print self.cleaned_path, "reset request"

@Page.observer(attrib="templatized")
def templatized_log_obs(self):
    """Each time the templatized version of the Page changes, log to stdout"""
    print self.cleaned_path, "regenerated"

class Template(object):
    """An object which applies a template to a chunk of text."""
    # this could probably be done with one regex. I'm too lazy to figure it out.
    # finds tags that look like <include_resource name="blah" />
    includetag1 = re.compile(r"\<\s*include_resource\s*name\s*=\s*" +\
                             r"'(?P<resource>[^']+)'\s*\/\>")
    includetag2 = re.compile(r'\<\s*include_resource\s*name\s*=\s*' +\
                             r'"(?P<resource>[^"]+)"\s*\/\>')

    def __init__(self, page, cache, template="default.tmpl"):
        self.page = page
        self.cache = cache
        self.template = template

    def render(self):
        """Actually applies the template"""
        rendered = ""
        
        # do resource insertion        
        for line in open(self.template).readlines():
            # by looking for resource inclusion tags
            m = self.includetag1.search(line)
            if not m:
                m = self.includetag2.search(line)

            # loop over the line while we find them
            while m:
                # if the requested resource is "__body__", insert the
                # page's rendered source
                var = m.group(1)
                if var == "__body__":
                    replacement = self.page.source
                elif var == "__rawbody__":
                    replacement = self.page.raw_source
                elif var == "__path__":
                    replacement = self.page.cleaned_path
                
                # otherwise, just pull from the page cache (which may build
                # another Page)
                else:
                    req = Request(path="/" + var) # dummy request
                    replacement = self.cache[req].source

                line = line[:m.span()[0]] + replacement + line[m.span()[1]:]
                            
                # look for more resource inclusion tags
                m = self.includetag1.search(line)
                if not m:
                    m = self.includetag2.search(line)

            rendered += line
            
        return rendered

# Make a page cache object
pages = PageCache()

class Request(object):
    """Just a container for the RequestHandler's current request data"""
    def __init__(self, request=None, path=None):
        # since we can request resources from a template or a "real"
        # request, there's two versions of this object, with a flag to
        # tell them apart
        if request:
            self.client_address = request.client_address
            self.command = request.command
            self.path = request.path
            self.request_version = request.request_version
            self.headers = request.headers
            self.rfile = request.rfile
            self.wfile = request.wfile
            self.is_dummy = False       # "real" request
        else:
            self.client_address = None
            self.command = None
            self.path = path
            self.request_version = None
            self.headers = None
            self.rfile = None
            self.wfile = None
            self.is_dummy = True        # template request

class CellRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Makes BaseHTTPServer use the page cache"""
    cleanpath = re.compile(r"(/([A-Za-z0-9]+\.)*([A-Za-z0-9]*))*(\?.*)?")     

    def do_GET(self):
        print >>self.wfile, pages[Request(request=self)].templatized

    def do_POST(self):
        # read the POSTed data
        content_len = int(self.headers.getheader('content-length'))
        postdata = self.rfile.read(content_len)
        newbody = filter(lambda a: a[0] == "newbody",
                         [s.split("=") for s in postdata.split("&")])[0][1]

        # check that we should write to the requested resource, and if
        # so write to it
        if self.cleanpath.match(self.path):
            out = open(CellCMSConfig.get('directories', 'storage') + self.path,
                       'w')
            out.write(urllib.unquote_plus(newbody))
            out.close()

        # this is inelegant, but it gets the job done: to get the edit
        # box a user must have navigated to the resource they're
        # changing. this may have generated a Page filled with
        # "resource not found"; instead of trying to make that Page
        # regenerate, I just nuke it...
        if not pages[Request(request=self)].is_valid:
            pages.remove(Request(request=self))
        # and this request makes a new one.
        print >>self.wfile, pages[Request(request=self)].templatized
    
# Finally, set the server moving:
print "Starting server at", CellCMSConfig.get('server', 'address'), "on port", \
      CellCMSConfig.get('server', 'port')
server_address=(CellCMSConfig.get('server', 'address'),
                CellCMSConfig.getint('server', 'port'))
httpd = BaseHTTPServer.HTTPServer(server_address, CellRequestHandler)
print "... server started."
httpd.serve_forever()

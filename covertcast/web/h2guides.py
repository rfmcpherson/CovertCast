from bs4 import BeautifulSoup
from collections import namedtuple
import multiprocessing
import sys

if sys.platform != "win32":
    import prefetching
from obj import Resource

# Abstract class to decide which URLs to load and send
# Child classes are in charge of filling out:
#   self._main_freq
#   self._main_url
#   self._update(page)
class Guide():
    def __init__(self):
        # how often to send the main page
        self._main_freq = None
        
        # track number of stories sent 
        self._story_count = 0
        
        # track number of next() calls
        self._next_count = 0
        
        # the main page's URL
        self._main_url = None
        
        # list of the story page's URL
        self._story_l = []
        

    def _fix_resources(self, resources): 
        return resources

        
    # updates self._stories based upon the latest main page
    def _update(self, page):
        pass
        
        
    # returns the "data" of the next page to send
    def next(self):

        url_l = []
        content_l = []

        print("Next called")

        # if it's time to send a main page
        if (self._next_count % self._main_freq) == 0:

            # Put this in it's own Process because Ghost.py has mp issues...
            results = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=prefetching.fetch_content, 
                args=(self._main_url, results))
            p.start()
            content_l = results.get()
            p.join()

            # Clean up site specific stuff
            content_l = self._fix_resources(content_l)

            # update the story list
            self._update(content_l[0].data)
            print("Update called")

        # else we're sending a story page
        elif self._story_l:
            story_num = self._story_count % len(self._story_l)
            story_url = self._story_l[story_num]

            # Put this in it's own Process because Ghost.py has mp issues...
            results = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=prefetching.fetch_content, 
                args=(story_url, results))
            p.start()
            content_l = results.get()
            p.join()

            # Clean up site specific stuff
            content_l = self._fix_resources(content_l)

            self._story_count += 1

        self._next_count += 1
        return content_l


# BBC News
# (top 3)
class BBCGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://www.bbc.com/news"

    def _update(self, page):
        try:
            soup = BeautifulSoup(page, "html.parser")
        except Exception as e:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = []
            
            for i in range(1,2):
                entityid = "container-top-stories#{}".format(i)
                story = soup.find("div", {"data-entityid":entityid})
                story_url = story.find("a", {"class":"title-link"})
                story_url = "http://www.bbc.com"+story_url["href"]
                print(story_url)
                self._story_l.append(story_url)

            return True


# New York Times
# (top 3)
class NYTimesGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://www.nytimes.com"

    def _update(self, page):
        try:
            soup = BeautifulSoup(page, "html.parser")
        except:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = [] 

            stories = soup.findAll("h2", {"class":"story-heading"})
            for i in range(3):
                story_url = stories[i].find("a")["href"]
                print(story_url)
                self._story_l.append(story_url)


# New York Times Mobile
# (top 3)
class NYTimesMobileGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://mobile.nytimes.com"

    def _update(self, page):
        try:
            soup = BeautifulSoup(page, "html.parser")
        except:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = [] 

            stories = soup.findAll("a", {"class":"sfgAsset-link"})
            for i in range(3):
                if stories[i]["href"].startswith("http"):
                    story_url = stories[i]["href"]
                else:
                    story_url = self._main_url + stories[i]["href"]
                print(story_url)
                self._story_l.append(story_url)

# USA Today
# (top 3)
class USATodayGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://www.usatoday.com"

    def _update(self, page):
        try:
            soup = BeautifulSoup(page, "html.parser")
        except:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = [] 

            top_url = soup.find("a", {"class", "lead-story"})["href"]
            story_url = self._main_url + top_url
            print(story_url)
            self._story_l.append(story_url)

            stories = soup.findAll("a", {"class":"inline-item"})
            for i in range(2):
                story_url = self._main_url + stories[i]["href"]
                print(story_url)
                self._story_l.append(story_url)

 
# Wall Street Journal
# (top 3)
class WSJGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://www.wsj.com"

    def _update(self, page):
        try:
            soup = BeautifulSoup(page, "html.parser")
        except:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = [] 

            stories = soup.findAll("a", {"class":"wsj-headline-link"})
            
            story_url = stories[9]["href"]
            print(story_url)
            self._story_l.append(story_url)
            story_url = stories[15]["href"]
            print(story_url)
            self._story_l.append(story_url)
            story_url = stories[16]["href"]
            print(story_url)
            self._story_l.append(story_url)

        
# The Guardian
# (top 3)
class GuardianGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://www.theguardian.com/us"

    def _update(self, page):
        try:
            soup = BeautifulSoup(page, "html.parser")
        except:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = [] 

            stories = soup.findAll("a", {"class", "fc-item__link"})
            for i in range(3):
                story_url = stories[i]["href"]
                print(story_url)
                self._story_l.append(story_url)


# Washington Post Mobile
# (top 3)
# UNFINISHED: DOESN'T WORK WITH OLD VERSION OF GHOST.PY
class WPostGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        self._main_freq = 4
        self._main_url = "http://m.washingtonpost.com/"

    def _update(self, page):
        return
        try:
            soup = BeautifulSoup(page, "html.parser")
        except:
            print("Error in BeautifulSoup:", e)
            return False
        else:
            self._story_l = []

       
# Loads data locally
class LocalGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        
    # just clober the parent code
    def next(self):
        import pickle

        location = "./web/testdata/main.html.pickle"
        location = "./web/testdata/simple.html.pickle"
        location = "./web/testdata/bbc.html.pickle"
        
        with open(location,"rb") as f:
            data = pickle.load(f)
            
        content_l = data[1]
            
        return content_l
        
        
# A fake guide for testing purposes
# Only sends the main page
class SimpleGuide(Guide):
    def __init__(self):
        Guide.__init__(self)
        
        self._main_freq = 1
        self._main_url = "http://www.cs.utexas.edu/~richard/test/main.html"
        #self._main_url = "http://www.cs.utexas.edu/~richard/test/simple.html"
        

# Sends the same set of raw data every time
# Unused
# The actual size of the data is 103 images
class RawGuide(Guide):
    def __init__(self):
      self._first = True
      self._num_images = 100
      self._size_images = int((1280/8 * 720/8 * 2*3 - 40 - 32)/8)

    def next(self):
        import random

        data = b""

        if self._first:            
            random.seed("covertcast")
            for image in range(self._num_images):
                print("Image: {}".format(image))
                raw = []
                for i in range(self._size_images):
                    raw.append(random.randint(0,255))
                data += bytes(raw)
            self._first = False
            
        print(len(data))

        return [Resource("http://www.1000julys.com", 200, data)]
        

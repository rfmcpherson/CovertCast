from ghost import Ghost # USE VERSION 0.1.2
import sys
import time
import traceback


from obj import Resource

ua_string = "Mozilla/5.0 (Linux; Android 4.0.4; Galaxy Nexus Build/IMM76B) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.133 Mobile Safari/535.19"

#Resource = namedtuple("Resource", ["url", "status", "data"])

# Takes a URL
# Returns (list of urls, list of page contents)
def fetch_content(url, queue):

    # Ghost.py stuff
    ghost = Ghost(
        user_agent=ua_string,
        #viewport_size=(2000,2000),
        wait_timeout=10
    ) 

    #with ghost.start(java_enabled=False) as session:#user_agent=ua_string) as session:

    # set to use privoxy proxy defaults
    ghost.set_proxy(type_="http", host="127.0.0.1", port=8118)

    # make the Ghost request
    # page is resources[0]
    for i in range(5):
        try:
            #ghost.open(url, wait=False)
            #time.sleep(5)
            #page, resources = ghost.wait_for_page_loaded()
            page, resources = ghost.open(url)
        except Exception as e:
            print("Error with ", url)
            print(e)
            #traceback.print_tb(sys.exc_info()[2])
            continue

        if page != None:
            break

    if page == None:
        print("Unrecoverable error with Ghost.py", url)

    ghost.exit()

    # create the list of dependencies
    '''
    url_l = []
    for r in resources:
        url_l.append(r.url)
    '''

    # list of [url, data] lists
    data_l = []

    # list of fetched urls
    fetched = []

    p_r = [page]
    p_r.extend(resources)
    
    #print(page.content)

    # fill data_l
    for r in p_r:

        url = r.url.split("?")[0].strip()

        # if we haven't seen this before
        if not url in fetched:

            #print(url)
            fetched.append(url)

            # if it's ASCII
            if type(r.content) == str:
                data = bytes(r.content, encoding='utf-8')
            else:
                data = r.content.data()

            data_l.append(Resource(url, r.http_status, data))

    #queue.put((url_l, data_l))
    queue.put(data_l)

def count_types(pages):
    
    counts = {"image":0, "css":0, "js":0, "html":0, "unknown":0}
    image_endings = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]

    for page in pages:

        image = False
        for ending in image_endings:
            if page.url.endswith(ending):
                counts["image"] += 1
                image = True
                break
        if image:
            continue
        
        if page.url.endswith(".css"):
            counts["css"] += 1
            continue

        if page.url.endswith(".js"):
            counts["js"] += 1
            continue

        if page.data.strip().lower().startswith(b"<!doctype html"):
            counts["html"] += 1
            continue

        counts["unknown"] += 1
        print()
        print(page.url)
        print(page.data[:25])
        print()

    return counts
        

def pick():
    import pickle
    import multiprocessing
    
    url = "http://www.cs.utexas.edu/~richard/test/main.html" # complicated page
    url = "http://www.cs.utexas.edu/~richard/test/simple.html" # simple page
    url = "http://www.bbc.com/news" # bbc news page
    url = 'http://www.wsj.com/articles/asia-struggles-for-a-solution-to-its-missing-women-problem-1448545813?tesla=y'

    url = 'http://www.nytimes.com'
    url = 'http://www.bbc.com/news'
    url = 'http://www.usatoday.com/story/news/environment/2015/12/10/how-unchecked-pumping-sucking-aquifers-dry-india/74634336/'
    url = 'http://www.usatoday.com/story/news/politics/2015/12/11/obama-executive-order-federal-employees-christmas-eve-half-day-off/77167136/'
    #url = 'http://www.usatoday.com'
    #url = 'http://www.wsj.com'
    #url = 'http://www.theguardian.com/us'

    q = multiprocessing.Queue()
    fetch_content(url, q)

    data_l = q.get()

    print(len(data_l))


    total = 0
    for i in data_l:
        #print(len(i.data), i.url)
        total += len(i.data)

    print(total)

    '''
    with open("./web/testdata/bbc7.html.pickle","wb") as f:
        pickle.dump([url_l, data_l], f)
    '''
    #print(count_types(data_l))

    #print(url_l)
    #print(len(data_l))
    print("done")
    return

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Small best-effort change detector for official source hubs. Does NOT ingest laws automatically."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

HUBS = {
 "gstcouncil": "https://gstcouncil.gov.in/what-s-new",
 "goa_gst": "https://statetax.goa.gov.in/GSTActs.html",
 "income_tax": "https://www.incometaxindia.gov.in/en/income-tax-act-202511",
 "gst_returns": "https://tutorial.gst.gov.in/userguide/returns/GSTR3B.htm",
}
class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.discard = 0
        self.text = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","noscript"):
            self.discard += 1
        if tag == "a":
            for key,value in attrs:
                if key == "href" and value:
                    self.links.append(value.strip())
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.discard:
            self.discard -= 1
    def handle_data(self,data):
        if not self.discard and data.strip():
            self.text.append(data.strip())

def fetch_fingerprint(url):
    req = Request(url,headers={"User-Agent":"IndiaLegalSourceMonitor/0.1 (document metadata checks, contact repository owner)"})
    with urlopen(req,timeout=18) as response:
        html=response.read(2_500_000).decode("utf-8","replace")
    parser=Visible()
    parser.feed(html)
    cleaned = " ".join(parser.text)
    # Deliberately stable-ish fingerprint; date/time widgets can still produce noise.
    cleaned = re.sub(r"\s+"," ",cleaned)
    links=sorted(set(x for x in parser.links if not x.startswith(("javascript:","#"))))
    return hashlib.sha256((cleaned+"\n"+"\n".join(links)).encode("utf-8")).hexdigest(),len(links)

def check(state_path, write=False):
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    events = []
    for name,url in HUBS.items():
        try:
            digest,links=fetch_fingerprint(url)
            old=state.get(name,{}).get("sha256")
            condition="changed" if old and old!=digest else "baseline" if not old else "unchanged"
            events.append({"name":name,"url":url,"event":condition,"links":links,"sha256":digest})
            if write:
                state[name]={"url":url,"sha256":digest}
        except (TimeoutError,URLError,HTTPError,ValueError) as exc:
            events.append({"name":name,"url":url,"event":"fetch_error","detail":str(exc)[:160]})
    if write:
        state_path.parent.mkdir(parents=True,exist_ok=True)
        state_path.write_text(json.dumps(state,sort_keys=True,indent=2)+"\n")
    return events

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--state",type=pathlib.Path,default=pathlib.Path("data/watch-state.json"))
    ap.add_argument("--write",action="store_true",help="Persist observed fingerprints; no law updates")
    args=ap.parse_args()
    print(json.dumps(check(args.state,args.write),indent=2))

#!/usr/bin/env python3
"""No-download CC0 catalog diagnostic. Log metadata shape only."""
import json,urllib.parse
import audio_runtime_v6 as a
for q in ("ambient music","ambient","piano","nature"):
    try:
        url=a.API+"?"+urllib.parse.urlencode({"q":q,"license":"cc0","page_size":12})
        body=json.loads(a.read_url(url,128000))
        found=body.get("results",[])
        print("OPENVERSE_CC0_DIAGNOSTIC",q,"results",len(found),
              "candidate_fields",[{
                 "license":r.get("license"),"type":r.get("filetype"),"duration":r.get("duration"),
                 "size":r.get("filesize"),"url_https":a.public_https(r.get("url")),
                 "license_cc0":str(r.get("license_url","")).startswith("https://creativecommons.org/publicdomain/zero/"),
                 "source_https":a.public_https(r.get("foreign_landing_url"))
              } for r in found[:6]])
    except Exception as exc:print("OPENVERSE_DIAGNOSTIC_ERROR",q,type(exc).__name__)

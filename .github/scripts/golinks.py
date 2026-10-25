"""go.vansh.nyc links for the issue-form Action.

Every job's url in listings.json is https://go.vansh.nyc/<key>; the real URL lives with the
go.vansh.nyc Worker. With GOLINKS_CREATE_SECRET set (an Actions secret that can only look up a
URL and add new jobs), a new job gets its go link here, and a real URL from an issue is matched
to the listing it belongs to. Without it, jobs keep the URL they were submitted with, and jobsync
links them on its next run.
"""

import json
import os
import re
import urllib.parse
import urllib.request

API = "https://go.vansh.nyc"
GO = re.compile(r"^https://go\.vansh\.nyc/[0-9A-Za-z]{1,6}$")


def enabled():
    return bool(os.environ.get("GOLINKS_CREATE_SECRET"))


def _call(path, body=None):
    request = urllib.request.Request(
        API + path, data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ["GOLINKS_CREATE_SECRET"],
                 "Content-Type": "application/json", "User-Agent": "listings-issue-form"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def urls_for(url):
    """Every url a listing could have for this submitted url: the url itself and its go links."""
    if not enabled() or GO.match(url):
        return {url}
    keys = _call("/api/lookup?url=" + urllib.parse.quote(url, safe=""))["keys"]
    return {url} | {f"{API}/{key}" for key in keys}


def link(listing_id, url, repo):
    """The go link for a new job (made now), or url unchanged when go links are off."""
    if not enabled() or GO.match(url):
        return url
    key = _call("/api/links", [{"listing_id": listing_id, "url": url, "repo": repo}])["links"][0]["key"]
    return f"{API}/{key}"

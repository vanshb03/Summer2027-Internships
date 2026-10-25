import re
import json
import os
from datetime import datetime
from collections import defaultdict
import time

# Set the TZ environment variable to PST
os.environ['TZ'] = 'America/Los_Angeles'
time.tzset()

# Constants for the apply button
APPLY_BUTTON = "https://i.imgur.com/u1KNU8z.png"


def setOutput(key, value):
    if output := os.getenv('GITHUB_OUTPUT', None):
        with open(output, 'a') as fh:
            print(f'{key}={value}', file=fh)


# This function is used to set the error message in the GitHub Actions output
def fail(why):
    setOutput("error_message", why)
    exit(1)

def getLocations(listing):
    locations = "</br>".join(listing["locations"])
    if len(listing["locations"]) <= 3:
        return locations
    num = str(len(listing["locations"])) + " locations"
    return f'<details><summary>**{num}**</summary>{locations}</details>'


def getSponsorship(listing):
    if listing["sponsorship"] == "Does Not Offer Sponsorship":
        return " 🛂"
    elif listing["sponsorship"] == "U.S. Citizenship is Required":
        return " 🇺🇸"
    return ""


# Each README page's code on go.vansh.nyc (sources table in jobbots/golinks), so a click from the page
# is counted as coming from it. listings.json keeps the bare go link; only the pages carry ?s=.
SOURCES = {"README.md": "y", "OFFSEASON_README.md": "z"}
GO_LINK = re.compile(r"^https://go\.vansh\.nyc/[0-9A-Za-z]{1,6}$")


def getLink(listing, source=None):
    if not listing["active"]:
        return "🔒"
    link = listing["url"]
    if source and GO_LINK.match(link):
        link += "?s=" + source
    # return f'<a href="{link}" style="display: inline-block;"><img src="{SHORT_APPLY_BUTTON}" width="160" alt="Apply"></a>'

    return f'<a href="{link}"><img src="{APPLY_BUTTON}" width="118" alt="Apply"></a>'


def create_md_table(listings, source=None):
    table = ""
    table += "| Company | Role | Location | Application/Link | Date Posted |\n"
    table += "| ------- | ---- | -------- | ---------------- | ----------- |\n"

    curr_company_key = None
    curr_date = None
    for listing in listings:
        
        # parse listing information
        company_url = listing["company_url"]
        company = f"**[{listing['company_name']}]({company_url})**" if len(company_url) > 0 else listing["company_name"]
        location = getLocations(listing)
        position = listing["title"] + getSponsorship(listing)
        link = getLink(listing, source)

        # parse listing date
        year_month = datetime.fromtimestamp(listing["date_posted"]).strftime('%b %Y')
        day_month = datetime.fromtimestamp(listing["date_posted"]).strftime('%b %d')
        is_before_july_18 = datetime.fromtimestamp(listing["date_posted"]) < datetime(2023, 7, 18, 0, 0, 0)
        date_posted = year_month if is_before_july_18 else day_month

        # add ↳ to listings with the same company
        # as "header" company listing (most recent)
        company_key = listing['company_name'].lower()
        if curr_company_key == company_key and curr_date == date_posted:
            company = "↳"
        else:
            curr_company_key = company_key
            curr_date = date_posted

        # create table row
        table += f"| {company} | {position} | {location} | {link} | {date_posted} |\n"

    return table


def getListingsFromJSON(filename=".github/scripts/listings.json"):
    with open(filename) as f:
        listings = json.load(f)
        print(f"Received {len(listings)} listings from listings.json")
        return listings


def embedTable(listings, filepath):
    newText = ""
    readingTable = False
    with open(filepath, "r") as f:
        for line in f.readlines():
            if readingTable:
                if "|" not in line and "TABLE_END" in line:
                    newText += line
                    readingTable = False
                continue
            else:
                newText += line
                if "TABLE_START" in line:
                    readingTable = True
                    newText += "\n" + \
                        create_md_table(listings, SOURCES.get(filepath)) + "\n"
    with open(filepath, "w") as f:
        f.write(newText)


def sortListings(listings):
    oldestListingFromCompany = {}
    linkForCompany = {}
    for listing in listings:
        date_posted = listing["date_posted"]
        if listing["company_name"].lower() not in oldestListingFromCompany or oldestListingFromCompany[listing["company_name"].lower()] > date_posted:
            oldestListingFromCompany[listing["company_name"].lower()] = date_posted
        if listing["company_name"] not in linkForCompany or len(listing["company_url"]) > 0:
            linkForCompany[listing["company_name"]] = listing["company_url"]
            
    listings.sort(
        key=lambda x: (
            x["active"],  # Active listings first
            datetime(
                datetime.fromtimestamp(x["date_posted"]).year,
                datetime.fromtimestamp(x["date_posted"]).month,
                datetime.fromtimestamp(x["date_posted"]).day
            ),
            x['company_name'].lower(),
            x['date_updated']
        ),
        reverse=True
    )
    for listing in listings:
        listing["company_url"] = linkForCompany[listing["company_name"]]
    return listings


def checkSchema(listings):
    props = ["source", "company_name",
             "id", "title", "active", "date_updated", "is_visible",
             "date_posted", "url", "locations", "season", "company_url",
             "sponsorship"]
    for listing in listings:
        for prop in props:
            if prop not in listing:
                fail("ERROR: Schema check FAILED - object with id " +
                      listing["id"] + " does not contain prop '" + prop + "'")

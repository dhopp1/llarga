import math
import requests
import re
import time
import json
from urllib.parse import quote, urlparse


from gnews import GNews
from googlesearch import search
from bs4 import BeautifulSoup

# supported countries/languages
available_countries = {
    "Australia": "AU",
    "Botswana": "BW",
    "Canada ": "CA",
    "Ethiopia": "ET",
    "Ghana": "GH",
    "India ": "IN",
    "Indonesia": "ID",
    "Ireland": "IE",
    "Israel ": "IL",
    "Kenya": "KE",
    "Latvia": "LV",
    "Malaysia": "MY",
    "Namibia": "NA",
    "New Zealand": "NZ",
    "Nigeria": "NG",
    "Pakistan": "PK",
    "Philippines": "PH",
    "Singapore": "SG",
    "South Africa": "ZA",
    "Tanzania": "TZ",
    "Uganda": "UG",
    "United Kingdom": "GB",
    "United States": "US",
    "Zimbabwe": "ZW",
    "Czech Republic": "CZ",
    "Germany": "DE",
    "Austria": "AT",
    "Switzerland": "CH",
    "Argentina": "AR",
    "Chile": "CL",
    "Colombia": "CO",
    "Cuba": "CU",
    "Mexico": "MX",
    "Peru": "PE",
    "Venezuela": "VE",
    "Belgium ": "BE",
    "France": "FR",
    "Morocco": "MA",
    "Senegal": "SN",
    "Italy": "IT",
    "Lithuania": "LT",
    "Hungary": "HU",
    "Netherlands": "NL",
    "Norway": "NO",
    "Poland": "PL",
    "Brazil": "BR",
    "Portugal": "PT",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Sweden": "SE",
    "Vietnam": "VN",
    "Turkey": "TR",
    "Greece": "GR",
    "Bulgaria": "BG",
    "Russia": "RU",
    "Ukraine ": "UA",
    "Serbia": "RS",
    "United Arab Emirates": "AE",
    "Saudi Arabia": "SA",
    "Lebanon": "LB",
    "Egypt": "EG",
    "Bangladesh": "BD",
    "Thailand": "TH",
    "China": "CN",
    "Taiwan": "TW",
    "Hong Kong": "HK",
    "Japan": "JP",
    "Republic of Korea": "KR",
}

available_languages = {
    "english": "en",
    "indonesian": "id",
    "czech": "cs",
    "german": "de",
    "spanish": "es-419",
    "french": "fr",
    "italian": "it",
    "latvian": "lv",
    "lithuanian": "lt",
    "hungarian": "hu",
    "dutch": "nl",
    "norwegian": "no",
    "polish": "pl",
    "portuguese brasil": "pt-419",
    "portuguese portugal": "pt-150",
    "romanian": "ro",
    "slovak": "sk",
    "slovenian": "sl",
    "swedish": "sv",
    "vietnamese": "vi",
    "turkish": "tr",
    "greek": "el",
    "bulgarian": "bg",
    "russian": "ru",
    "serbian": "sr",
    "ukrainian": "uk",
    "hebrew": "he",
    "arabic": "ar",
    "marathi": "mr",
    "hindi": "hi",
    "bengali": "bn",
    "tamil": "ta",
    "telugu": "te",
    "malyalam": "ml",
    "thai": "th",
    "chinese simplified": "zh-Hans",
    "chinese traditional": "zh-Hant",
    "japanese": "ja",
    "korean": "ko",
}


# helping functions for decoding google news URLs
def get_decoding_params(gn_art_id):
    response = requests.get(f"https://news.google.com/articles/{gn_art_id}")
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    div = soup.select_one("c-wiz > div")
    return {
        "signature": div.get("data-n-a-sg"),
        "timestamp": div.get("data-n-a-ts"),
        "gn_art_id": gn_art_id,
    }


def decode_urls(articles):
    articles_reqs = [
        [
            "Fbv4je",
            f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{art["gn_art_id"]}",{art["timestamp"]},"{art["signature"]}"]',
        ]
        for art in articles
    ]
    payload = f"f.req={quote(json.dumps([articles_reqs]))}"
    headers = {"content-type": "application/x-www-form-urlencoded;charset=UTF-8"}
    response = requests.post(
        url="https://news.google.com/_/DotsSplashUi/data/batchexecute",
        headers=headers,
        data=payload,
    )
    response.raise_for_status()
    return [
        json.loads(res[2])[1] for res in json.loads(response.text.split("\n\n")[1])[:-2]
    ]


def get_news(news_obj, search_term, site_list=[]):
    "get google news results for a given search term and site list"
    search_term = "%20".join(search_term.split(" "))
    if site_list == [""] or site_list == []:
        query = f"""/search?q={search_term}"""
        results = news_obj._get_news(query)
    else:
        results = []
        for i in range(len(site_list)):
            query = f"""/search?q=site:{site_list[i]}+{search_term}"""
            tmp_result = news_obj._get_news(query)
            tmp_result = tmp_result[: math.floor(news_obj.max_results / len(site_list))]
            results += tmp_result
    return results


def gen_google_news(
    language,
    max_results,
    country,
    start_date,  # in (yyyy,mm,dd) format
    end_date,
    search_term,
    site_list,
):
    "get google news results"
    news_obj = GNews(
        language=language,
        max_results=max_results,
        country=country,
        start_date=start_date,
        end_date=end_date,
    )
    results = get_news(news_obj, search_term, site_list)

    # don't return .asp or .page results
    results = [x for x in results if x["url"][-4:] not in [".asp", "page"]]

    # convert google news URL to normal URL
    for i in range(len(results)):
        try:
            art_id = re.search(r"articles/(.+?)\?", results[i]["url"]).group(1)
            decoding_params = get_decoding_params(art_id)
            url = decode_urls([decoding_params])
            results[i]["url"] = url[0]
            time.sleep(1)
        except:
            pass

    return results


def extract_domain(url):
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        result = parsed.netloc
    else:
        # Prepend 'http://' to ensure proper parsing if no scheme is present
        parsed_padded = urlparse("http://" + url)
        result = parsed_padded.netloc
    result = result.replace("www.", "")
    name = result.replace("." + result.split(".")[-1], "")
    return [result, name]


def gen_google_search(
    query,
    language,
    country,
    max_results,
    site_list=[],
):
    "get google search results"
    urls = [
        x
        for x in search(
            query,
            region=country.lower(),
            lang=language,
            num_results=max_results,
            unique=True,
        )
        if not (any(sub in x for sub in ["google.com", "gstatic.com"]))
    ]

    # put in format of google news
    final_results = [
        {
            "title": extract_domain(x)[0],
            "description": extract_domain(x)[1],
            "published date": "",
            "url": x,
            "publisher": {
                "href": "",
                "title": "",
            },
        }
        for x in urls
    ]

    # don't return .asp or .page results
    final_results = [x for x in final_results if x["url"][-4:] not in [".asp", "page"]]

    # format data to be exact same style as gnews
    return final_results

from gnews import GNews
import math


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


def get_news(news_obj, search_term, site_list=[]):
    "get google news results for a given search term and site list"
    search_term = "%20".join(search_term.split(" "))
    if len(site_list) == 0:
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
    return results

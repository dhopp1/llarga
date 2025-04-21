from duckduckgo_search import DDGS
import re
import requests
from readability import Document
from lxml import html
import pandas as pd


def is_url(s):
    """Check if the input is a single formatted URL or a comma-separated list of them."""
    URL_REGEX = re.compile(
        r"^(https?://)"  # scheme
        r"([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"  # domain
        r"(:\d+)?"  # optional port
        r"(/[^\s]*)?$"  # optional path/query
    )

    def is_formatted_url(url):
        """Check if a single URL is in valid format (does not verify if it's live)."""
        return bool(URL_REGEX.match(url.strip()))

    urls = [url.strip() for url in s.split(",")]
    return all(is_formatted_url(url) for url in urls)


def search_web_duckduckgo(query, news=False, max_results=10):
    results = pd.DataFrame(columns=["url", "title", "date", "source"])
    with DDGS() as ddgs:
        search = (
            ddgs.news(query, max_results=max_results)
            if news
            else ddgs.text(query, max_results=max_results)
        )
        for r in search:
            tmp = pd.DataFrame(
                {
                    "url": r["url"] if news else r["href"],
                    "title": r["title"],
                    "date": str(pd.to_datetime(r["date"]).date()) if news else "",
                    "source": r["source"] if news else "",
                },
                index=[0],
            )
            results = pd.concat([results, tmp], ignore_index=True)
    return results


def extract_main_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        doc = Document(response.text)
        summary_html = doc.summary()

        # Optionally: Convert summary_html to plain text
        tree = html.fromstring(summary_html)
        main_text = tree.text_content().strip()

        return main_text

    except:
        return ""


def gen_url_content(urls):
    "return content of explicitly asked for urls"

    final_text = f"{urls}. You will be provided with the content for this URL(s). In a bulleted list, list the URL, then summarize the content. If no useful content is provided for the URL, then say 'The content of this URL could not be fetched'.\n\n"
    for i in range(len(urls.split(","))):
        body = extract_main_content(urls.split(",")[i]).replace("\n", "")

        final_text += f"\n\nURL: {urls.split(',')[i]}"
        final_text += f"\n\nmain article: {body}"

    return final_text


def gen_web_search(query, news=False, max_results=5):
    results = search_web_duckduckgo(query, news, max_results)
    results["body"] = ""

    final_text = f"""{query}\n\nHere is some contextual information from the web to help answer the question. At the end of any sentences that you support from the context, place the following text: <span class="tooltip superscript-link">†<span class="tooltiptext">url</span></span>, where you replace 'url' with the URL of the story you are referencing. If no useful information is provided, say 'Sorry I couldn't find any relevant information on the web on that.'"""

    for i in range(len(results)):
        results.loc[i, "body"] = extract_main_content(results.loc[i, "url"]).replace(
            "\n", ""
        )

        if results.loc[i, "body"] != "":
            # metadata
            final_text += f"\n\nURL: {results.loc[i, 'url']}"

            # story
            final_text += f"\n\nmain article: {results.loc[i, 'body']}"

    return final_text

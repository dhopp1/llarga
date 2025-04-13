from duckduckgo_search import DDGS
import requests
from readability import Document
from lxml import html
import pandas as pd


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

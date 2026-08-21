import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


MAX_RESULTS = 5
MAX_PAGE_CHARS = 3000
REQUEST_TIMEOUT = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


class WebTools:

    def search_web(self, query: str) -> str:

        try:

            with DDGS() as ddgs:

                results = list(
                    ddgs.text(
                        query,
                        max_results=MAX_RESULTS
                    )
                )

        except Exception as error:
            return f"Web search failed: {error}"

        if not results:
            return f"No results found for '{query}'."

        lines = []

        for index, result in enumerate(results, start=1):

            title = result.get("title", "Untitled")
            body = result.get("body", "").strip()
            url = result.get("href", "")

            lines.append(
                f"{index}. {title} — {body} ({url})"
            )

        return "\n".join(lines)

    def read_webpage(self, url: str) -> str:

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

        except Exception as error:
            return f"Couldn't fetch {url}: {error}"

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = " ".join(soup.get_text(separator=" ").split())

        if not text:
            return f"Fetched {url} but found no readable text."

        if len(text) > MAX_PAGE_CHARS:
            text = text[:MAX_PAGE_CHARS] + "..."

        return text
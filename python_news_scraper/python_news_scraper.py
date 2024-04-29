import datetime
import requests
from bs4 import BeautifulSoup
from .buildQueryString import buildQueryString
from .getArticleContent import getArticleContent
from .getPrettyUrl import get_pretty_url
import asyncio

def scrapeImage(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all <img> tags in the document
    images = soup.find_all('img')
    
    # Filter images by minimum width (assuming width can be parsed directly from attributes or styles)
    min_width = 400
    main_image_url = None
    max_width = 0  # Track the largest image above the minimum width requirement

    for img in images:
        width = extract_width(img)

        # Only consider images that meet the minimum width requirement
        if width >= min_width and width > max_width:
            main_image_url = img.get('src')
            max_width = width
        if not main_image_url:
            main_image_url = "https://placehold.co/700x400"

    return main_image_url

def extract_width(img):
    """Extract width from an image tag using either the 'width' attribute or 'style'."""
    if 'width' in img.attrs:
        try:
            # Directly return the width if specified in attributes
            return int(img['width'])
        except ValueError:
            pass
    
    if 'style' in img.attrs:
        # Extract width from the 'style' attribute
        styles = img['style'].split(';')
        for style in styles:
            if 'width' in style:
                width_str = style.split(':')[1].strip()
                if 'px' in width_str:
                    try:
                        return int(width_str.replace('px', ''))
                    except ValueError:
                        pass

    return 0  # Default width if none is found or if parsing fails


def googleNewsScraper(userConfig):
    config = {
        "prettyURLs": True,
        "getArticleContent": False,
        "timeframe": "7d",
        "puppeteerArgs": [],
    }
    config.update(userConfig)

    queryString = buildQueryString(config["queryVars"]) if config["queryVars"] else ""
    url = f"https://news.google.com/search?{queryString}&q={config['searchTerm']} when:{config.get('timeframe', '7d')}"
    print(f"SCRAPING NEWS FROM: {url}")

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/"
    }
    cookies = {
        "CONSENT": f"YES+cb.{datetime.datetime.now().isoformat().split('T')[0].replace('-', '')}-04-p0.en-GB+FX+667"
    }
    response = requests.get(url, headers=headers, cookies=cookies)
    content = response.content

    soup = BeautifulSoup(content, 'html.parser')
    articles = soup.find_all('article')
    results = []
    urlChecklist = []

    for article in articles:
        link_element = article.find('a', href=lambda href: href and href.startswith('./article'))
        link = link_element.get('href').replace('./', 'https://news.google.com/') if link_element else None
        if link:
            urlChecklist.append(link)
        figure_element = article.find('figure')
        srcset = figure_element.find('img').get('srcset').split(' ') if figure_element and figure_element.find('img') else []
        image = srcset[-2] if srcset else figure_element.find('img').get('src') if figure_element and figure_element.find('img') else None
        if image and image.startswith('/'):
            image = f"https://news.google.com{image}"
        title_element = article.find_all('div', {"class": 'm5k28'})[0].find_all('div', {"class": 'B6pJDd'})[0].find_all('div')[0].find_all('a')
        title = title_element[0].text
        source_element = article.find('div', {'data-n-tid': True})
        source = source_element.text if source_element else None
        datetime_element = article.find_all('div:last-child time')
        datetime_str = datetime_element.get('datetime') if datetime_element else None
        datetime_val = datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ") if datetime_str else None
        time = datetime_element.text if datetime_element else None
        mainArticle = {
            "title": title,
            "link": link,
            "image": image,
            "source": source,
            "datetime": datetime_val,
            "time": time
        }
        results.append(mainArticle)

    if config["prettyURLs"]:
        for result in results:
            new_link = get_pretty_url(result["link"])
            result["link"] = new_link

    if config["getArticleContent"]:
        filterWords = config.get("filterWords", [])
        results = asyncio.run(getArticleContent(results, filterWords))
    
    return results
from typing import List
from json import loads
from bs4 import BeautifulSoup as bs

def get_pages(html: str) -> List[str]:
    soup = bs(html, "html.parser")
    
    region = soup.find("html").get("lang")

    _main = soup.find("div", {"id": "__next"}).find("main")
    section = _main.find("section", {"class": "ems-sdk-grid"})
    psw = section.find("div", {"class": "psw-l-stack-center"})
    
    count = int(psw.find("nav").find("ol").find_all("li")[-1].find("span").text)
    
    return [f"https://store.playstation.com/{region}/pages/browse/{i}" for i in range(1, count+1)]

def get_name(html: str) -> List[str]:

    soup = bs(html, "html.parser")
    
    main = soup.find("div", {"id": "__next"}).find("main")
    section = main.find("section", {"class": "ems-sdk-grid"})
    ul = section.find("ul", {"class": "psw-grid-list psw-l-grid"})
    products = ul.find_all("li")
    
    return [loads(product.find("a")["data-telemetry-meta"])["name"] for product in products]

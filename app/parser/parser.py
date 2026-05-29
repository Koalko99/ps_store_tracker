from typing import List, Tuple, Dict, Any
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


def get_names(html: str) -> List[str]:

    soup = bs(html, "html.parser")
    
    main = soup.find("div", {"id": "__next"}).find("main")
    section = main.find("section", {"class": "ems-sdk-grid"})
    ul = section.find("ul", {"class": "psw-grid-list psw-l-grid"})
    products = ul.find_all("li")
    
    return [loads(product.find("a")["data-telemetry-meta"])["name"] for product in products]


def ps_plus_extract(flag: str, text: str) -> Tuple[str, List[Any]]:
    json = loads(text)
    games = sum([i["games"] for i in json], [])
    return flag, games


def ps_plus_combine(region: str, json: List) -> Dict[str, Dict[str, List[Tuple[str]]]]:

    result = {
        region: {
            "essential": [],
            "extra": [],
            "premium": []
        }
    }

    for resp in json:
        flag, json = resp
        games = [(j["name"], j["productId"])  for j in json]
        if flag == "plus-monthly-games-list":
            result["essential"].extend(games)
            result["extra"].extend(games)
            result["premium"].extend(games)
        elif flag == "plus-games-list":
            result["extra"].extend(games)
            result["premium"].extend(games)
        elif flag == "ubisoft-classics-list":
            result["extra"].extend(games)
            result["premium"].extend(games)
        elif flag == "plus-classics-list":
            result["premium"].extend(games)

    return result

def extract_products(html: str):
    soup = bs(html, "html.parser")
    
    main = soup.find("div", {"id": "__next"}).find("main")
    section = main.find("section", {"class": "ems-sdk-grid"})
    ul = section.find("ul", {"class": "psw-grid-list psw-l-grid"})
    products = ul.find_all("li")

    return products


def concept_to_product(url: str, json: Dict):
    
    result = []
    products = json["data"]["conceptRetrieve"]["products"]
    
    for product in products:
        ID = product["id"]
        result.append(f'{"/".join(url.split("/")[:4])}/product/{ID}')
    
    return result

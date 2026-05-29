import json

import pytest

from app.core.errors import ParserError
from app.parser.parser import (
    concept_to_product,
    extract_concepts,
    get_names,
    get_pages,
    ps_plus_combine,
    ps_plus_extract,
)


def browse_html(region: str = "ru-ua") -> str:
    return f"""
    <html lang="{region}">
      <body>
        <div id="__next">
          <main>
            <section class="ems-sdk-grid">
              <ul class="psw-grid-list psw-l-grid">
                <li>
                  <a href="/{region}/concept/100"
                     data-telemetry-meta='{{"name": "Game One"}}'>Game</a>
                </li>
              </ul>
              <nav><ol><li><span>1</span></li><li><span>3</span></li></ol></nav>
            </section>
          </main>
        </div>
      </body>
    </html>
    """


def test_get_pages():
    assert get_pages(browse_html()) == [
        "https://store.playstation.com/ru-ua/pages/browse/1",
        "https://store.playstation.com/ru-ua/pages/browse/2",
        "https://store.playstation.com/ru-ua/pages/browse/3",
    ]


def test_extract_concepts():
    assert extract_concepts(browse_html()) == ["https://store.playstation.com/ru-ua/concept/100"]


def test_get_names():
    assert get_names(browse_html()) == ["Game One"]


def test_get_pages_raises_for_missing_pagination():
    with pytest.raises(ParserError):
        get_pages("<html lang='ru-ua'></html>")


def test_concept_to_product():
    payload = {"data": {"conceptRetrieve": {"products": [{"id": "PPSA00001"}]}}}

    assert concept_to_product("ru-ua", payload) == [
        "https://store.playstation.com/ru-ua/product/PPSA00001",
    ]


def test_ps_plus_extract_and_combine():
    raw = json.dumps([{"games": [{"name": "Game", "productId": "PPSA00001"}]}])
    extracted = [ps_plus_extract("plus-monthly-games-list", raw)]

    catalog = ps_plus_combine("ru-ua", extracted)

    assert catalog.essential[0].name == "Game"
    assert catalog.extra[0].product_id == "PPSA00001"
    assert catalog.premium[0].product_id == "PPSA00001"

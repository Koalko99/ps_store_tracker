import json

from app.parser.models.product import ProductPageDetails
from app.parser.products import (
    extract_price,
    parse_product_page,
    parse_products,
    product_ids_to_load,
)


def product_page_html(product_id: str = "PPSA00001") -> str:
    rating = (
        "<div>"
        + json.dumps(
            {"cache": {f"Product:{product_id}": {"starRating": {"averageRating": 4.7}}}},
        )
        + "</div>"
    )
    background = (
        "<div>"
        + json.dumps(
            {
                "cache": {
                    f"Product:{product_id}": {
                        "media": [{"role": "MASTER", "url": "image.jpg"}],
                    },
                },
            },
        )
        + "</div>"
    )
    next_data = json.dumps(
        {
            "props": {
                "pageProps": {
                    "batarangs": {
                        "overview": {"text": "<p>Description</p>"},
                        "compatibility-notices": {"text": "<p>Title</p><p>Notice</p>"},
                        "star-rating": {"text": rating},
                        "background-image": {"text": background},
                    },
                },
            },
        },
    )
    return f"""
    <html>
      <body>
        <main>
          <div class="pdp-main psw-dark-theme">
            <div data-qa="gameInfo">
              <dl>
                <dd data-qa="gameInfo#releaseInformation#platform-value">PS4, PS5</dd>
                <dd data-qa="gameInfo#releaseInformation#publisher-value">Publisher</dd>
                <dd data-qa="gameInfo#releaseInformation#voice-value">Russian, English</dd>
                <dd data-qa="gameInfo#releaseInformation#subtitles-value">English</dd>
              </dl>
            </div>
          </div>
        </main>
        <script id="__NEXT_DATA__" type="application/json">{next_data}</script>
      </body>
    </html>
    """


def product_payload():
    return {
        "data": {
            "productRetrieve": {
                "topCategory": "GAME",
                "concept": {
                    "name": "Main Game",
                    "products": [
                        {
                            "id": "PPSA00001",
                            "name": "Main Game Deluxe",
                            "invariantName": "Main Game Deluxe",
                            "topCategory": "GAME",
                            "localizedGenres": [{"value": "Action"}],
                            "skus": [{"name": "Full Game"}],
                            "edition": {"name": "Deluxe", "features": ["Bonus"]},
                            "media": [{"role": "MASTER", "url": "master.jpg"}],
                            "webctas": [
                                {
                                    "type": "ADD_TO_CART",
                                    "price": {
                                        "discountedPrice": "$10",
                                        "discountedValue": 1000,
                                        "basePrice": "$20",
                                        "basePriceValue": 2000,
                                        "discountText": "-50%",
                                        "endTime": None,
                                    },
                                },
                            ],
                        },
                    ],
                },
            },
        },
    }


def test_parse_product_page():
    details = parse_product_page("PPSA00001", product_page_html())

    assert details.platforms == ["PS4", "PS5"]
    assert details.publisher == "Publisher"
    assert details.description == "Description"
    assert details.rating == 4.7
    assert details.master_image == "image.jpg"


def test_product_ids_to_load_for_concept_products():
    ids = product_ids_to_load(product_payload(), {"data": {"productRetrieve": {"id": "ignored"}}})

    assert ids == ["PPSA00001"]


def test_extract_price():
    webctas = product_payload()["data"]["productRetrieve"]["concept"]["products"][0]["webctas"]

    price = extract_price(webctas)

    assert price.price == 10
    assert price.old_price == 20
    assert price.discount == "-50%"


def test_parse_products():
    details = {
        "PPSA00001": ProductPageDetails(
            product_id="PPSA00001",
            platforms=["PS5"],
            publisher="Publisher",
            voice_languages="Russian",
            subtitles="English",
            description="Description",
            rating=4.7,
            master_image="image.jpg",
        ),
    }

    products = parse_products(
        "https://store.playstation.com/ru-ua/product/PPSA00001",
        product_payload(),
        product_payload(),
        details,
    )

    assert len(products) == 1
    assert products[0].id == "PPSA00001"
    assert products[0].product_type == "Игра"
    assert products[0].price == 10
    assert products[0].localization == 2

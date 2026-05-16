import os
import json
import app.core.logging as logging

class Config:

    def __init__(self, config_path: str = ""):

        self.logger = logging.get_logger(__name__)

        if not config_path or not os.path.exists(self.CONFIG_FILE):
            self.logger.warning("Cannot load data from config file")
            self.set_defaults()
        else:
            try:
                with open(config_path, "r") as file:
                    config = json.loads(file.read())
                
                self.REGIONS = []

                self.MAX_RETRIES = config.get('max_retries', 3)
                self.REQUEST_TIMEOUT = config.get('request_timeout', 120)
                self.BATCH_SIZE_PAGES = config.get('batch_size_pages', 30)
                self.BATCH_SIZE_PRODUCTS = config.get('batch_size_products', 70)
                self.BATCH_SIZE_UNQUOTE = config.get('batch_size_unquote', 250)
                self.SLEEP_BETWEEN_BATCHES = config.get('sleep_between_batches', 3)
                self.SLEEP_ON_CLOUDFLARE = config.get('sleep_on_cloudflare', 30)
                self.ACCESS_DENIED_CHECK_INTERVAL = config.get('access_denied_check_interval', 60)

                for region in config.get("regions", []):
                    
                    code = None
                    divide_price_by_100 = None
                    
                    if "code" in region:
                        tmp = region.get("code")
                        if len(tmp) == 5:
                            if tmp[2] == '-':
                                code = tmp
                    
                    if "divide_price_by_100" in region:
                        tmp = region.get("divide_price_by_100")
                        if isinstance(tmp, bool):
                            divide_price_by_100 = tmp
                    
                    if code is not None and divide_price_by_100 is not None:
                        self.REGIONS.append(
                            {
                                "code": code,
                                "divide_price_by_100": divide_price_by_100
                            }
                        )

            except Exception:
                self.logger.exception("Config error")
                self.set_defaults()
            

    def set_defaults(self):
        
        self.logger.info("Set default config")

        self.MAX_RETRIES = 3
        self.REQUEST_TIMEOUT = 120
        self.BATCH_SIZE_PAGES = 30
        self.BATCH_SIZE_PRODUCTS = 70
        self.BATCH_SIZE_UNQUOTE = 250
        self.SLEEP_BETWEEN_BATCHES = 3
        self.SLEEP_ON_CLOUDFLARE = 30
        self.ACCESS_DENIED_CHECK_INTERVAL = 60

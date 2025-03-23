import scrapy
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse
import os
import json
from datetime import datetime

class AirbnbSpider(scrapy.Spider):
    name = "airbnb"
    allowed_domains = ["airbnb.com"]

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'output_%(time)s.csv',  # Eindeutiger Dateiname mit Zeitstempel
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, *args, **kwargs):
        super(AirbnbSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Erstelle einen Debug-Ordner
        self.debug_dir = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # Zähler für jede URL
        self.per_url_counter = {}
        self.urls_to_scrape = [
            "https://www.airbnb.com/s/St-Gallen--Switzerland/homes?checkin=2025-06-26&checkout=2025-06-29",
            "https://www.airbnb.com/s/St-Gallen--Switzerland/homes?checkin=2025-10-09&checkout=2025-10-19"
        ]

    def start_requests(self):
        # Starte mit der ersten URL, der Rest wird später verarbeitet
        yield scrapy.Request(self.urls_to_scrape[0], self.parse)

    def parse(self, response):
        # Extrahiere den Zeitraum aus der URL
        parsed_url = urllib.parse.urlparse(response.url)
        query = urllib.parse.parse_qs(parsed_url.query)
        checkin = query.get("checkin", [""])[0]
        checkout = query.get("checkout", [""])[0]
        time_period = f"{checkin} bis {checkout}"
        
        # Initialisiere Zähler für diese URL
        if response.url not in self.per_url_counter:
            self.per_url_counter[response.url] = 0

        # Lade die Seite
        self.logger.info(f"Starte Scraping für {response.url}")
        self.driver.get(response.url)
        
        # Cookie-Banner akzeptieren
        self.handle_cookie_banner()
        
        # Debug: Speichere die erste Seite
        initial_page_file = os.path.join(self.debug_dir, f"initial_page_{checkin}.html")
        with open(initial_page_file, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        
        # Warte auf das Laden der Listings
        self.wait_for_listings()
        
        # Scrolle zur Mitte der Seite, um sicherzustellen, dass alles geladen ist
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(2)
        
        current_page = 1
        max_pages = 10  # Sicherheitsgrenze
        
        # Schleife durch die Seiten, bis genug Listings gefunden wurden
        while self.per_url_counter[response.url] < 100 and current_page <= max_pages:
            self.logger.info(f"Verarbeite Seite {current_page} für Zeitraum {time_period}")
            
            # Warte und hole den Seitenquelltext
            time.sleep(3)
            page_source = self.driver.page_source
            sel = Selector(text=page_source)
            
            # Debug: Speichere den Quelltext der aktuellen Seite
            page_file = os.path.join(self.debug_dir, f"page_{checkin}_{current_page}.html")
            with open(page_file, "w", encoding="utf-8") as f:
                f.write(page_source)
            
            # Finde Listings mit verschiedenen Selektoren
            listing_containers = self.find_listings(sel)
            
            if not listing_containers:
                self.logger.error(f"Keine Listings auf Seite {current_page} gefunden!")
                break
            
            self.logger.info(f"Gefunden: {len(listing_containers)} Listings auf Seite {current_page}")
            
            # Verarbeite die Listings
            for i, listing in enumerate(listing_containers):
                if self.per_url_counter[response.url] >= 100:
                    break
                
                # Debug: Speichere das erste Listing jeder Seite
                if i == 0:
                    listing_html = listing.get()
                    listing_file = os.path.join(self.debug_dir, f"listing_{checkin}_{current_page}.html")
                    with open(listing_file, "w", encoding="utf-8") as f:
                        f.write(listing_html)
                
                # Extrahiere Daten
                name = self.extract_name(listing)
                price = self.extract_price(listing)
                listing_url = self.extract_listing_url(listing)
                
                self.logger.info(f"Extrahiert #{self.per_url_counter[response.url]+1}: Name: {name}, Preis: {price}")
                
                yield {
                    "time_period": time_period,
                    "name": name if name else "Kein Name gefunden",
                    "price_per_night": price if price else "Kein Preis gefunden",
                    "url": listing_url if listing_url else "Keine URL gefunden"
                }
                
                self.per_url_counter[response.url] += 1
            
            # Falls noch mehr Listings benötigt werden, gehe zur nächsten Seite
            if self.per_url_counter[response.url] < 100:
                if self.go_to_next_page(current_page):
                    current_page += 1
                else:
                    self.logger.info(f"Keine weitere Seite verfügbar für {time_period}")
                    break
            else:
                self.logger.info(f"Ziel von 100 Listings für {time_period} erreicht!")
                break
        
        # Überprüfe, ob alle URLs verarbeitet wurden
        current_url_index = self.urls_to_scrape.index(response.url)
        if current_url_index < len(self.urls_to_scrape) - 1:
            next_url = self.urls_to_scrape[current_url_index + 1]
            self.logger.info(f"Wechsle zur nächsten URL: {next_url}")
            yield scrapy.Request(next_url, self.parse)
        else:
            self.logger.info("Alle URLs wurden verarbeitet")
    
    def handle_cookie_banner(self):
        """Versucht, Cookie-Banner zu akzeptieren"""
        try:
            time.sleep(3)
            cookie_selectors = [
                "//button[contains(text(),'Akzept')]",
                "//button[contains(text(),'Accept')]", 
                "//button[contains(text(),'Cookie')]",
                "//button[contains(text(),'Zustimm')]",
                "//button[contains(@data-testid, 'accept')]"
            ]
            for selector in cookie_selectors:
                try:
                    cookie_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    cookie_button.click()
                    self.logger.info(f"Cookie-Banner akzeptiert mit: {selector}")
                    time.sleep(2)
                    return
                except:
                    continue
        except Exception as e:
            self.logger.info(f"Kein Cookie-Banner gefunden oder Fehler: {e}")
    
    def wait_for_listings(self):
        """Wartet auf das Laden der Listings"""
        listing_selectors = [
            "//div[contains(@data-testid, 'card-container')]",
            "//div[contains(@data-testid, 'listing-card')]",
            "//div[contains(@id, 'listing-')]",
            "//div[contains(@class, 'listing-card')]",
            "//div[@data-component='ExploreLayoutItem']"
        ]
        
        for selector in listing_selectors:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                self.logger.info(f"Listings gefunden mit Selector: {selector}")
                return
            except:
                continue
        
        self.logger.warning("Timeout beim Warten auf Listings mit allen Selektoren")
    
    def find_listings(self, selector):
        """Findet Listings mit verschiedenen Selektoren"""
        listing_selectors = [
            "//div[contains(@data-testid, 'card-container')]",
            "//div[contains(@data-testid, 'listing-card')]",
            "//div[contains(@id, 'listing-')]",
            "//div[contains(@class, 'listing-card')]",
            "//div[@data-component='ExploreLayoutItem']",
            "//div[contains(@style, 'position: relative') and .//a[contains(@href, '/rooms/')]]",
            "//div[contains(@itemtype, 'lodging') or contains(@itemtype, 'Product')]"
        ]
        
        for xpath in listing_selectors:
            listings = selector.xpath(xpath)
            if listings:
                self.logger.info(f"Listings gefunden mit Selector: {xpath}, Anzahl: {len(listings)}")
                return listings
        return []
    
    def extract_name(self, listing):
        """Extrahiert den Namen eines Listings"""
        name_selectors = [
            ".//div[contains(@data-testid, 'title')]/text()",
            ".//div[contains(@data-testid, 'listing-card-title')]/text()",
            ".//h3/text()",
            ".//div[contains(@class, 'title')]/text()",
            ".//a[contains(@href, '/rooms/')]/@aria-label",
            ".//a[contains(@href, '/rooms/')]//span/text()",
            ".//div[contains(@style, 'overflow: hidden')]/text()"
        ]
        
        for selector in name_selectors:
            name = listing.xpath(selector).get()
            if name:
                return name.strip()
        return None
    
    def extract_price(self, listing):
        """Extrahiert den Preis eines Listings"""
        price_selectors = [
            ".//span[contains(@data-testid, 'price')]/text()",
            ".//div[contains(@data-testid, 'price')]/span/text()",
            ".//span[contains(text(), '€')]/text()",
            ".//span[contains(text(), 'CHF')]/text()",
            ".//div[contains(@style, 'font-weight: 600')]//span/text()",
            ".//span[contains(@class, 'price')]/text()"
        ]
        
        for selector in price_selectors:
            price = listing.xpath(selector).get()
            if price:
                return price.strip()
        return None
    
    def extract_listing_url(self, listing):
        """Extrahiert die URL eines Listings"""
        url = listing.xpath(".//a[contains(@href, '/rooms/')]/@href").get()
        if url:
            if url.startswith('/'):
                return f"https://www.airbnb.com{url}"
            return url
        return None
    
    def go_to_next_page(self, current_page):
        """Navigiert zur nächsten Seite"""
        next_page = current_page + 1
        
        # Verschiedene Methoden, um zur nächsten Seite zu gelangen
        next_page_selectors = [
            f"//a[contains(@aria-label, 'Page {next_page}')]",
            f"//a[text()='{next_page}']",
            "//a[contains(@aria-label, 'Next')]",
            "//button[contains(@aria-label, 'Next')]",
            "//span[contains(@aria-label, 'Next')]",
            "//a[contains(text(), 'Nächste')]",
            "//button[contains(@aria-label, 'nächste')]",
            "//button[contains(@data-testid, 'next')]"
        ]
        
        for selector in next_page_selectors:
            try:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.logger.info(f"Nächste Seite Button gefunden mit: {selector}")
                next_button.click()
                time.sleep(5)
                return True
            except:
                continue
        
        # Alternative Methode: Direkt zur nächsten Seite-URL gehen
        try:
            current_url = self.driver.current_url
            if "page=" in current_url:
                # URL enthält bereits page Parameter
                new_url = current_url.replace(f"page={current_page}", f"page={next_page}")
            else:
                # URL hat noch keinen page Parameter
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}page={next_page}"
            
            self.logger.info(f"Versuche direkte URL-Navigation zur Seite {next_page}: {new_url}")
            self.driver.get(new_url)
            time.sleep(5)
            return True
        except Exception as e:
            self.logger.error(f"Fehler bei URL-Navigation: {e}")
            return False

    def closed(self, reason):
        self.driver.quit()
        
        # Zusammenfassung ausgeben
        self.logger.info("=== Scraping-Zusammenfassung ===")
        for url, count in self.per_url_counter.items():
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            checkin = query.get("checkin", [""])[0]
            checkout = query.get("checkout", [""])[0]
            self.logger.info(f"Zeitraum {checkin} bis {checkout}: {count} Listings")
        
        self.logger.info(f"Spider geschlossen. Grund: {reason}")
import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import os
import re
from datetime import datetime

class AirbnbFinal2Spider(scrapy.Spider):
    name = "airbnb_final2"
    allowed_domains = ["www.airbnb.com"]
    base_url = "https://www.airbnb.com/s/St.-Gallen--Schweiz/homes"
    search_configs = [
        {
            'checkin': '2025-10-09',
            'checkout': '2025-10-19',
            'target_results': 100,
            'current_results': 0
        }
    ]
    current_config_index = 0
    
    # Muster für Texte, die keine echten Apartment-Namen sind
    GENERIC_NAME_PATTERNS = [
        r'^Apartment in\s',
        r'^Wohnung in\s',
        r'^Zimmer in\s',
        r'^Room in\s',
        r'^Entire\s',
        r'^Studio in\s',
        r'^Privatzimmer in\s',
        r'^Private room in\s',
        r'^Ganze Wohnung in\s',
        r'^Ganze Unterkunft in\s',
        r'^Gesamte Unterkunft in\s',
    ]
    
    # Muster für Texte, die keine Preise sind
    NON_PRICE_PATTERNS = [
        r'Superhost',
        r'Superhostin',
        r'Plus',
        r'Luxury',
        r'Rarität',
        r'Beliebt',
        r'Popular',
        r'New',
        r'Neu',
    ]

    def __init__(self):
        super().__init__()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.html_dir = 'saved_html'
        if not os.path.exists(self.html_dir):
            os.makedirs(self.html_dir)
            
        # Spezieller Ordner für Problem-HTML
        self.problem_html_dir = 'problem_html'
        if not os.path.exists(self.problem_html_dir):
            os.makedirs(self.problem_html_dir)

    def save_html(self, html_content, page_num):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.html_dir}/airbnb_page_{page_num}_{timestamp}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info(f'Saved HTML content to {filename}')
        
    def save_problem_html(self, html_content, issue_type):
        """Speichert HTML von problematischen Elementen zur späteren Analyse"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.problem_html_dir}/{issue_type}_{timestamp}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info(f'Saved problematic HTML to {filename}')

    def is_generic_name(self, name_text):
        """Überprüft, ob der gefundene Name ein generischer Apartment-Typ ist"""
        if not name_text:
            return True
        
        # Entferne Leerzeichen am Anfang und Ende
        name_text = name_text.strip()
        
        # Wenn der Text zu kurz ist, wahrscheinlich kein Name
        if len(name_text) < 10:
            return True
            
        # Prüfen auf typische Wohnungstyp-Beschreibungen
        for pattern in self.GENERIC_NAME_PATTERNS:
            if re.match(pattern, name_text):
                return True
                
        return False

    def extract_price(self, price_text):
        """Verbesserte Preisextraktion"""
        if not price_text:
            return None
            
        # Prüfen auf Nicht-Preis-Texte
        for pattern in self.NON_PRICE_PATTERNS:
            if re.search(pattern, price_text):
                return None
                
        # Wenn der Text "Nacht" oder "night" enthält, ist es wahrscheinlicher ein echter Preis
        is_likely_price = any(term in price_text.lower() for term in ["nacht", "night", "pro", "total", "gesamt"])
        
        # Regulärer Ausdruck für CHF-Preisformate mit Nummer + Währung
        price_match = re.search(r'(?:CHF\s*)?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:CHF)?', price_text)
        
        if price_match:
            # Extrahiere den Preis und bereinige ihn
            price_str = price_match.group(1).replace(',', '.').strip()
            
            # Stelle sicher, dass nur ein Dezimalpunkt vorhanden ist
            if price_str.count('.') > 1:
                # Ersetze alle bis auf den letzten Dezimalpunkt
                parts = price_str.split('.')
                price_str = ''.join(parts[:-1]) + '.' + parts[-1]
            
            # Zusätzliche Überprüfung - Konvertiere zu Float, um zu verifizieren, dass es eine gültige Zahl ist
            try:
                float_price = float(price_str)
                if float_price <= 0:
                    return None
                
                # Wenn es kein wahrscheinlicher Preis ist und kleiner als 30, wahrscheinlich kein Übernachtungspreis
                if not is_likely_price and float_price < 30:
                    return None
                    
                return f"{price_str} CHF"
            except:
                return None
                
        return None

    def start_requests(self):
        config = self.search_configs[self.current_config_index]
        start_url = f"{self.base_url}?checkin={config['checkin']}&checkout={config['checkout']}&page=1&items_per_page=20"
        yield scrapy.Request(start_url, self.parse, dont_filter=True)

    def parse(self, response):
        self.driver.get(response.url)
        
        # Dynamisches Warten auf Inhalte
        wait = WebDriverWait(self.driver, 15)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
                "div[itemprop='itemListElement'], div[data-testid='card-container'], div[data-testid='listing-card']")))
        except Exception as e:
            self.logger.warning(f"Timeout beim Warten auf Listing-Karten: {str(e)}")
            current_url = self.driver.current_url
            page_num = current_url.split('page=')[-1].split('&')[0] if 'page=' in current_url else '1'
            self.save_html(self.driver.page_source, page_num)
        
        # Verbesserte Scroll-Logik
        viewport_height = self.driver.execute_script("return window.innerHeight")
        page_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # Progressive Scrolling in 25% Schritten
        scroll_positions = [int(page_height * p) for p in [0.25, 0.5, 0.75, 1.0]]
        for position in scroll_positions:
            self.driver.execute_script(f"window.scrollTo(0, {position});")
            time.sleep(2)  # Längere Pause für dynamisches Laden
            
        # Zurück nach oben und erneute progressive Scrolls (manchmal hilft wiederholtes Scrolling)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        for position in scroll_positions:
            self.driver.execute_script(f"window.scrollTo(0, {position});")
            time.sleep(1)
            
        # Nach dem Scrollen, warte auf mögliche Nachladeeffekte
        time.sleep(3)
        
        current_url = self.driver.current_url
        page_num = current_url.split('page=')[-1].split('&')[0] if 'page=' in current_url else '1'
        self.save_html(self.driver.page_source, page_num)
        
        # Verbesserte Listing-Karten-Selektoren
        listing_cards = []
        card_selectors = [
            "div[itemprop='itemListElement']",  # Schema.org Markup für Listenelemente
            "div[data-testid='card-container']", 
            "div.c4mnd7m",  # Airbnb-Klasse für Karten
            "div[data-testid='listing-card']",
            "div.cy5jw6o",   # Alternative Kartenklasse
            "div.gsgwcjk.g1qv1ctd",  # Neuere Kartenklasse (2024)
            "div.c1l1h97y:not(.dir)",  # Weitere potenzielle Kartenklasse
        ]
        
        for selector in card_selectors:
            cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                listing_cards = cards
                self.logger.info(f"Gefunden: {len(cards)} Listing-Karten mit Selektor: {selector}")
                break
        
        if not listing_cards:
            self.logger.error("Keine Listing-Karten mit irgendeinem Selektor gefunden!")
            
        success_count = 0  # Zähle erfolgreiche Extraktionen für Feedback
        for idx, card in enumerate(listing_cards):
            try:
                # Debug-HTML für die Karte
                try:
                    card_html = card.get_attribute('outerHTML')
                    card_debug_str = card_html[:500] + "..." if len(card_html) > 500 else card_html
                    self.logger.debug(f"Verarbeite Karte {idx+1}: {card_debug_str}")
                except:
                    self.logger.debug(f"Konnte kein HTML für Karte {idx+1} bekommen")
                
                # VERBESSERTE NAME-EXTRAKTION MIT DEINEM XPATH
                name = None
                name_selectors = [
                    # Füge die neuen XPath-basierten Selektoren hinzu
                    "div.t1jojoys span",  # Basierend auf deinem XPath
                    "div[data-testid='listing-card-title'] span",
                    "span[data-testid='listing-card-name']",
                    # Behalte die bestehenden Selektoren bei
                    "h3.t1jojoys",
                    "div.t1jojoys",
                    "h3.i4phm33",
                    "h2[class*='title']",
                    "div.t1jojoys h3",
                    "div[data-testid='listing-card-title']", 
                    "span[data-testid='listing-card-name']",
                    "div[itemprop='name']",
                    "meta[itemprop='name']",
                    "div.dir.dir-ltr h3",
                    "div._qrfr9x9 h3",
                ]
                
                # Versuche zuerst den spezifischen XPath-Ausdruck
                try:
                    xpath_result = card.find_elements(By.XPATH, 
                        ".//div[contains(@class, 't1jojoys')]/span | .//div[contains(@class, 'i4phm33')]/span")
                    if xpath_result:
                        for element in xpath_result:
                            text = element.text
                            if text and len(text) > 3 and not self.is_generic_name(text):
                                name = text
                                self.logger.debug(f"Name gefunden mit XPath: {name}")
                                break
                except Exception as e:
                    self.logger.debug(f"XPath-Name-Extraktion fehlgeschlagen: {str(e)}")
                
                # Falls kein Name gefunden wurde, versuche die regulären Selektoren
                if not name:
                    for selector in name_selectors:
                        try:
                            elements = card.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                for element in elements:
                                    text = element.text or element.get_attribute("content")
                                    if text and len(text) > 3 and not self.is_generic_name(text):
                                        name = text
                                        self.logger.debug(f"Name gefunden mit Selektor {selector}: {name}")
                                        break
                            if name:
                                break
                        except Exception as e:
                            continue
                
                # Wenn kein Name gefunden wurde, versuche eine andere Strategie mit JavaScript
                if not name:
                    try:
                        # Verwende JS, um den H3-Titel zu finden
                        js_result = self.driver.execute_script("""
                            var card = arguments[0];
                            var titles = card.querySelectorAll('h3');
                            for (var i = 0; i < titles.length; i++) {
                                var text = titles[i].textContent.trim();
                                if (text.length > 10) {
                                    return text;
                                }
                            }
                            return null;
                        """, card)
                        
                        if js_result and not self.is_generic_name(js_result):
                            name = js_result
                            self.logger.debug(f"Name mit JS gefunden: {name}")
                    except Exception as e:
                        self.logger.warning(f"Fehler bei JS-Name-Extraktion: {str(e)}")
                
                # VERBESSERTE PREIS-EXTRAKTION MIT DEINEM XPATH
                price = None
                price_selectors = [
                    # Füge präzisere Selektoren basierend auf deinem XPath hinzu
                    "div[data-testid='price-element'] span", 
                    "div.p1qe1cgb span",  # Klasse vom Preiselement
                    "div.a8jt5op span",   # Alternative Preisklasse
                    # Behalte die bestehenden Selektoren bei
                    "span._tyxjp1",
                    "span[data-testid='price-and-discounted-price']",
                    "span[data-testid='listing-card-price']",
                    "span[data-testid='card-price']",
                    "div._1jo4hgw span",
                    "span._14y1gc",
                    "span.a8jt5op",
                    "span[data-testid^='price']",
                    "div._i5duul span",
                ]
                
                # Versuche zuerst den spezifischen XPath-Ausdruck
                try:
                    xpath_result = card.find_elements(By.XPATH, 
                        ".//div[contains(@data-testid, 'price-element')]/span | .//div[contains(@class, 'p1qe1cgb')]/span | .//span[contains(@class, '_tyxjp1')]")
                    if xpath_result:
                        for element in xpath_result:
                            price_text = element.text
                            if price_text and "CHF" in price_text and any(c.isdigit() for c in price_text):
                                extracted_price = self.extract_price(price_text)
                                if extracted_price:
                                    price = extracted_price
                                    self.logger.debug(f"Preis gefunden mit XPath: {price}")
                                    break
                except Exception as e:
                    self.logger.debug(f"XPath-Preis-Extraktion fehlgeschlagen: {str(e)}")
                
                # Falls kein Preis gefunden wurde, versuche die regulären Selektoren
                if not price:
                    for selector in price_selectors:
                        try:
                            elements = card.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                for element in elements:
                                    price_text = element.text
                                    # Nur weitermachen, wenn der Text "CHF" und eine Ziffer enthält
                                    if price_text and "CHF" in price_text and any(c.isdigit() for c in price_text):
                                        extracted_price = self.extract_price(price_text)
                                        if extracted_price:
                                            price = extracted_price
                                            self.logger.debug(f"Preis gefunden mit Selektor {selector}: {price}")
                                            break
                            if price:
                                break
                        except Exception as e:
                            continue
                
                # Fallback-Strategie für Preise: Suche nach spezifischen Preismustern
                if not price:
                    try:
                        # Suche speziell nach Preismustern mit der Nacht-Referenz
                        price_patterns = [
                            ".//span[contains(text(), 'CHF') and contains(text(), 'Nacht')]",
                            ".//span[contains(text(), 'CHF') and contains(text(), 'night')]",
                            ".//span[contains(text(), 'CHF') and contains(text(), 'pro')]",
                            ".//div[contains(text(), 'CHF') and contains(text(), 'Nacht')]",
                        ]
                        
                        for xpath in price_patterns:
                            elements = card.find_elements(By.XPATH, xpath)
                            if elements:
                                for element in elements:
                                    price_text = element.text
                                    extracted_price = self.extract_price(price_text)
                                    if extracted_price:
                                        price = extracted_price
                                        self.logger.debug(f"Preis gefunden mit XPath-Muster: {price}")
                                        break
                            if price:
                                break
                    except Exception as e:
                        self.logger.warning(f"Fehler bei Preis-Fallback: {str(e)}")
                
                # Als letzten Ausweg versuche JavaScript für komplexere Auswahl
                if not price:
                    try:
                        js_price = self.driver.execute_script("""
                            var card = arguments[0];
                            var allSpans = card.querySelectorAll('span');
                            for (var i = 0; i < allSpans.length; i++) {
                                var text = allSpans[i].textContent;
                                if (text.includes('CHF') && text.match(/\\d+/)) {
                                    if (text.includes('Nacht') || text.includes('night') || 
                                        text.includes('pro') || text.includes('total')) {
                                        return text;
                                    }
                                }
                            }
                            return null;
                        """, card)
                        
                        if js_price:
                            extracted_price = self.extract_price(js_price)
                            if extracted_price:
                                price = extracted_price
                                self.logger.debug(f"Preis mit JS gefunden: {price}")
                    except Exception as e:
                        self.logger.warning(f"Fehler bei JS-Preis-Extraktion: {str(e)}")
                
                # Verbesserter XPath als absoluter letzter Versuch, wenn alle anderen Methoden versagen
                if not name or not price:
                    try:
                        # Verwende JavaScript, um die exact-XPath-Ausdrücke auszuführen
                        result = self.driver.execute_script("""
                            var card = arguments[0];
                            var document = card.ownerDocument;
                            
                            // Versuche den Namen mit XPath zu finden
                            var nameXPath = ".//div[contains(@class, 't1jojoys')]/span";
                            var nameResult = "";
                            try {
                                var nameElements = document.evaluate(nameXPath, card, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                for (var i = 0; i < nameElements.snapshotLength; i++) {
                                    var text = nameElements.snapshotItem(i).textContent.trim();
                                    if (text && text.length > 3) {
                                        nameResult = text;
                                        break;
                                    }
                                }
                            } catch(e) {}
                            
                            // Versuche den Preis mit XPath zu finden
                            var priceXPath = ".//span[contains(@class, '_tyxjp1') or contains(@class, 'a8jt5op')]";
                            var priceResult = "";
                            try {
                                var priceElements = document.evaluate(priceXPath, card, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                for (var i = 0; i < priceElements.snapshotLength; i++) {
                                    var text = priceElements.snapshotItem(i).textContent.trim();
                                    if (text && text.includes("CHF")) {
                                        priceResult = text;
                                        break;
                                    }
                                }
                            } catch(e) {}
                            
                            return {name: nameResult, price: priceResult};
                        """, card)
                        
                        if result and isinstance(result, dict):
                            if not name and result.get('name') and len(result['name']) > 3:
                                name = result['name']
                                self.logger.debug(f"Name mit exaktem XPath-JS gefunden: {name}")
                            
                            if not price and result.get('price') and "CHF" in result['price']:
                                extracted_price = self.extract_price(result['price'])
                                if extracted_price:
                                    price = extracted_price
                                    self.logger.debug(f"Preis mit exaktem XPath-JS gefunden: {price}")
                    except Exception as e:
                        self.logger.warning(f"Fehler bei exakter XPath-Extraktion: {str(e)}")
                
                # Logging für Debugging
                if not name:
                    self.logger.warning(f"Konnte keinen Namen für Listing {idx+1} extrahieren")
                    # Speichere das HTML für spätere Analyse
                    try:
                        self.save_problem_html(card.get_attribute('outerHTML'), "no_name_found")
                    except:
                        pass
                
                if not price:
                    self.logger.warning(f"Konnte keinen Preis für Listing {idx+1} extrahieren")
                    # Speichere das HTML für spätere Analyse
                    try:
                        self.save_problem_html(card.get_attribute('outerHTML'), "no_price_found")
                    except:
                        pass
                
                # Nur Ergebnisse liefern, wenn wir sowohl Namen als auch Preis haben
                if name and price and price.endswith('CHF'):
                    current_config = self.search_configs[self.current_config_index]
                    
                    # Only yield if we haven't reached target results for current period
                    if current_config['current_results'] < current_config['target_results']:
                        current_config['current_results'] += 1
                        success_count += 1  # Zähle erfolgreiche Extraktion
                        
                        result = {
                            'period_index': self.current_config_index + 1,  # 1 for June, 2 for October
                            'result_number': current_config['current_results'],
                            'apartment_name': name.strip(),
                            'price_per_night': price,
                            'checkin_date': current_config['checkin'],
                            'checkout_date': current_config['checkout'],
                            'scrape_date': datetime.now().strftime('%Y-%m-%d')
                        }
                        yield result
                        
                        # Wenn wir das Ziel erreicht haben, zur nächsten Konfiguration wechseln
                        if current_config['current_results'] >= current_config['target_results']:
                            self.logger.info(f"Zielanzahl von {current_config['target_results']} für Periode {self.current_config_index + 1} erreicht")
                            next_request = self.switch_to_next_config()
                            if next_request:
                                yield next_request
                            return  # Wichtig: Beende die aktuelle Verarbeitung
                        
            except Exception as e:
                self.logger.error(f"Fehler bei der Verarbeitung der Karte {idx+1}: {str(e)}")
                continue

        self.logger.info(f"Erfolgreich extrahiert: {success_count} von {len(listing_cards)} Karten auf Seite {page_num}")
        
        current_config = self.search_configs[self.current_config_index]
        # Prüfen, ob wir zur nächsten Seite wechseln oder zur nächsten Datumskonfiguration
        if current_config['current_results'] < current_config['target_results']:
            try:
                # Verbesserte Next-Button-Suche
                next_button = None
                next_button_selectors = [
                    "a[aria-label='Next']", 
                    "a[data-testid='pagination-next-btn']", 
                    "a.c1ytbx3a._1sikdxcl",
                    "a[aria-label='Weiter']",  # Für deutsche Seiten
                    "button[aria-label='Next']",
                    "button[aria-label='Weiter']",
                    "svg[aria-label='Next']",  # SVG-Icon könnte ebenfalls ein Target sein
                ]
                
                for selector in next_button_selectors:
                    next_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if next_buttons and next_buttons[0].is_displayed():
                        try:
                            # Prüfe, ob der Button aktiviert ist
                            if next_buttons[0].is_enabled() and not next_buttons[0].get_attribute("disabled"):
                                next_button = next_buttons[0]
                                break
                        except:
                            continue
                
                if next_button:
                    # Versuche direkt zu klicken statt href zu extrahieren
                    try:
                        next_url = next_button.get_attribute('href')
                        if next_url:
                            self.logger.info(f"Wechsle zur nächsten Seite: {next_url}")
                            yield scrapy.Request(next_url, self.parse, dont_filter=True)
                        else:
                            # Wenn kein href gefunden, versuche zu klicken und die neue URL zu bekommen
                            self.logger.info("Klicke auf Next-Button ohne URL")
                            next_button.click()
                            time.sleep(3)  # Warte auf Seitenwechsel
                            new_url = self.driver.current_url
                            yield scrapy.Request(new_url, self.parse, dont_filter=True)
                    except Exception as click_err:
                        self.logger.error(f"Fehler beim Klicken auf Next-Button: {str(click_err)}")
                        next_request = self.switch_to_next_config()
                        if next_request:
                            yield next_request
                else:
                    self.logger.info(f"Keine weiteren Seiten für den aktuellen Datumsbereich gefunden")
                    next_request = self.switch_to_next_config()
                    if next_request:
                        yield next_request
            except Exception as e:
                self.logger.error(f"Fehler bei der Navigation zur nächsten Seite: {str(e)}")
                next_request = self.switch_to_next_config()
                if next_request:
                    yield next_request
        else:
            self.logger.info(f"Anzahl der Zielergebnisse für den aktuellen Datumsbereich erreicht: {current_config['current_results']} Listings gesammelt")
            next_request = self.switch_to_next_config()
            if next_request:
                yield next_request
        
    def switch_to_next_config(self):
        """Wechselt zur nächsten Datumskonfiguration und gibt ein Request-Objekt zurück, falls verfügbar"""
        self.current_config_index += 1
        if self.current_config_index < len(self.search_configs):
            next_config = self.search_configs[self.current_config_index]
            self.logger.info(f"Wechsel zum nächsten Datumsbereich: {next_config['checkin']} bis {next_config['checkout']}")
            
            # Erstelle die URL für die neue Konfiguration
            next_url = f"{self.base_url}?checkin={next_config['checkin']}&checkout={next_config['checkout']}&page=1&items_per_page=20"
            
            # Wichtig: Gib das Request-Objekt zurück, damit es an der aufrufenden Stelle verarbeitet werden kann
            return scrapy.Request(next_url, self.parse, dont_filter=True)
        return None
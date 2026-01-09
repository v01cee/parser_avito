"""
Парсер Авито с использованием браузера (Selenium)
Имитирует действия пользователя: поиск, сортировка, получение последнего объявления
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from typing import Optional, Dict, List
from datetime import datetime
import os

# Пробуем использовать webdriver-manager, если не получается - используем системный ChromeDriver
try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except:
    USE_WDM = False


class AvitoBrowserParser:
    def __init__(self, headless: bool = True):
        """
        Инициализация парсера с браузером
        
        Args:
            headless: Запускать браузер в фоновом режиме (без окна)
        """
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def init_driver(self):
        """Инициализация веб-драйвера Chrome"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')  # Новый headless режим
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        
        # Улучшенный user-agent для имитации реального пользователя
        import random
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # Добавляем прокси если указан
        if self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
            print(f"🌐 Используется прокси: {self.proxy.split('@')[-1] if '@' in self.proxy else self.proxy}")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Дополнительные опции для обхода детекции
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        
        # Для Docker добавляем дополнительные опции
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--disable-setuid-sandbox')
        
        try:
            # Пробуем использовать webdriver-manager
            if USE_WDM:
                try:
                    driver_path = ChromeDriverManager().install()
                    # ChromeDriverManager может вернуть путь к директории или неправильный файл
                    import os
                    import glob
                    # Если это директория, ищем chromedriver внутри
                    if os.path.isdir(driver_path):
                        # Ищем chromedriver в директории и поддиректориях
                        possible_paths = [
                            os.path.join(driver_path, 'chromedriver'),
                            os.path.join(driver_path, 'chromedriver-linux64', 'chromedriver'),
                            os.path.join(driver_path, 'chromedriver', 'chromedriver'),
                        ]
                        # Также ищем через glob (включая все поддиректории)
                        chromedriver_files = glob.glob(os.path.join(driver_path, '**/chromedriver'), recursive=True)
                        # Исключаем файлы с THIRD_PARTY_NOTICES
                        chromedriver_files = [f for f in chromedriver_files if 'THIRD_PARTY_NOTICES' not in f]
                        possible_paths.extend(chromedriver_files)
                        
                        found = False
                        for path in possible_paths:
                            if os.path.exists(path) and os.path.isfile(path) and os.access(path, os.X_OK):
                                # Проверяем что это не директория и не текстовый файл
                                if not os.path.isdir(path) and 'THIRD_PARTY_NOTICES' not in path:
                                    driver_path = path
                                    found = True
                                    break
                        
                        if not found:
                            # Последняя попытка - найти любой исполняемый файл chromedriver
                            all_files = glob.glob(os.path.join(driver_path, '**/*'), recursive=True)
                            for path in all_files:
                                if os.path.isfile(path) and 'chromedriver' in os.path.basename(path).lower() and 'THIRD_PARTY_NOTICES' not in path:
                                    if os.access(path, os.X_OK):
                                        driver_path = path
                                        found = True
                                        break
                            
                            if not found:
                                raise Exception(f"Не найден исполняемый chromedriver в {driver_path}")
                    # Если это файл, проверяем что это не THIRD_PARTY_NOTICES
                    elif os.path.isfile(driver_path):
                        if 'THIRD_PARTY_NOTICES' in driver_path or not driver_path.endswith('chromedriver'):
                            # Ищем chromedriver в той же директории
                            dir_path = os.path.dirname(driver_path)
                            chromedriver_file = os.path.join(dir_path, 'chromedriver')
                            if os.path.exists(chromedriver_file) and os.access(chromedriver_file, os.X_OK):
                                driver_path = chromedriver_file
                            else:
                                # Ищем в поддиректориях
                                chromedriver_files = glob.glob(os.path.join(dir_path, '**/chromedriver'), recursive=True)
                                for path in chromedriver_files:
                                    if os.access(path, os.X_OK):
                                        driver_path = path
                                        break
                                else:
                                    raise Exception(f"Не найден исполняемый chromedriver в {dir_path}")
                    
                    print(f"✅ Используется ChromeDriver: {driver_path}")
                    service = Service(driver_path)
                except Exception as e:
                    print(f"⚠️ ChromeDriverManager не сработал: {e}")
                    print("💡 Пробую использовать системный ChromeDriver...")
                    # Если не работает, используем системный ChromeDriver
                    service = Service()
            else:
                # Используем системный ChromeDriver (должен быть в PATH)
                service = Service()
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            print("✅ Браузер инициализирован")
        except Exception as e:
            print(f"❌ Ошибка при инициализации браузера: {e}")
            print("💡 Убедитесь, что Chrome установлен и ChromeDriver доступен")
            raise
    
    def close_driver(self):
        """Закрытие браузера"""
        if self.driver:
            self.driver.quit()
            print("✅ Браузер закрыт")
    
    def search_item(self, query: str) -> bool:
        """
        Поиск товара на Авито
        
        Args:
            query: Название товара для поиска
        
        Returns:
            True если поиск выполнен успешно
        """
        try:
            # Открываем главную страницу Авито
            print(f"🔍 Открываю страницу Авито...")
            self.driver.get("https://www.avito.ru/")
            time.sleep(3)  # Ждем загрузки
            
            # Проверяем, не заблокирован ли доступ
            page_text = self.driver.page_source.lower()
            if "доступ ограничен" in page_text or "access denied" in page_text or "проблема с ip" in page_text:
                print("⚠️ Авито заблокировал доступ (проблема с IP)")
                print("💡 Возможные причины:")
                print("   - Слишком частые запросы")
                print("   - IP используется несколькими пользователями")
                print("   - Нужно решить капчу")
                # Пробуем нажать кнопку "Продолжить" если есть
                try:
                    continue_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Продолжить') or contains(text(), 'Continue')]")
                    if continue_btn:
                        print("🔄 Пробую нажать 'Продолжить'...")
                        continue_btn.click()
                        time.sleep(5)  # Ждем обработки капчи
                        # Проверяем снова
                        page_text = self.driver.page_source.lower()
                        if "доступ ограничен" in page_text or "проблема с ip" in page_text:
                            print("❌ Блокировка не снята, нужна ручная проверка")
                            return False
                except:
                    pass
                # Если все еще заблокировано, возвращаем ошибку
                page_text = self.driver.page_source.lower()
                if "доступ ограничен" in page_text or "проблема с ip" in page_text:
                    return False
            
            # Пробуем закрыть возможные модальные окна (cookies, регистрация и т.д.)
            try:
                # Ищем и закрываем кнопки "Принять", "Закрыть", "Понятно" и т.д.
                close_buttons = [
                    "button[data-marker='cookie-policy-agreement']",
                    "button[class*='close']",
                    "button[class*='accept']",
                    "button[aria-label*='Закрыть']",
                    "//button[contains(text(), 'Принять')]",
                    "//button[contains(text(), 'Закрыть')]",
                    "//button[contains(text(), 'Понятно')]"
                ]
                for btn_selector in close_buttons:
                    try:
                        if btn_selector.startswith("//"):
                            btn = self.driver.find_element(By.XPATH, btn_selector)
                        else:
                            btn = self.driver.find_element(By.CSS_SELECTOR, btn_selector)
                        if btn and btn.is_displayed():
                            btn.click()
                            time.sleep(1)
                            print("✅ Закрыто модальное окно")
                            break
                    except:
                        continue
            except:
                pass  # Игнорируем ошибки при закрытии модальных окон
            
            # Находим поле поиска
            # Попробуем разные селекторы для поля поиска
            search_selectors = [
                "input[data-marker='search-form/suggest']",
                "input[placeholder*='Поиск']",
                "input[placeholder*='поиск']",
                "input[type='search']",
                "input[name='q']",
                "input[id*='search']",
                "input[class*='search']",
                "#search-input",
                "input.input-input-Zpzc1",
                "input[aria-label*='Поиск']",
                "input[aria-label*='поиск']"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if search_input and search_input.is_displayed():
                        print(f"✅ Найдено поле поиска через селектор: {selector}")
                        break
                except Exception as e:
                    continue
            
            if not search_input:
                # Пробуем найти через XPath
                xpath_selectors = [
                    "//input[contains(@placeholder, 'Поиск') or contains(@placeholder, 'поиск')]",
                    "//input[@type='search']",
                    "//input[contains(@data-marker, 'search')]",
                    "//input[contains(@class, 'search')]"
                ]
                for xpath in xpath_selectors:
                    try:
                        search_input = self.driver.find_element(By.XPATH, xpath)
                        if search_input and search_input.is_displayed():
                            print(f"✅ Найдено поле поиска через XPath: {xpath}")
                            break
                    except:
                        continue
            
            if not search_input:
                # Последняя попытка - найти любое поле ввода в области поиска
                try:
                    # Ищем форму поиска
                    search_form = self.driver.find_element(By.CSS_SELECTOR, "form[data-marker='search-form'], form[class*='search']")
                    search_input = search_form.find_element(By.TAG_NAME, "input")
                    print("✅ Найдено поле поиска через форму")
                except:
                    print("❌ Не удалось найти поле поиска")
                    # Сохраняем скриншот и HTML для отладки
                    try:
                        screenshot_path = "/app/data/debug_search_failed.png"
                        html_path = "/app/data/debug_page.html"
                        self.driver.save_screenshot(screenshot_path)
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        print(f"💾 Скриншот сохранен: {screenshot_path}")
                        print(f"💾 HTML сохранен: {html_path}")
                        # Выводим информацию о найденных input элементах
                        inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        print(f"🔍 Найдено input элементов на странице: {len(inputs)}")
                        for i, inp in enumerate(inputs[:5]):  # Показываем первые 5
                            try:
                                placeholder = inp.get_attribute('placeholder') or 'нет'
                                data_marker = inp.get_attribute('data-marker') or 'нет'
                                input_type = inp.get_attribute('type') or 'нет'
                                print(f"   Input {i+1}: type={input_type}, placeholder={placeholder[:30]}, data-marker={data_marker}")
                            except:
                                pass
                    except Exception as e:
                        print(f"⚠️ Ошибка при сохранении отладочной информации: {e}")
                    return False
            
            print(f"📝 Ввожу запрос: {query}")
            # Очищаем поле и вводим запрос (имитируем реального пользователя)
            search_input.click()  # Кликаем на поле
            time.sleep(0.5)
            search_input.clear()
            time.sleep(0.3)
            # Вводим по одной букве для имитации реального пользователя
            for char in query:
                search_input.send_keys(char)
                time.sleep(0.1)  # Небольшая задержка между символами
            time.sleep(1)
            
            # Нажимаем Enter для поиска
            search_input.send_keys(Keys.RETURN)
            print("⏳ Жду загрузки результатов...")
            
            # Ждем загрузки результатов поиска
            time.sleep(5)  # Увеличиваем время ожидания
            
            # Проверяем, не заблокирован ли доступ после поиска
            page_text = self.driver.page_source.lower()
            if "доступ ограничен" in page_text or "проблема с ip" in page_text:
                print("⚠️ Авито заблокировал доступ после поиска")
                return False
            
            # Проверяем, что мы на странице результатов
            current_url = self.driver.current_url
            if 'avito.ru' in current_url and ('q=' in current_url or '/all' in current_url):
                print("✅ Поиск выполнен успешно")
                return True
            else:
                print(f"⚠️ Возможно, страница не загрузилась. URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при поиске: {e}")
            return False
    
    def set_sort_by_date(self) -> bool:
        """
        Установка сортировки по дате
        
        Returns:
            True если сортировка установлена успешно
        """
        try:
            print("🔄 Ищу кнопку сортировки...")
            
            # Сначала сохраняем HTML для анализа (если нужно)
            try:
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print("💾 HTML страницы сохранен в debug_page.html")
            except:
                pass
            
            # Ищем все кнопки на странице для отладки
            try:
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                print(f"🔍 Найдено всего кнопок на странице: {len(all_buttons)}")
                
                # Ищем кнопки со словом "сортировка" в тексте или атрибутах
                sort_related = []
                for btn in all_buttons[:50]:  # Проверяем первые 50
                    try:
                        text = btn.text.lower()
                        aria_label = btn.get_attribute('aria-label') or ''
                        data_marker = btn.get_attribute('data-marker') or ''
                        
                        if 'сортир' in text or 'сортир' in aria_label.lower() or 'sort' in data_marker.lower():
                            sort_related.append({
                                'text': btn.text[:50],
                                'aria-label': aria_label[:50],
                                'data-marker': data_marker,
                                'class': btn.get_attribute('class')[:100]
                            })
                    except:
                        continue
                
                if sort_related:
                    print("🔍 Найдены кнопки связанные со сортировкой:")
                    for i, btn_info in enumerate(sort_related[:5], 1):
                        print(f"   {i}. Текст: '{btn_info['text']}' | data-marker: '{btn_info['data-marker']}' | aria-label: '{btn_info['aria-label']}'")
            except Exception as e:
                print(f"⚠️ Ошибка при поиске кнопок: {e}")
            
            # Ищем кнопку сортировки - расширенный список селекторов
            sort_selectors = [
                # По data-marker
                "button[data-marker='sort-button']",
                "button[data-marker*='sort']",
                "div[data-marker='sort-button']",
                # По тексту через XPath
                "//button[contains(text(), 'Сортировка')]",
                "//button[contains(text(), 'сортировка')]",
                "//button[contains(., 'Сортировка')]",
                "//div[contains(text(), 'Сортировка')]",
                "//span[contains(text(), 'Сортировка')]",
                "//span[contains(text(), 'Сортировка')]/ancestor::button",
                "//span[contains(text(), 'Сортировка')]/parent::button",
                "//span[contains(text(), 'Сортировка')]/parent::div",
                # По классам
                ".sort-select-button",
                "[class*='sort']",
                "[class*='Sort']",
                # По aria-label
                "button[aria-label*='Сортировка']",
                "button[aria-label*='сортировка']",
                "button[aria-label*='sort']",
                # Альтернативные варианты
                "//button[contains(@aria-label, 'Сортировка')]",
                "//div[contains(@class, 'sort')]",
            ]
            
            sort_button = None
            for i, selector in enumerate(sort_selectors, 1):
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        sort_button = elements[0]
                        print(f"✅ Найдена кнопка сортировки через селектор #{i}: {selector}")
                        print(f"   Текст кнопки: '{sort_button.text[:50]}'")
                        print(f"   data-marker: '{sort_button.get_attribute('data-marker')}'")
                        break
                except Exception as e:
                    continue
            
            if not sort_button:
                print("❌ Не удалось найти кнопку сортировки ни одним способом")
                
                # Сохраняем скриншот для анализа
                try:
                    screenshot_path = 'debug_screenshot.png'
                    self.driver.save_screenshot(screenshot_path)
                    print(f"📸 Скриншот сохранен: {screenshot_path}")
                except:
                    pass
                
                # Ищем все элементы содержащие слово "сортировка" в любом виде
                try:
                    print("\n🔍 Ищу все элементы со словом 'сортировка'...")
                    all_elements = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'СОРТИРОВКА', 'сортировка'), 'сортировка')]")
                    print(f"   Найдено элементов: {len(all_elements)}")
                    for i, elem in enumerate(all_elements[:10], 1):
                        try:
                            tag = elem.tag_name
                            text = elem.text[:50] if elem.text else ''
                            parent = elem.find_element(By.XPATH, "./..")
                            parent_tag = parent.tag_name
                            parent_class = parent.get_attribute('class')[:50] if parent.get_attribute('class') else ''
                            print(f"   {i}. <{tag}> '{text}' -> родитель <{parent_tag}> class='{parent_class}'")
                        except:
                            pass
                except Exception as e:
                    print(f"   Ошибка при поиске: {e}")
                
                print("\n💡 Помоги найти кнопку:")
                print("   1. Открой страницу результатов поиска вручную (браузер сейчас открыт)")
                print("   2. Найди кнопку 'Сортировка' на странице")
                print("   3. Правый клик на кнопке -> Inspect (Исследовать элемент) или F12")
                print("   4. В DevTools найди элемент и посмотри его атрибуты:")
                print("      - data-marker='...' ?")
                print("      - class='...' ?")
                print("      - id='...' ?")
                print("   5. Скажи мне эти атрибуты, и я добавлю правильный селектор")
                return False
            
            print("🖱️ Нажимаю на кнопку сортировки...")
            # Прокручиваем к кнопке если нужно
            self.driver.execute_script("arguments[0].scrollIntoView(true);", sort_button)
            time.sleep(0.5)
            
            # Нажимаем на кнопку
            sort_button.click()
            time.sleep(1)
            
            # Ищем опцию "По дате"
            print("📅 Ищу опцию 'По дате'...")
            date_sort_selectors = [
                "//span[contains(text(), 'По дате')]",
                "//div[contains(text(), 'По дате')]",
                "//button[contains(text(), 'По дате')]",
                "//a[contains(text(), 'По дате')]",
                "[data-marker='sort-option-date']",
            ]
            
            date_option = None
            for selector in date_sort_selectors:
                try:
                    if selector.startswith("//"):
                        date_option = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        date_option = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if date_option:
                        break
                except:
                    continue
            
            if not date_option:
                print("❌ Не удалось найти опцию 'По дате'")
                return False
            
            print("✅ Выбираю сортировку по дате...")
            date_option.click()
            time.sleep(2)  # Ждем применения сортировки
            
            print("✅ Сортировка по дате установлена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при установке сортировки: {e}")
            return False
    
    def get_last_item_link(self) -> Optional[str]:
        """
        Получение ссылки на последнее объявление
        
        Returns:
            Ссылка на последнее объявление или None
        """
        try:
            print("🔗 Ищу последнее объявление...")
            
            # Ждем загрузки списка объявлений
            time.sleep(2)
            
            # Ищем объявления
            item_selectors = [
                "a[data-marker='item-title']",
                "a[href*='/items/']",
                "a[href*='/i']",
                ".iva-item-titleStep-pdebR a",
                "[data-marker='item'] a",
            ]
            
            items = []
            for selector in item_selectors:
                try:
                    if selector.startswith("//"):
                        items = self.driver.find_elements(By.XPATH, selector)
                    else:
                        items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        break
                except:
                    continue
            
            if not items:
                print("❌ Не найдено объявлений на странице")
                return None
            
            print(f"📋 Найдено объявлений: {len(items)}")
            
            # Берем первое объявление (последнее по дате после сортировки)
            first_item = items[0]
            link = first_item.get_attribute('href')
            
            if not link:
                # Пробуем получить через родительский элемент
                parent = first_item.find_element(By.XPATH, "./ancestor::a[@href]")
                if parent:
                    link = parent.get_attribute('href')
            
            if link:
                # Убеждаемся, что ссылка полная
                if link.startswith('/'):
                    link = f"https://www.avito.ru{link}"
                
                print(f"✅ Найдена ссылка на последнее объявление: {link}")
                return link
            else:
                print("❌ Не удалось получить ссылку")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при получении ссылки: {e}")
            return None
    
    def get_last_item_info(self) -> Optional[Dict]:
        """
        Получение полной информации о последнем объявлении
        
        Returns:
            Словарь с информацией об объявлении или None
        """
        try:
            link = self.get_last_item_link()
            if not link:
                return None
            
            # Получаем дополнительную информацию о первом объявлении
            item_selectors = [
                "[data-marker='item']:first-child",
                ".items-items-kAJAg > div:first-child",
            ]
            
            item_element = None
            for selector in item_selectors:
                try:
                    item_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if item_element:
                        break
                except:
                    continue
            
            title = ""
            price = ""
            
            if item_element:
                try:
                    title_elem = item_element.find_element(By.CSS_SELECTOR, "[data-marker='item-title'], .title-root-zZCwT, h3")
                    title = title_elem.text
                except:
                    pass
                
                try:
                    price_elem = item_element.find_element(By.CSS_SELECTOR, "[data-marker='item-price'], .price-text-_YGDY")
                    price = price_elem.text
                except:
                    pass
            
            return {
                'title': title,
                'price': price,
                'link': link,
                'found_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Ошибка при получении информации: {e}")
            return None
    
    def search_and_get_last(self, query: str) -> Optional[Dict]:
        """
        Полный цикл: поиск, сортировка, получение последнего объявления
        
        Args:
            query: Название товара для поиска
        
        Returns:
            Информация о последнем объявлении или None
        """
        try:
            # Инициализируем браузер
            if not self.driver:
                self.init_driver()
            
            # Выполняем поиск
            if not self.search_item(query):
                return None
            
            # Устанавливаем сортировку по дате
            if not self.set_sort_by_date():
                print("⚠️ Не удалось установить сортировку, но продолжаю...")
            
            # Получаем информацию о последнем объявлении
            item_info = self.get_last_item_info()
            
            return item_info
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении поиска: {e}")
            return None


def main():
    """Тестирование парсера"""
    parser = AvitoBrowserParser(headless=False)  # headless=False для визуального контроля
    
    try:
        query = input("Введите название товара для поиска: ")
        if not query:
            query = "iphone"
        
        result = parser.search_and_get_last(query)
        
        if result:
            print("\n" + "="*60)
            print("РЕЗУЛЬТАТ ПОИСКА:")
            print("="*60)
            print(f"Заголовок: {result.get('title', 'N/A')}")
            print(f"Цена: {result.get('price', 'N/A')}")
            print(f"Ссылка: {result.get('link', 'N/A')}")
            print("="*60)
        else:
            print("❌ Не удалось получить информацию об объявлении")
            
    except KeyboardInterrupt:
        print("\n\nПарсер остановлен пользователем")
    finally:
        parser.close_driver()


if __name__ == '__main__':
    main()


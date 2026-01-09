"""
Парсер объявлений с Авито
"""
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import os
from database import Database
from avito_browser_parser import AvitoBrowserParser
from avito_browser_parser import AvitoBrowserParser


class AvitoParser:
    def __init__(self, config_path: str = "config.json", notify_callback=None, use_db: bool = True, use_browser: bool = True):
        """
        Инициализация парсера
        
        Args:
            config_path: Путь к файлу конфигурации (используется как fallback)
            notify_callback: Функция для отправки уведомлений (принимает item: Dict)
            use_db: Использовать SQLite базу данных вместо JSON файлов
            use_browser: Использовать браузер (Selenium) для парсинга
        """
        self.config_path = config_path
        self.use_db = use_db
        self.use_browser = use_browser
        
        # Инициализируем базу данных
        if use_db:
            self.db = Database()
            self.config = self.load_config_from_db()
        else:
            self.db = None
            self.config = self.load_config()
        
        # Инициализируем браузерный парсер если нужно (но не создаем браузер сразу)
        if use_browser:
            # Проверяем наличие прокси в переменных окружения
            import os
            proxy = os.getenv('AVITO_PROXY', None)
            self.browser_parser = AvitoBrowserParser(headless=True, proxy=proxy)
            # Не инициализируем браузер сразу, только при первом использовании
            self.browser_parser.driver = None
        else:
            self.browser_parser = None
            self.ua = UserAgent()
            self.session = requests.Session()
        
        self.notify_callback = notify_callback
        
    def load_config_from_db(self) -> dict:
        """Загрузка конфигурации из базы данных"""
        if not self.db:
            return self.load_config()
        
        # Загружаем конфигурацию из БД
        config = self.db.get_all_config()
        
        if 'search_params' not in config or not config.get('search_params', {}).get('query'):
            # Если конфигурации нет в БД, создаем дефолтную с хардкод данными для теста
            default_config = {
                "search_params": {
                    "query": "iphone",  # ХАРДКОД для теста
                    "location": "",
                    "category": "",
                    "price_min": "",
                    "price_max": "",
                    "sort": "date"
                },
                "check_interval_minutes": 1,
                "notify_on_new": True
            }
            self.save_config_to_db(default_config)
            return default_config
        
        # Восстанавливаем структуру конфигурации
        result = {
            "search_params": config.get('search_params', {
                "query": "iphone",  # ХАРДКОД для теста
                "location": "",
                "category": "",
                "price_min": "",
                "price_max": "",
                "sort": "date"
            }),
            "check_interval_minutes": config.get('check_interval_minutes', 1),
            "notify_on_new": config.get('notify_on_new', True)
        }
        
        # Если query пустой, ставим дефолт
        if not result['search_params'].get('query'):
            result['search_params']['query'] = "iphone"
        
        return result
    
    def load_config(self) -> dict:
        """Загрузка конфигурации из файла (fallback)"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Если query пустой, ставим дефолт
                if not config.get('search_params', {}).get('query'):
                    config['search_params']['query'] = "iphone"
                return config
        except FileNotFoundError:
            print(f"Файл конфигурации {self.config_path} не найден. Использую хардкод данные.")
            default_config = {
                "search_params": {
                    "query": "iphone",  # ХАРДКОД для теста
                    "location": "",
                    "category": "",
                    "price_min": "",
                    "price_max": "",
                    "sort": "date"
                },
                "check_interval_minutes": 1,
                "notify_on_new": True
            }
            return default_config
    
    def save_config_to_db(self, config: dict = None):
        """Сохранение конфигурации в базу данных"""
        if not self.db:
            self.save_config(config)
            return
        
        if config is None:
            config = self.config
        
        # Сохраняем каждое значение отдельно
        self.db.set_config('search_params', config.get('search_params', {}))
        self.db.set_config('check_interval_minutes', config.get('check_interval_minutes', 1))
        self.db.set_config('notify_on_new', config.get('notify_on_new', True))
    
    def save_config(self, config: dict = None):
        """Сохранение конфигурации в файл (fallback)"""
        if self.use_db and self.db:
            self.save_config_to_db(config)
            return
        
        if config is None:
            config = self.config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def is_item_found(self, item_id: str) -> bool:
        """Проверка, найдено ли объявление ранее"""
        if self.use_db and self.db:
            return self.db.is_item_found(item_id)
        else:
            # Fallback на старый метод (для совместимости)
            return item_id in self.load_found_items()
    
    def add_found_item(self, item: Dict) -> bool:
        """Добавление найденного объявления"""
        if self.use_db and self.db:
            return self.db.add_found_item(item)
        else:
            # Fallback на старый метод
            item_id = item.get('id')
            if not item_id:
                return False
            
            found_items = self.load_found_items()
            if item_id in found_items:
                return False
            
            found_items.add(item_id)
            self.save_found_items_set(found_items)
            return True
    
    def load_found_items(self) -> set:
        """Загрузка списка уже найденных объявлений (для fallback)"""
        if self.use_db and self.db:
            # Возвращаем пустой set, так как проверка идет через БД
            return set()
        else:
            try:
                with open('found_items.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('item_ids', []))
            except FileNotFoundError:
                return set()
    
    def save_found_items_set(self, found_items: set):
        """Сохранение списка найденных объявлений (для fallback)"""
        with open('found_items.json', 'w', encoding='utf-8') as f:
            json.dump({'item_ids': list(found_items)}, f, ensure_ascii=False, indent=2)
    
    def save_found_items(self):
        """Сохранение найденных объявлений (оставлено для совместимости)"""
        # Метод больше не нужен при использовании БД, но оставлен для обратной совместимости
        pass
    
    def build_url(self) -> str:
        """Построение URL для поиска на Авито"""
        from urllib.parse import quote, urlencode
        
        base_url = "https://www.avito.ru"
        params = self.config['search_params']
        
        # Формируем путь поиска
        path_parts = []
        
        if params.get('location'):
            # Кодируем локацию для URL
            location = params['location'].lower().replace(' ', '-')
            path_parts.append(location)
        
        if params.get('category'):
            category = params['category'].lower().replace(' ', '-')
            path_parts.append(category)
        
        # Добавляем параметры запроса
        query_params = {}
        
        if params.get('query'):
            query_params['q'] = params['query']
        
        if params.get('price_min'):
            query_params['pmin'] = params['price_min']
        
        if params.get('price_max'):
            query_params['pmax'] = params['price_max']
        
        if params.get('sort'):
            query_params['s'] = params['sort']
        
        # Строим URL
        if path_parts:
            url = f"{base_url}/{'/'.join(path_parts)}"
        else:
            url = f"{base_url}/all"
        
        if query_params:
            url += "?" + urlencode(query_params, doseq=True)
        
        return url
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Получение HTML страницы"""
        try:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Ошибка при получении страницы: {e}")
            return None
    
    def parse_items(self, soup: BeautifulSoup) -> List[Dict]:
        """Парсинг объявлений со страницы"""
        items = []
        
        if not soup:
            return items
        
        # Ищем контейнеры с объявлениями
        # Авито использует различные селекторы, попробуем несколько вариантов
        item_selectors = [
            'div[data-marker="item"]',
            'div[data-marker*="item"]',
            'article[data-marker="item"]',
            'div[itemprop="itemListElement"]',
            'div[class*="iva-item"]',
            'div[class*="item-root"]',
        ]
        
        item_elements = []
        for selector in item_selectors:
            found = soup.select(selector)
            if found:
                item_elements = found
                break
        
        # Если не нашли через селекторы, пробуем найти по структуре
        if not item_elements:
            # Ищем все div с классами содержащими item
            item_elements = soup.find_all('div', class_=lambda x: x and (
                'item' in str(x).lower() or 
                'iva-item' in str(x).lower() or
                'item-root' in str(x).lower()
            ))
        
        # Также пробуем найти через data-item-id
        if not item_elements:
            item_elements = soup.find_all(attrs={'data-item-id': True})
        
        print(f"Найдено элементов на странице: {len(item_elements)}")
        
        for item in item_elements[:30]:  # Ограничиваем до 30 объявлений за раз
            try:
                item_data = self.extract_item_data(item)
                if item_data and item_data.get('id'):
                    items.append(item_data)
            except Exception as e:
                print(f"Ошибка при парсинге объявления: {e}")
                continue
        
        return items
    
    def extract_item_data(self, item_element) -> Optional[Dict]:
        """Извлечение данных из объявления"""
        try:
            # Получаем ID объявления
            item_id = None
            item_link = None
            
            # Сначала пробуем найти data-item-id
            item_id = item_element.get('data-item-id')
            
            # Ищем ссылку на объявление
            link_elem = item_element.find('a', href=True)
            if link_elem:
                item_link = link_elem.get('href', '')
                if item_link.startswith('/'):
                    item_link = f"https://www.avito.ru{item_link}"
                
                # Извлекаем ID из ссылки если еще не нашли
                if not item_id:
                    if '/items/' in item_link:
                        item_id = item_link.split('/items/')[-1].split('?')[0]
                    elif '/i' in item_link:
                        # Формат: /category/location/i/item_id
                        parts = item_link.split('/')
                        for i, part in enumerate(parts):
                            if part == 'i' and i + 1 < len(parts):
                                item_id = parts[i + 1].split('?')[0]
                                break
                    else:
                        # Пробуем найти ID в любом месте ссылки
                        import re
                        match = re.search(r'/(\d+)(?:\?|$)', item_link)
                        if match:
                            item_id = match.group(1)
            
            # Если все еще нет ID, пробуем найти в других атрибутах
            if not item_id:
                item_id = item_element.get('id', '')
                # Убираем префиксы если есть
                if item_id and '_' in item_id:
                    item_id = item_id.split('_')[-1]
            
            if not item_id:
                return None
            
            # Получаем заголовок
            title = ""
            # Пробуем разные варианты поиска заголовка
            title_selectors = [
                ('h3', lambda x: 'title' in str(x).lower()),
                ('a', lambda x: 'title' in str(x).lower() or 'link' in str(x).lower()),
                ('div', lambda x: 'title' in str(x).lower()),
                ('span', lambda x: 'title' in str(x).lower()),
            ]
            
            for tag, class_check in title_selectors:
                title_elem = item_element.find(tag, class_=class_check)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # Если не нашли, берем первый заголовок или ссылку
            if not title:
                title_elem = item_element.find(['h3', 'h2', 'h1', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            # Получаем цену
            price = ""
            price_selectors = [
                ('span', lambda x: 'price' in str(x).lower()),
                ('div', lambda x: 'price' in str(x).lower()),
            ]
            
            for tag, class_check in price_selectors:
                price_elem = item_element.find(tag, class_=class_check)
                if price_elem:
                    price = price_elem.get_text(strip=True)
                    if price:
                        break
            
            # Пробуем через meta
            if not price:
                price_elem = item_element.find('meta', {'itemprop': 'price'})
                if price_elem:
                    price = price_elem.get('content', '')
            
            # Получаем описание/локацию
            description = ""
            desc_elem = item_element.find(['div', 'span'], class_=lambda x: x and (
                'description' in str(x).lower() or 
                'location' in str(x).lower() or
                'geo' in str(x).lower()
            ))
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            return {
                'id': str(item_id),
                'title': title,
                'price': price,
                'description': description,
                'link': item_link or f"https://www.avito.ru/item/{item_id}",
                'found_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Ошибка при извлечении данных: {e}")
            return None
    
    def check_new_items(self) -> List[Dict]:
        """Проверка новых объявлений"""
        search_params = self.config.get('search_params', {})
        query = search_params.get('query', '')
        
        if not query:
            print("❌ Параметры поиска не заданы!")
            return []
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверяю запрос: {query}")
        
        # Используем браузерный парсер если включен
        if self.use_browser and self.browser_parser:
            return self.check_new_items_browser(query)
        else:
            # Используем старый метод через requests
            return self.check_new_items_requests()
    
    def check_new_items_browser(self, query: str) -> List[Dict]:
        """Проверка новых объявлений через браузер"""
        browser_was_init = False
        try:
            # Инициализируем браузер если еще не инициализирован
            if not self.browser_parser.driver:
                self.browser_parser.init_driver()
                browser_was_init = True
            
            # Выполняем поиск и получаем последнее объявление
            last_item = self.browser_parser.search_and_get_last(query)
            
            if not last_item:
                # Проверяем, не заблокирован ли доступ
                if hasattr(self.browser_parser, 'driver') and self.browser_parser.driver:
                    try:
                        page_text = self.browser_parser.driver.page_source.lower()
                        if "доступ ограничен" in page_text or "проблема с ip" in page_text:
                            print("⚠️ Авито заблокировал IP. Пропускаю эту проверку.")
                            print("💡 Рекомендации:")
                            print("   - Увеличьте интервал проверки (минимум 5-10 минут)")
                            print("   - Подождите некоторое время перед следующей проверкой")
                            return []  # Возвращаем пустой список, не считаем это ошибкой
                    except:
                        pass
                
                print("⚠️ Не удалось получить информацию об объявлении")
                return []
            
            # Извлекаем ID из ссылки
            link = last_item.get('link', '')
            item_id = None
            if link:
                # Пробуем извлечь ID из разных форматов ссылок
                if '/items/' in link:
                    item_id = link.split('/items/')[-1].split('?')[0]
                elif '/i' in link:
                    # Формат: /category/location/i/item_id или /location/category/i/item_id
                    parts = link.split('/i')
                    if len(parts) > 1:
                        # Берем последнюю часть до ? или /
                        item_id = parts[-1].split('?')[0].split('/')[0]
            
            if not item_id:
                # Используем хеш от ссылки как ID
                import hashlib
                item_id = hashlib.md5(link.encode()).hexdigest()[:16]
            
            # Создаем объект объявления
            item = {
                'id': item_id,
                'title': last_item.get('title', ''),
                'price': last_item.get('price', ''),
                'description': '',
                'link': link,
                'found_at': datetime.now().isoformat()
            }
            
            # Просто отправляем объявление без проверки
            new_items = [item]
            
            # Сохраняем в БД
            self.add_found_item(item)
            
            # Отправляем уведомление
            if self.config.get('notify_on_new', True):
                self.notify_new_item(item)
                # Вызываем callback если он установлен
                if self.notify_callback:
                    try:
                        self.notify_callback(item)
                    except Exception as e:
                        print(f"Ошибка в callback уведомления: {e}")
            
            print(f"✅ Найдено объявление и отправлено")
            
            return new_items
            
        except Exception as e:
            print(f"❌ Ошибка при проверке через браузер: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            # Закрываем браузер только если мы его создали в этом вызове
            # Или закрываем всегда для освобождения ресурсов между проверками
            if self.browser_parser and self.browser_parser.driver:
                try:
                    self.browser_parser.close_driver()
                    # Сбрасываем driver чтобы при следующем вызове создался новый
                    self.browser_parser.driver = None
                except Exception as e:
                    print(f"⚠️ Ошибка при закрытии браузера: {e}")
    
    def check_new_items_requests(self) -> List[Dict]:
        """Проверка новых объявлений через requests (старый метод)"""
        url = self.build_url()
        print(f"Проверяю URL: {url}")
        
        soup = self.get_page(url)
        if not soup:
            print("Не удалось получить страницу")
            return []
        
        items = self.parse_items(soup)
        new_items = []
        
        for item in items:
            item_id = item.get('id')
            if item_id:
                # Проверяем через БД или set
                if not self.is_item_found(item_id):
                    # Добавляем объявление
                    is_new = self.add_found_item(item)
                    if is_new:
                        new_items.append(item)
                        
                        if self.config.get('notify_on_new', True):
                            self.notify_new_item(item)
                            # Вызываем callback если он установлен (для Telegram бота)
                            if self.notify_callback:
                                try:
                                    self.notify_callback(item)
                                except Exception as e:
                                    print(f"Ошибка в callback уведомления: {e}")
        
        if new_items:
            print(f"Найдено новых объявлений: {len(new_items)}")
        else:
            print("Новых объявлений не найдено")
        
        return new_items
    
    def notify_new_item(self, item: Dict):
        """Уведомление о новом объявлении"""
        print("\n" + "="*60)
        print("НОВОЕ ОБЪЯВЛЕНИЕ!")
        print(f"Заголовок: {item.get('title', 'N/A')}")
        print(f"Цена: {item.get('price', 'N/A')}")
        print(f"Описание: {item.get('description', 'N/A')}")
        print(f"Ссылка: {item.get('link', 'N/A')}")
        print("="*60 + "\n")
        
        # Сохранение происходит автоматически в БД через add_found_item
    
    def update_config(self, **kwargs):
        """Обновление параметров поиска"""
        if 'search_params' in kwargs:
            self.config['search_params'].update(kwargs['search_params'])
        else:
            for key, value in kwargs.items():
                if key in self.config:
                    self.config[key] = value
                elif key in self.config.get('search_params', {}):
                    self.config['search_params'][key] = value
        
        self.save_config()
        print("Конфигурация обновлена")
    
    def get_stats(self) -> Dict:
        """Получение статистики"""
        if self.use_db and self.db:
            return self.db.get_stats()
        else:
            return {
                'total_found': len(self.load_found_items()),
                'new_today': 0,
                'last_found_at': None
            }


def main():
    """Главная функция для запуска парсера"""
    # Используем базу данных и браузер по умолчанию
    parser = AvitoParser(use_db=True, use_browser=True)
    
    # Проверяем, заданы ли параметры поиска
    search_params = parser.config.get('search_params', {})
    if not search_params.get('query'):
        print("="*60)
        print("ВНИМАНИЕ: Название товара не задано!")
        print("Используйте Telegram бота (/setup) или отредактируйте config.json")
        print("="*60)
        print("\nПример конфигурации:")
        print(json.dumps({
            "search_params": {
                "query": "iphone"
            }
        }, ensure_ascii=False, indent=2))
        return
    
    # Показываем статистику
    stats = parser.get_stats()
    print(f"📊 Статистика: найдено всего {stats.get('total_found', 0)} объявлений")
    
    # Первая проверка
    try:
        parser.check_new_items()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Периодическая проверка
    interval = parser.config.get('check_interval_minutes', 1)
    print(f"\nПарсер запущен. Проверка каждые {interval} минут(ы)")
    print("Нажмите Ctrl+C для остановки\n")
    
    try:
        while True:
            time.sleep(interval * 60)  # Конвертируем минуты в секунды
            try:
                parser.check_new_items()
            except Exception as e:
                print(f"❌ Ошибка при проверке: {e}")
                import traceback
                traceback.print_exc()
    except KeyboardInterrupt:
        print("\n\nПарсер остановлен пользователем")
        # Закрываем браузер если открыт
        if parser.browser_parser and parser.browser_parser.driver:
            parser.browser_parser.close_driver()
        # При использовании БД сохранение происходит автоматически


if __name__ == "__main__":
    main()


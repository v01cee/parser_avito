"""
Модуль для работы с SQLite базой данных
"""
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
import os


class Database:
    def __init__(self, db_path: str = None):
        """
        Инициализация базы данных
        
        Args:
            db_path: Путь к файлу базы данных (по умолчанию avito_parser.db в текущей директории)
        """
        if db_path is None:
            # В Docker используем /app/db/avito_parser.db, локально - текущая директория
            if os.path.exists("/app"):
                self.db_path = "/app/db/avito_parser.db"
            else:
                self.db_path = os.path.join(os.getcwd(), "avito_parser.db")
        else:
            self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        # Создаем директорию если её нет
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Для удобного доступа к колонкам по имени
        return conn
    
    def init_database(self):
        """Инициализация структуры базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица для найденных объявлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS found_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT UNIQUE NOT NULL,
                title TEXT,
                price TEXT,
                description TEXT,
                link TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified BOOLEAN DEFAULT 0
            )
        ''')
        
        # Таблица для новых объявлений (логирование)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS new_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                title TEXT,
                price TEXT,
                description TEXT,
                link TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для конфигурации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для ускорения поиска
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_item_id ON found_items(item_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_found_at ON found_items(found_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_new_items_at ON new_items(found_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def is_item_found(self, item_id: str) -> bool:
        """Проверка, найдено ли объявление ранее"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM found_items WHERE item_id = ?', (item_id,))
        result = cursor.fetchone() is not None
        
        conn.close()
        return result
    
    def add_found_item(self, item: Dict) -> bool:
        """
        Добавление найденного объявления
        
        Args:
            item: Словарь с данными объявления (id, title, price, description, link)
        
        Returns:
            True если объявление новое (добавлено), False если уже было
        """
        item_id = item.get('id')
        if not item_id:
            return False
        
        # Проверяем, есть ли уже такое объявление
        if self.is_item_found(item_id):
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO found_items (item_id, title, price, description, link, found_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                item.get('title', ''),
                item.get('price', ''),
                item.get('description', ''),
                item.get('link', ''),
                item.get('found_at', datetime.now().isoformat())
            ))
            
            # Также добавляем в таблицу новых объявлений
            cursor.execute('''
                INSERT INTO new_items (item_id, title, price, description, link, found_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                item.get('title', ''),
                item.get('price', ''),
                item.get('description', ''),
                item.get('link', ''),
                item.get('found_at', datetime.now().isoformat())
            ))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Объявление уже существует
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_found_items(self, limit: int = 100) -> List[Dict]:
        """Получение списка найденных объявлений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT item_id, title, price, description, link, found_at
            FROM found_items
            ORDER BY found_at DESC
            LIMIT ?
        ''', (limit,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row['item_id'],
                'title': row['title'],
                'price': row['price'],
                'description': row['description'],
                'link': row['link'],
                'found_at': row['found_at']
            })
        
        conn.close()
        return items
    
    def get_new_items(self, limit: int = 50) -> List[Dict]:
        """Получение последних новых объявлений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT item_id, title, price, description, link, found_at
            FROM new_items
            ORDER BY found_at DESC
            LIMIT ?
        ''', (limit,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row['item_id'],
                'title': row['title'],
                'price': row['price'],
                'description': row['description'],
                'link': row['link'],
                'found_at': row['found_at']
            })
        
        conn.close()
        return items
    
    def mark_as_notified(self, item_id: str):
        """Отметить объявление как отправленное в уведомлении"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE found_items
            SET notified = 1
            WHERE item_id = ?
        ''', (item_id,))
        
        conn.commit()
        conn.close()
    
    def get_config(self, key: str, default: any = None) -> any:
        """Получение значения конфигурации"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row is None:
            return default
        
        try:
            # Пробуем распарсить JSON
            return json.loads(row['value'])
        except:
            # Если не JSON, возвращаем как строку
            return row['value']
    
    def set_config(self, key: str, value: any):
        """Установка значения конфигурации"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Преобразуем значение в JSON строку
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        
        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value_str))
        
        conn.commit()
        conn.close()
    
    def get_all_config(self) -> Dict:
        """Получение всей конфигурации"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT key, value FROM config')
        config = {}
        
        for row in cursor.fetchall():
            try:
                config[row['key']] = json.loads(row['value'])
            except:
                config[row['key']] = row['value']
        
        conn.close()
        return config
    
    def clear_found_items(self):
        """Очистить список найденных объявлений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM found_items')
        cursor.execute('DELETE FROM new_items')
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """Получение статистики"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Общее количество найденных объявлений
        cursor.execute('SELECT COUNT(*) as count FROM found_items')
        total_found = cursor.fetchone()['count']
        
        # Количество новых объявлений за последние 24 часа
        cursor.execute('''
            SELECT COUNT(*) as count FROM new_items
            WHERE found_at > datetime('now', '-1 day')
        ''')
        new_today = cursor.fetchone()['count']
        
        # Последнее найденное объявление
        cursor.execute('''
            SELECT found_at FROM found_items
            ORDER BY found_at DESC
            LIMIT 1
        ''')
        last_found = cursor.fetchone()
        last_found_at = last_found['found_at'] if last_found else None
        
        conn.close()
        
        return {
            'total_found': total_found,
            'new_today': new_today,
            'last_found_at': last_found_at
        }



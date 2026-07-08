from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import sqlite3
import os
import json
from datetime import datetime

# Настройка окна
Window.size = (360, 640)


class NotesApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.storage_mode = 'sqlite'  # 'sqlite' или 'file'
        self.db_name = 'notes.db'
        self.notes_dir = 'notes_files'
        self.init_storage()

    def init_storage(self):
        """Инициализация хранилища"""
        if self.storage_mode == 'sqlite':
            self.init_sqlite()
        else:
            if not os.path.exists(self.notes_dir):
                os.makedirs(self.notes_dir)

    def init_sqlite(self):
        """Создание базы данных SQLite"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def build(self):
        """Построение интерфейса"""
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(NoteEditScreen(name='edit'))
        sm.add_widget(SearchScreen(name='search'))
        return sm


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = NotesApp.get_running_app()

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Заголовок
        title = Label(text='Мои заметки', size_hint_y=0.1, font_size='20sp', bold=True)
        layout.add_widget(title)

        # Информация о хранилище
        storage_info = Label(
            text=f'Хранилище: {"SQLite" if self.app.storage_mode == "sqlite" else "Файловая система"}',
            size_hint_y=0.05,
            font_size='14sp'
        )
        layout.add_widget(storage_info)

        # Список заметок
        self.scroll = ScrollView(size_hint=(1, 0.7))
        self.notes_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.notes_list.bind(minimum_height=self.notes_list.setter('height'))
        self.scroll.add_widget(self.notes_list)
        layout.add_widget(self.scroll)

        # Кнопки управления
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)

        btn_add = Button(text='Добавить', background_color=(0.2, 0.6, 0.8, 1))
        btn_add.bind(on_press=self.add_note)
        btn_layout.add_widget(btn_add)

        btn_search = Button(text='Поиск', background_color=(0.8, 0.6, 0.2, 1))
        btn_search.bind(on_press=self.go_to_search)
        btn_layout.add_widget(btn_search)

        btn_toggle = Button(text='Сменить хранилище', background_color=(0.6, 0.2, 0.6, 1))
        btn_toggle.bind(on_press=self.toggle_storage)
        btn_layout.add_widget(btn_toggle)

        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def on_enter(self):
        """При входе на экран обновить список"""
        self.load_notes()

    def load_notes(self):
        """Загрузка заметок из хранилища"""
        self.notes_list.clear_widgets()

        if self.app.storage_mode == 'sqlite':
            notes = self.load_from_sqlite()
        else:
            notes = self.load_from_files()

        if not notes:
            self.notes_list.add_widget(Label(text='Нет заметок', size_hint_y=None, height=40))
            return

        for note in notes:
            note_widget = self.create_note_widget(note)
            self.notes_list.add_widget(note_widget)

    def load_from_sqlite(self):
        """Загрузка из SQLite"""
        conn = sqlite3.connect(self.app.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, content, date, time FROM notes ORDER BY date DESC, time DESC')
        notes = cursor.fetchall()
        conn.close()
        return [{'id': n[0], 'title': n[1], 'content': n[2], 'date': n[3], 'time': n[4]} for n in notes]

    def load_from_files(self):
        """Загрузка из файлов"""
        notes = []
        if os.path.exists(self.app.notes_dir):
            for filename in os.listdir(self.app.notes_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.app.notes_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        note = json.load(f)
                        note['id'] = filename.replace('.json', '')
                        notes.append(note)
        notes.sort(key=lambda x: (x['date'], x['time']), reverse=True)
        return notes

    def create_note_widget(self, note):
        """Создание виджета заметки"""
        box = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=5)
        box.background_color = (0.9, 0.9, 0.9, 1)

        # Заголовок и дата
        header = BoxLayout(size_hint_y=0.3)
        title_label = Label(text=note['title'], bold=True, halign='left', size_hint_x=0.7)
        title_label.text_size = title_label.size
        header.add_widget(title_label)

        date_label = Label(text=f"{note['date']} {note['time']}", size_hint_x=0.3, font_size='12sp')
        header.add_widget(date_label)
        box.add_widget(header)

        # Содержимое
        content_label = Label(text=note['content'][:100] + ('...' if len(note['content']) > 100 else ''),
                              halign='left', size_hint_y=0.4)
        content_label.text_size = content_label.size
        box.add_widget(content_label)

        # Кнопки
        btn_box = BoxLayout(size_hint_y=0.3, spacing=5)

        btn_edit = Button(text='Редактировать', size_hint_x=0.5, background_color=(0.2, 0.7, 0.3, 1))
        btn_edit.bind(on_press=lambda x: self.edit_note(note))
        btn_box.add_widget(btn_edit)

        btn_delete = Button(text='Удалить', size_hint_x=0.5, background_color=(0.8, 0.2, 0.2, 1))
        btn_delete.bind(on_press=lambda x: self.delete_note(note))
        btn_box.add_widget(btn_delete)

        box.add_widget(btn_box)
        return box

    def add_note(self, instance):
        """Переход к экрану добавления"""
        edit_screen = self.manager.get_screen('edit')
        edit_screen.note = None
        self.manager.current = 'edit'

    def edit_note(self, note):
        """Переход к экрану редактирования"""
        edit_screen = self.manager.get_screen('edit')
        edit_screen.note = note
        self.manager.current = 'edit'

    def delete_note(self, note):
        """Удаление заметки"""
        popup = Popup(title='Подтверждение',
                      content=Label(text='Удалить заметку?'),
                      size_hint=(0.8, 0.4))

        btn_box = BoxLayout(orientation='horizontal', spacing=10)
        btn_yes = Button(text='Да', background_color=(0.8, 0.2, 0.2, 1))
        btn_no = Button(text='Нет', background_color=(0.2, 0.6, 0.8, 1))

        btn_box.add_widget(btn_yes)
        btn_box.add_widget(btn_no)

        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='Удалить заметку?'))
        content.add_widget(btn_box)
        popup.content = content

        btn_yes.bind(on_press=lambda x: self.confirm_delete(note, popup))
        btn_no.bind(on_press=popup.dismiss)

        popup.open()

    def confirm_delete(self, note, popup):
        """Подтверждение удаления"""
        if self.app.storage_mode == 'sqlite':
            conn = sqlite3.connect(self.app.db_name)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM notes WHERE id = ?', (note['id'],))
            conn.commit()
            conn.close()
        else:
            filepath = os.path.join(self.app.notes_dir, f"{note['id']}.json")
            if os.path.exists(filepath):
                os.remove(filepath)

        popup.dismiss()
        self.load_notes()

    def go_to_search(self, instance):
        """Переход к экрану поиска"""
        self.manager.current = 'search'

    def toggle_storage(self, instance):
        """Переключение хранилища"""
        self.app.storage_mode = 'file' if self.app.storage_mode == 'sqlite' else 'sqlite'
        self.load_notes()


class NoteEditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = NotesApp.get_running_app()
        self.note = None

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Заголовок
        title = Label(text='Редактирование заметки', size_hint_y=0.1, font_size='20sp', bold=True)
        layout.add_widget(title)

        # Поле заголовка
        self.title_input = TextInput(hint_text='Заголовок', multiline=False, size_hint_y=0.1)
        layout.add_widget(self.title_input)

        # Поле содержимого
        self.content_input = TextInput(hint_text='Содержимое заметки...', size_hint_y=0.6)
        layout.add_widget(self.content_input)

        # Кнопки
        btn_box = BoxLayout(size_hint_y=0.2, spacing=10)

        btn_save = Button(text='Сохранить', background_color=(0.2, 0.7, 0.3, 1))
        btn_save.bind(on_press=self.save_note)
        btn_box.add_widget(btn_save)

        btn_cancel = Button(text='Отмена', background_color=(0.6, 0.6, 0.6, 1))
        btn_cancel.bind(on_press=self.cancel)
        btn_box.add_widget(btn_cancel)

        layout.add_widget(btn_box)
        self.add_widget(layout)

    def on_enter(self):
        """Загрузка данных заметки при входе"""
        if self.note:
            self.title_input.text = self.note['title']
            self.content_input.text = self.note['content']
        else:
            self.title_input.text = ''
            self.content_input.text = ''

    def save_note(self, instance):
        """Сохранение заметки"""
        title = self.title_input.text.strip()
        content = self.content_input.text.strip()

        if not title or not content:
            popup = Popup(title='Ошибка', content=Label(text='Заполните все поля!'), size_hint=(0.8, 0.3))
            popup.open()
            return

        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M')

        if self.app.storage_mode == 'sqlite':
            self.save_to_sqlite(title, content, date_str, time_str)
        else:
            self.save_to_file(title, content, date_str, time_str)

        self.manager.current = 'main'

    def save_to_sqlite(self, title, content, date, time):
        """Сохранение в SQLite"""
        conn = sqlite3.connect(self.app.db_name)
        cursor = conn.cursor()

        if self.note:
            cursor.execute('UPDATE notes SET title=?, content=?, date=?, time=? WHERE id=?',
                           (title, content, date, time, self.note['id']))
        else:
            cursor.execute('INSERT INTO notes (title, content, date, time) VALUES (?, ?, ?, ?)',
                           (title, content, date, time))

        conn.commit()
        conn.close()

    def save_to_file(self, title, content, date, time):
        """Сохранение в файл"""
        if self.note:
            note_id = self.note['id']
        else:
            note_id = datetime.now().strftime('%Y%m%d%H%M%S')

        note_data = {
            'title': title,
            'content': content,
            'date': date,
            'time': time
        }

        filepath = os.path.join(self.app.notes_dir, f"{note_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(note_data, f, ensure_ascii=False, indent=2)

    def cancel(self, instance):
        """Отмена редактирования"""
        self.manager.current = 'main'


class SearchScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = NotesApp.get_running_app()

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Заголовок
        title = Label(text='Поиск заметок', size_hint_y=0.1, font_size='20sp', bold=True)
        layout.add_widget(title)

        # Поле поиска
        self.search_input = TextInput(hint_text='Введите ключевые слова...', multiline=False, size_hint_y=0.1)
        layout.add_widget(self.search_input)

        # Кнопка поиска
        btn_search = Button(text='Искать', background_color=(0.8, 0.6, 0.2, 1), size_hint_y=0.1)
        btn_search.bind(on_press=self.perform_search)
        layout.add_widget(btn_search)

        # Результаты поиска
        self.scroll = ScrollView(size_hint=(1, 0.6))
        self.results_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.results_list.bind(minimum_height=self.results_list.setter('height'))
        self.scroll.add_widget(self.results_list)
        layout.add_widget(self.scroll)

        # Кнопка назад
        btn_back = Button(text='Назад', background_color=(0.6, 0.6, 0.6, 1), size_hint_y=0.1)
        btn_back.bind(on_press=self.go_back)
        layout.add_widget(btn_back)

        self.add_widget(layout)

    def perform_search(self, instance):
        """Выполнение поиска"""
        query = self.search_input.text.strip().lower()
        self.results_list.clear_widgets()

        if not query:
            self.results_list.add_widget(Label(text='Введите поисковый запрос', size_hint_y=None, height=40))
            return

        # Загрузка всех заметок
        if self.app.storage_mode == 'sqlite':
            notes = self.load_from_sqlite()
        else:
            notes = self.load_from_files()

        # Фильтрация
        results = []
        for note in notes:
            if query in note['title'].lower() or query in note['content'].lower():
                results.append(note)

        if not results:
            self.results_list.add_widget(Label(text='Ничего не найдено', size_hint_y=None, height=40))
            return

        # Отображение результатов
        for note in results:
            note_widget = self.create_result_widget(note)
            self.results_list.add_widget(note_widget)

    def load_from_sqlite(self):
        """Загрузка из SQLite"""
        conn = sqlite3.connect(self.app.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, content, date, time FROM notes')
        notes = cursor.fetchall()
        conn.close()
        return [{'id': n[0], 'title': n[1], 'content': n[2], 'date': n[3], 'time': n[4]} for n in notes]

    def load_from_files(self):
        """Загрузка из файлов"""
        notes = []
        if os.path.exists(self.app.notes_dir):
            for filename in os.listdir(self.app.notes_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.app.notes_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        note = json.load(f)
                        note['id'] = filename.replace('.json', '')
                        notes.append(note)
        return notes

    def create_result_widget(self, note):
        """Создание виджета результата"""
        box = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=5)

        header = BoxLayout(size_hint_y=0.3)
        title_label = Label(text=note['title'], bold=True, halign='left', size_hint_x=0.7)
        title_label.text_size = title_label.size
        header.add_widget(title_label)

        date_label = Label(text=f"{note['date']} {note['time']}", size_hint_x=0.3, font_size='12sp')
        header.add_widget(date_label)
        box.add_widget(header)

        content_label = Label(text=note['content'][:100] + ('...' if len(note['content']) > 100 else ''),
                              halign='left', size_hint_y=0.7)
        content_label.text_size = content_label.size
        box.add_widget(content_label)

        return box

    def go_back(self, instance):
        """Возврат на главный экран"""
        self.manager.current = 'main'


if __name__ == '__main__':
    NotesApp().run()
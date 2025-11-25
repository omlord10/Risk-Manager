import tkinter as tk
from tkinter import messagebox
from models import RiskNode
from storage import save_nodes, load_nodes
from report import generate_pdf, REPORTLAB_AVAILABLE
from ui import build_ui, _init_style

class RiskAnalyzerMagnitApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Риск-анализатор ПАО "МАГНИТ"')

        # Инициализация стиля
        _init_style(self)

        # Загрузка сохранённых узлов
        self.nodes = load_nodes()
        if not self.nodes:
            # Если данных нет — создаём корневой узел
            root_node = RiskNode(id=1, name='ПАО "МАГНИТ"')
            self.nodes[1] = root_node

        self.next_id = max(self.nodes.keys()) + 1
        self.selected_id = 1

        # Построение интерфейса
        build_ui(self)

        # --- Привязка клавиши Del ---
        self.root.bind("<Delete>", self._on_delete_key)

        # --- Функция, которая вызывается при нажатии Del ---

    def _on_delete_key(self, event=None):
        # Используем уже существующую функцию удаления из ui.py
        from ui import on_delete
        on_delete(self)

    def on_report(self):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror(
                "ReportLab не установлен",
                "Для генерации PDF установите пакет reportlab:\n\npip install reportlab"
            )
            return
        try:
            generate_pdf(list(self.nodes.values()))
            messagebox.showinfo("Готово", "Файл risk_report_magnit.pdf успешно создан.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
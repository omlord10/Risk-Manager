import tkinter as tk
from tkinter import messagebox
from models import RiskNode
from storage import save_nodes, load_nodes
from report import generate_pdf, REPORTLAB_AVAILABLE
from ui import build_ui, _init_style
from ui import (
    _refresh_tree,
    _recalc_parents_only,
    ui_on_duplicate,
    ui_on_move_up,
    ui_on_move_down,
    ui_on_toggle_expand,
    ui_on_undo,
    ui_on_redo,
    on_add,
    on_rename,
    on_delete,
    on_save_risk,
    on_report
)


class RiskAnalyzerMagnitApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.item_to_id: dict
        self.id_to_item: dict
        self.selected_id: int = 1
        self.nodes: dict
        self.next_id: int
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

        # Привязка хоткеев
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        # ----------------- Горячие клавиши -----------------

        # Управление узлами
        self.root.bind('<Return>', lambda e: on_save_risk(self))
        self.root.bind('<Control-d>', lambda e: ui_on_duplicate(self))
        self.root.bind('<Control-r>', lambda e: on_rename(self))
        self.root.bind('<Control-Shift-Up>', lambda e: ui_on_move_up(self))
        self.root.bind('<Control-Shift-Down>', lambda e: ui_on_move_down(self))
        self.root.bind('<Control-n>', lambda e: on_add(self))

        # Работа с деревом
        self.root.bind('<F2>', lambda e: on_rename(self))

        # Отчёты и анализ
        self.root.bind('<Control-p>', lambda e: on_report(self))
        self.root.bind('<Control-Shift-R>', lambda e: _recalc_parents_only(self))

        # UX и навигация
        self.root.bind('<Escape>', lambda e: self.tree.selection_remove(self.tree.selection()))
        self.root.bind('<Control-z>', lambda e: ui_on_undo(self))
        self.root.bind('<Control-y>', lambda e: ui_on_redo(self))

        # Delete → удаление узла
        self.root.bind('<Delete>', lambda e: on_delete(self))

        # F1 → справка
        self.root.bind('<F1>', lambda e: show_help())

    def _on_delete_key(self, event=None):
        # Используем уже существующую функцию удаления из ui.py
        from ui import on_delete
        on_delete(self)

    def ui_on_duplicate(app):
        """Дублируем выбранный узел вместе с детьми"""
        if app.selected_id is None: return
        old_node = app.nodes[app.selected_id]

        def duplicate_rec(node, parent_id):
            new_id = app.next_id
            app.next_id += 1
            new_node = RiskNode(id=new_id, name=node.name + " (копия)", parent_id=parent_id)
            app.nodes[new_id] = new_node
            if parent_id:
                app.nodes[parent_id].children.append(new_id)
            for cid in node.children:
                duplicate_rec(app.nodes[cid], new_id)

        duplicate_rec(old_node, old_node.parent_id)
        app._refresh_tree()
        save_nodes(app.nodes)

    def ui_on_toggle_expand(app):
        """Раскрыть/свернуть выбранный узел"""
        if app.selected_id is None: return
        item = app.id_to_item[app.selected_id]
        app.tree.item(item, open=not app.tree.item(item, "open"))

    def ui_on_move_up(app):
        """Перемещаем узел вверх среди братьев"""
        # реализовать логику с перестановкой app.nodes[parent].children

    def ui_on_move_down(app):
        """Перемещаем узел вниз среди братьев"""
        # аналогично

    def ui_on_search(app):
        """Открыть диалог поиска по имени узла"""
        # можно открыть simpledialog.askstring и затем выделить/раскрыть узел

    def on_report(app, sort_column=None, sort_order=None):
        try:
            nodes_list = list(app.nodes.values())
            # Сортировка перед генерацией PDF
            if sort_column:
                reverse = sort_order == "Убыванию"

                def get_key(n):
                    mapping = {
                        "#0": n.name.lower(),
                        "Объект": n.name.lower(),
                        "P": n.prob,
                        "Lmin": n.loss_min,
                        "Lmax": n.loss_max,
                        "ExpectedMin": (n.prob or 0.0) * (n.loss_min or 0.0),
                        "ExpectedMax": (n.prob or 0.0) * (n.loss_max or 0.0),
                        "Severity": n.severity,
                        "Risk": (n.prob or 0.0) * (n.severity or 1.0)
                    }
                    return mapping.get(sort_column, 0)

                nodes_list.sort(key=get_key, reverse=reverse)

            generate_pdf(nodes_list)
            messagebox.showinfo("Готово", "Файл risk_report_magnit.pdf успешно создан.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

def show_help():
    messagebox.showinfo(
        "Справка по программе",
        "Горячие клавиши и управление:\n\n"
        "Управление узлами:\n"
        "  - Enter        : Сохранить параметры узла\n"
        "  - F2             : Переименовать узел\n"
        "  - Delete      : Удалить узел\n"
        "  - Ctrl+D      : Дублировать узел\n"
        "  - Ctrl+Shift+Up/Down : Переместить узел вверх/вниз\n"
        "  - Ctrl+N      : Добавить новый узел\n\n"
        "Работа с деревом:\n"
        "  - Стрелки   : Навигация по дереву\n\n"
        "Отчёты и анализ:\n"
        "  - Ctrl+P      : Создать PDF отчёт\n"
        "  - Ctrl+Shift+R  : Пересчитать родителей\n\n"
        "Отмена/Повтор:\n"
        "  - Ctrl+Z      : Отмена действия\n"
        "  - Ctrl+Y      : Повтор действия"
    )

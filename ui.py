import tkinter as tk
from tkinter import ttk, messagebox
from models import RiskNode
from storage import save_nodes
from report import generate_pdf, REPORTLAB_AVAILABLE

# ----------------- Стили -----------------
def _init_style(app):
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    bg_root = "#fafafa"
    card_bg = "#ffffff"
    accent = "#e31b23"
    accent_hover = "#c7171b"
    text_main = "#111827"
    text_secondary = "#4b5563"
    border_color = "#e5e7eb"

    app.root.configure(bg=bg_root)

    style.configure("Card.TFrame", background=card_bg, relief="flat", borderwidth=1)
    style.configure("Main.TFrame", background=bg_root)
    style.configure("Title.TLabel", background=card_bg, foreground=text_main, font=("Segoe UI",14,"bold"))
    style.configure("Section.TLabel", background=card_bg, foreground=text_secondary, font=("Segoe UI",10,"bold"))
    style.configure("TLabel", background=card_bg, foreground=text_secondary, font=("Segoe UI",9))
    style.configure("TEntry", padding=4)
    style.configure("Accent.TButton", background=accent, foreground="white", font=("Segoe UI",9,"bold"), padding=6, borderwidth=0)
    style.map("Accent.TButton", background=[("active", accent_hover), ("pressed", accent_hover)])
    style.configure("Ghost.TButton", background=card_bg, foreground=accent, font=("Segoe UI",9), padding=5, borderwidth=1, relief="solid")
    style.map("Ghost.TButton", background=[("active", "#fff1f2")])
    style.configure("Danger.TButton", background="#ef4444", foreground="white", font=("Segoe UI",9,"bold"), padding=5, borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#dc2626")])
    style.configure("Treeview", background=card_bg, fieldbackground=card_bg, foreground=text_main, rowheight=22, bordercolor=border_color, borderwidth=1, font=("Segoe UI",9))
    style.configure("Treeview.Heading", background="#f3f4f6", foreground=text_secondary, font=("Segoe UI",9,"bold"))

# ----------------- Вспомогательные функции -----------------
def _refresh_tree(app):
    for item in app.tree.get_children():
        app.tree.delete(item)
    app.item_to_id.clear()
    app.id_to_item.clear()

    def insert_node_rec(node_id, parent_item=""):
        node = app.nodes[node_id]
        item = app.tree.insert(parent_item, "end", text=node.name,
            values=(f"{node.prob}",f"{node.loss_min}",f"{node.loss_max}","0.00","0.00",f"{node.severity}","0.00"))
        app.item_to_id[item] = node_id
        app.id_to_item[node_id] = item
        for cid in node.children:
            insert_node_rec(cid, item)
    insert_node_rec(1)
    _recalc_and_update_tree(app)
    _update_total_label(app)
    if app.selected_id in app.id_to_item:
        app.tree.selection_set(app.id_to_item[app.selected_id])

def _recalc_and_update_tree(app):
    def update_node_rec(node_id):
        node = app.nodes[node_id]
        lower = (node.prob or 0.0)*(node.loss_min or 0.0)
        upper = (node.prob or 0.0)*(node.loss_max or 0.0)
        risk = (node.prob or 0.0)*(node.severity or 1.0)
        item = app.id_to_item.get(node_id)
        if item:
            app.tree.item(item, values=(f"{node.prob:.3f}",f"{node.loss_min:.2f}",f"{node.loss_max:.2f}",f"{lower:.2f}",f"{upper:.2f}",f"{node.severity:.1f}",f"{risk:.2f}"))
        for cid in node.children:
            update_node_rec(cid)
    update_node_rec(1)

def _update_total_label(app):
    def calc_lower(node_id):
        node = app.nodes[node_id]
        return (node.prob or 0.0)*(node.loss_min or 0.0) + sum(calc_lower(cid) for cid in node.children)
    def calc_upper(node_id):
        node = app.nodes[node_id]
        return (node.prob or 0.0)*(node.loss_max or 0.0) + sum(calc_upper(cid) for cid in node.children)
    total_lower = calc_lower(1)
    total_upper = calc_upper(1)
    app.label_total.config(text=f"ΣLower группы: {total_lower:.2f} руб.\nΣUpper группы: {total_upper:.2f} руб.")

def _sync_inputs_with_selection(app):
    node = app.nodes[app.selected_id]
    app.entry_name.delete(0, tk.END)
    app.entry_name.insert(0, node.name)
    if app.selected_id == 1:
        for e in [app.entry_prob, app.entry_loss_min, app.entry_loss_max, app.entry_severity, app.btn_save_risk]:
            e.config(state="disabled")
    else:
        for e in [app.entry_prob, app.entry_loss_min, app.entry_loss_max, app.entry_severity, app.btn_save_risk]:
            e.config(state="normal")
        app.entry_prob.delete(0, tk.END)
        app.entry_prob.insert(0,str(node.prob))
        app.entry_loss_min.delete(0, tk.END)
        app.entry_loss_min.insert(0,str(node.loss_min))
        app.entry_loss_max.delete(0, tk.END)
        app.entry_loss_max.insert(0,str(node.loss_max))
        app.entry_severity.delete(0, tk.END)
        app.entry_severity.insert(0,str(node.severity))

# ----------------- Дерево -----------------
def _build_treeview(app):
    columns = ("P","Lmin","Lmax","Lower","Upper","Severity","Risk")
    app.tree = ttk.Treeview(app.right_frame, columns=columns, show="tree headings", height=20)
    for col in columns:
        app.tree.heading(col, text=col)
    app.tree.heading("#0", text="Объект")
    app.tree.column("#0", width=260, anchor="w")
    app.tree.column("P", width=60, anchor="center")
    app.tree.column("Lmin", width=80, anchor="e")
    app.tree.column("Lmax", width=80, anchor="e")
    app.tree.column("Lower", width=80, anchor="e")
    app.tree.column("Upper", width=80, anchor="e")
    app.tree.column("Severity", width=70, anchor="center")
    app.tree.column("Risk", width=70, anchor="e")
    app.tree.pack(fill="both", expand=True)

    app.item_to_id = {}
    app.id_to_item = {}

    _refresh_tree(app)


# ----------------- События / Обработчики -----------------
def on_select(app, event=None):
    selected = app.tree.selection()
    if not selected: return
    item = selected[0]
    node_id = app.item_to_id.get(item)
    if not node_id: return
    app.selected_id = node_id
    _sync_inputs_with_selection(app)

def recalc_tree_up(app, node_id):
    """Рекурсивно пересчитывает все узлы от выбранного до корня."""
    if node_id is None:
        return
    node = app.nodes[node_id]
    # если есть дети — пересчитываем текущий узел по детям
    if node.children:
        total_prob = 0.0
        total_loss_min = 0.0
        total_loss_max = 0.0
        total_severity = 0.0
        count = 0
        for cid in node.children:
            child = app.nodes[cid]
            total_prob += child.prob or 0.0
            total_loss_min += child.loss_min or 0.0
            total_loss_max += child.loss_max or 0.0
            total_severity += child.severity or 1.0
            count += 1
        if count > 0:
            node.prob = total_prob / count
            node.loss_min = total_loss_min / count
            node.loss_max = total_loss_max / count
            node.severity = total_severity / count
        else:
            node.prob = 0.0
            node.loss_min = 0.0
            node.loss_max = 0.0
            node.severity = 1.0
    # поднимаемся к родителю
    recalc_tree_up(app, node.parent_id)


def on_add(app):
    if app.selected_id is None:
        messagebox.showwarning("Нет выбора","Сначала выберите узел в дереве.")
        return
    name = app.entry_name.get().strip()
    if not name:
        messagebox.showwarning("Пустое имя","Введите название блока.")
        return

    # Создаём новый объект
    new_id = app.next_id
    app.next_id += 1
    new_node = RiskNode(id=new_id, name=name, parent_id=app.selected_id)
    app.nodes[new_id] = new_node
    app.nodes[app.selected_id].children.append(new_id)

    # Сразу пересчёт для родительского города
    recalc_tree_up(app, app.selected_id)

    # Обновляем дерево и сохраняем
    _refresh_tree(app)
    save_nodes(app.nodes)

def on_rename(app):
    if app.selected_id is None: return
    name = app.entry_name.get().strip()
    if not name:
        messagebox.showwarning("Пустое имя","Введите новое название.")
        return
    app.nodes[app.selected_id].name = name
    _refresh_tree(app)
    save_nodes(app.nodes)

def on_delete(app):
    if app.selected_id is None: return
    if app.selected_id == 1:
        messagebox.showinfo("Удаление запрещено","Нельзя удалить корневой узел группы.")
        return
    if not messagebox.askyesno("Подтверждение удаления","Удалить выбранный узел и все его дочерние элементы?"):
        return
    def delete_rec(nid):
        node = app.nodes[nid]
        for cid in list(node.children):
            delete_rec(cid)
        del app.nodes[nid]
    parent_id = app.nodes[app.selected_id].parent_id
    if parent_id:
        app.nodes[parent_id].children = [cid for cid in app.nodes[parent_id].children if cid != app.selected_id]
    delete_rec(app.selected_id)
    app.selected_id = 1
    _refresh_tree(app)
    _sync_inputs_with_selection(app)
    save_nodes(app.nodes)

def on_save_risk(app):
    if app.selected_id is None or app.selected_id == 1: return
    try: p = float(app.entry_prob.get().replace(",","."))
    except: p=0.0
    try: lmin = float(app.entry_loss_min.get().replace(",","."))
    except: lmin=0.0
    try: lmax = float(app.entry_loss_max.get().replace(",","."))
    except: lmax=0.0
    try: s = float(app.entry_severity.get().replace(",","."))
    except: s=1.0
    p = max(0.0,min(1.0,p))
    if lmax < lmin: lmin,lmax = lmax,lmin
    s = max(1.0,min(5.0,s))
    node = app.nodes[app.selected_id]
    node.prob = max(0.0,p)
    node.loss_min = max(0.0,lmin)
    node.loss_max = max(0.0,lmax)
    node.severity = s
    recalc_tree_up(app, app.selected_id)
    _recalc_and_update_tree(app)
    _update_total_label(app)
    save_nodes(app.nodes)

def on_report(app):
    try:
        generate_pdf(list(app.nodes.values()))
        messagebox.showinfo("Готово","Файл risk_report_magnit.pdf успешно создан.")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

# ----------------- Основной UI -----------------
def build_ui(app):
    # Основной фрейм
    main_frame = ttk.Frame(app.root, style="Main.TFrame")
    main_frame.pack(fill="both", expand=True, padx=16, pady=16)
    main_frame.columnconfigure(0, weight=0)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(0, weight=1)

    # Левая панель
    left_card = ttk.Frame(main_frame, style="Card.TFrame")
    left_card.grid(row=0, column=0, sticky="nsw", padx=(0,12))
    left_inner = ttk.Frame(left_card, style="Card.TFrame", padding=12)
    left_inner.pack(fill="both", expand=True)

    # Правая панель
    right_card = ttk.Frame(main_frame, style="Card.TFrame")
    right_card.grid(row=0, column=1, sticky="nsew", padx=(12,0))
    right_inner = ttk.Frame(right_card, style="Card.TFrame", padding=8)
    right_inner.pack(fill="both", expand=True)
    app.right_frame = right_inner

    # Заголовки
    ttk.Label(left_inner, text='Риск-анализатор ПАО "МАГНИТ"', style="Title.TLabel").pack(anchor="w", pady=(0,8))
    ttk.Label(left_inner, text="Управление структурой объектов", style="Section.TLabel").pack(anchor="w")

    # Поле названия узла
    app.entry_name = ttk.Entry(left_inner, width=30)
    app.entry_name.pack(fill="x", pady=(4,2))
    app.entry_name.insert(0, "Новый объект/система")

    # Кнопки добавить / переименовать
    struct_btn_row = ttk.Frame(left_inner, style="Card.TFrame")
    struct_btn_row.pack(fill="x", pady=(2,4))
    ttk.Button(struct_btn_row, text="Добавить", style="Accent.TButton", command=lambda: on_add(app)).pack(side="left", expand=True, fill="x", padx=(0,3))
    ttk.Button(struct_btn_row, text="Переименовать", style="Ghost.TButton", command=lambda: on_rename(app)).pack(side="left", expand=True, fill="x", padx=(3,0))

    # Кнопка удалить
    ttk.Button(left_inner, text="Удалить выбранный", style="Danger.TButton", command=lambda: on_delete(app)).pack(fill="x", pady=(2,6))

    # Раздел: параметры риска
    ttk.Separator(left_inner, orient="horizontal").pack(fill="x", pady=8)
    ttk.Label(left_inner, text="Параметры риска", style="Section.TLabel").pack(anchor="w")
    app.entry_prob = ttk.Entry(left_inner); app.entry_prob.pack(fill="x", pady=2); app.entry_prob.insert(0,"0")
    app.entry_loss_min = ttk.Entry(left_inner); app.entry_loss_min.pack(fill="x", pady=2); app.entry_loss_min.insert(0,"0")
    app.entry_loss_max = ttk.Entry(left_inner); app.entry_loss_max.pack(fill="x", pady=2); app.entry_loss_max.insert(0,"0")
    app.entry_severity = ttk.Entry(left_inner); app.entry_severity.pack(fill="x", pady=2); app.entry_severity.insert(0,"1")
    app.btn_save_risk = ttk.Button(left_inner, text="Сохранить параметры", style="Accent.TButton", command=lambda: on_save_risk(app))
    app.btn_save_risk.pack(fill="x", pady=(6,4))
    app.label_root_hint = ttk.Label(left_inner, text="Для корневого узла параметры риска не задаются", foreground="#9ca3af", background="#ffffff", wraplength=260)
    app.label_root_hint.pack(anchor="w", pady=(2,0))

    # Итоговая оценка
    ttk.Separator(left_inner, orient="horizontal").pack(fill="x", pady=8)
    ttk.Label(left_inner, text="Итоговая оценка группы Магнит", style="Section.TLabel").pack(anchor="w")
    app.label_total = ttk.Label(left_inner, text="ΣLower: 0.00 руб.\nΣUpper: 0.00 руб.", font=("Segoe UI",10,"bold"), background="#ffffff", foreground="#111827", wraplength=260)
    app.label_total.pack(anchor="w", pady=(4,4))

    # PDF
    ttk.Separator(left_inner, orient="horizontal").pack(fill="x", pady=8)
    ttk.Label(left_inner, text="Генерация отчёта", style="Section.TLabel").pack(anchor="w")
    ttk.Button(left_inner, text="Сделать отчёт (PDF)", style="Accent.TButton", command=lambda: on_report(app)).pack(fill="x", pady=(6,2))
    if not REPORTLAB_AVAILABLE:
        ttk.Label(left_inner, text="(для PDF установите пакет reportlab)", foreground="#dc2626", background="#ffffff", wraplength=260).pack(anchor="w", pady=(2,0))

    # Строим дерево
    _build_treeview(app)
    enable_tree_sorting(app.tree)

    # Синхронизация при выборе
    app.tree.bind("<<TreeviewSelect>>", lambda e: on_select(app))
    on_select(app)

# ----------------- Сортировка по колонкам Treeview -----------------
def enable_tree_sorting(tree):
    """Сортировка Treeview по колонкам с чередованием по убыванию/возрастанию, с сохранением иерархии."""
    sort_states = {col: False for col in tree["columns"]}  # False = сначала по убыванию

    def sort_column(col):
        reverse = sort_states[col]

        def sort_level(item_ids):
            # Сортируем элементы текущего уровня
            l = []
            for iid in item_ids:
                try:
                    v = float(tree.set(iid, col))
                except ValueError:
                    v = tree.set(iid, col)
                l.append((v, iid))
            l.sort(key=lambda t: t[0], reverse=reverse)

            # Переставляем элементы на текущем уровне
            for index, (_, iid) in enumerate(l):
                tree.move(iid, tree.parent(iid), index)
                # Рекурсивно сортируем детей
                sort_level(tree.get_children(iid))

        sort_level(tree.get_children(''))  # начинаем с корня
        sort_states[col] = not reverse  # меняем направление для следующего клика

    for col in tree["columns"]:
        tree.heading(col, command=lambda c=col: sort_column(c))

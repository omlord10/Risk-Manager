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

    # фон всего окна
    app.root.configure(bg=bg_root)

    # белая верхняя панель
    style.configure("TopPanel.TFrame", background=card_bg)

    # существующие стили
    style.configure("Card.TFrame", background=card_bg)
    style.configure("Main.TFrame", background=bg_root)
    style.configure("Title.TLabel", background=card_bg, foreground=text_main, font=("Segoe UI",14,"bold"))
    style.configure("Section.TLabel", background=card_bg, foreground=text_secondary, font=("Segoe UI",10,"bold"))
    style.configure("TLabel", background=card_bg, foreground=text_secondary, font=("Segoe UI",9))
    style.configure("TEntry", padding=4)

    style.configure("Accent.TButton", background=accent, foreground="white",
                    font=("Segoe UI",9,"bold"), padding=6, borderwidth=0)
    style.map("Accent.TButton", background=[("active", accent_hover)])

    style.configure("Ghost.TButton", background=card_bg, foreground=accent,
                    font=("Segoe UI",9), padding=5, borderwidth=1, relief="solid")
    style.map("Ghost.TButton", background=[("active", "#fff1f2")])

    style.configure("Danger.TButton", background="#ef4444", foreground="white",
                    font=("Segoe UI",9,"bold"), padding=5, borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#dc2626")])

    # дерево
    style.configure("Treeview", background=card_bg, fieldbackground=card_bg,
                    foreground=text_main, rowheight=22, bordercolor=border_color, borderwidth=1)
    style.configure("Treeview.Heading", background="#f3f4f6",
                    foreground=text_secondary, font=("Segoe UI",9,"bold"))


# ----------------- Вспомогательные функции -----------------
def _refresh_tree(app):
    # 1. Сохранить открытые узлы по node_id
    open_nodes = set()

    def collect(item):
        node_id = app.item_to_id.get(item)
        if node_id and app.tree.item(item, "open"):
            open_nodes.add(node_id)
        for c in app.tree.get_children(item):
            collect(c)

    for i in app.tree.get_children():
        collect(i)

    # 2. Сохранить выделение
    old_selection = app.tree.selection()
    old_selection_ids = [app.item_to_id.get(i) for i in old_selection if i in app.item_to_id]

    # 3. Очистить
    for item in app.tree.get_children():
        app.tree.delete(item)
    app.item_to_id.clear()
    app.id_to_item.clear()

    # 4. Вставка рекурсивно
    def insert(node_id, parent=""):
        node = app.nodes[node_id]
        item = app.tree.insert(
            parent, "end", text=node.name,
            values=(f"{node.prob:.3f}", f"{node.loss_min:.2f}", f"{node.loss_max:.2f}",
                    f"{(node.prob or 0.0)*(node.loss_min or 0.0):.2f}",
                    f"{(node.prob or 0.0)*(node.loss_max or 0.0):.2f}",
                    f"{node.severity:.1f}",
                    f"{(node.prob or 0.0)*(node.severity or 1.0):.2f}")
        )
        app.item_to_id[item] = node_id
        app.id_to_item[node_id] = item
        for cid in node.children:
            insert(cid, item)
        # восстанавливаем раскрытие по node_id
        if node_id in open_nodes:
            app.tree.item(item, open=True)

    insert(1)

    # 5. Восстановить выделение
    if old_selection_ids:
        new_selection = [app.id_to_item[nid] for nid in old_selection_ids if nid in app.id_to_item]
        try:
            app.tree.selection_set(new_selection)
        except Exception:
            pass

    # 6. Пересчёт и обновление итогов
    _recalc_and_update_tree(app)
    _update_total_label(app)

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
    # Считаем только листья
    def calc_lower(node_id):
        node = app.nodes[node_id]
        if not node.children:  # если нет детей — это лист
            return (node.prob or 0.0)*(node.loss_min or 0.0)
        return sum(calc_lower(cid) for cid in node.children)

    def calc_upper(node_id):
        node = app.nodes[node_id]
        if not node.children:
            return (node.prob or 0.0)*(node.loss_max or 0.0)
        return sum(calc_upper(cid) for cid in node.children)

    total_lower = calc_lower(1)
    total_upper = calc_upper(1)

    # Считаем города и улицы
    cities = sum(1 for cid in app.nodes[1].children)
    streets = sum(len(app.nodes[cid].children) for cid in app.nodes[1].children)

    app.label_total.config(text=(
        f"Ожидаемые мин. потери: {total_lower:.2f} руб.\n"
        f"Ожидаемые макс. потери: {total_upper:.2f} руб.\n"
        f"Городов: {cities}\n"
        f"Магазины (улицы): {streets}"
    ))

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
    columns = ("P", "Lmin", "Lmax", "ExpectedMin", "ExpectedMax", "Severity", "Risk")
    headers = {
        "P": "Вероятность",
        "Lmin": "Мин. потери",
        "Lmax": "Макс. потери",
        "ExpectedMin": "Ожидаемые мин. потери",
        "ExpectedMax": "Ожидаемые макс. потери",
        "Severity": "Вес",
        "Risk": "Риск"
    }

    app.tree = ttk.Treeview(app.right_frame, columns=columns, show="tree headings", height=20)

    for col in columns:
        app.tree.heading(col, text=headers[col])

    app.tree.heading("#0", text="Объект")
    app.tree.column("#0", width=260, anchor="w")
    app.tree.column("P", width=60, anchor="center")
    app.tree.column("Lmin", width=80, anchor="e")
    app.tree.column("Lmax", width=80, anchor="e")
    app.tree.column("ExpectedMin", width=120, anchor="e")
    app.tree.column("ExpectedMax", width=120, anchor="e")
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
    """Рекурсивно пересчитывает узлы от выбранного до корня по средним значениям детей."""
    if node_id is None:
        return
    node = app.nodes[node_id]

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

    # Рекурсивно поднимаемся к родителю
    if node.parent_id:
        recalc_tree_up(app, node.parent_id)

def on_add(app):
    if app.selected_id is None:
        messagebox.showwarning("Нет выбора","Сначала выберите узел в дереве.")
        return
    name = app.entry_name.get().strip()
    if not name:
        messagebox.showwarning("Пустое имя","Введите название блока.")
        return

    new_id = app.next_id
    app.next_id += 1
    new_node = RiskNode(id=new_id, name=name, parent_id=app.selected_id)
    app.nodes[new_id] = new_node
    app.nodes[app.selected_id].children.append(new_id)

    # Пересчёт родителя
    recalc_tree_up(app, app.selected_id)

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

    # После удаления сразу пересчитываем родителя
    if parent_id:
        recalc_tree_up(app, parent_id)

    app.selected_id = 1
    _refresh_tree(app)
    _sync_inputs_with_selection(app)
    save_nodes(app.nodes)

# ----------------- Кнопка "Обновить параметры" -----------------
def on_recalc(app):
    """Принудительно пересчитывает средние значения по всем родителям."""
    recalc_tree_up(app, 1)
    _refresh_tree(app)

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

UI_TO_KEY = {
    "Объект": "Объект",
    "Вероятность": "P",
    "Мин. потери": "Lmin",
    "Макс. потери": "Lmax",
    "Ожидаемый мин. потери": "ExpectedMin",
    "Ожидаемый макс. потери": "ExpectedMax",
    "Вес": "Severity",
    "Риск": "Risk"
}

def on_report(app, sort_column="Risk", sort_order="Убыванию"):
    try:
        nodes_list = list(app.nodes.values())

        sort_key = UI_TO_KEY.get(sort_column, "Risk")
        reverse = sort_order == "Убыванию"

        def get_key(n):
            mapping = {
                "Объект": n.name.lower(),
                "P": n.prob,
                "Lmin": n.loss_min,
                "Lmax": n.loss_max,
                "ExpectedMin": (n.prob or 0.0) * (n.loss_min or 0.0),
                "ExpectedMax": (n.prob or 0.0) * (n.loss_max or 0.0),
                "Severity": n.severity,
                "Risk": (n.prob or 0.0) * (n.severity or 1.0)
            }
            return mapping.get(sort_key, 0)

        nodes_list.sort(key=get_key, reverse=reverse)
        print("sort_column combobox:", sort_column)
        print("mapped key:", sort_key)
        print("sort_order:", sort_order)
        generate_pdf(nodes_list, sort_column=sort_column, sort_order=sort_order)
        messagebox.showinfo("Готово","Файл risk_report_magnit.pdf успешно создан.")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def build_ui(app):
    main_frame = ttk.Frame(app.root)
    main_frame.pack(fill="both", expand=True)
    main_frame.rowconfigure(1, weight=1)
    main_frame.columnconfigure(0, weight=1)

    # -------------------- ВЕРХНЯЯ ПАНЕЛЬ --------------------
    top_panel = ttk.Frame(main_frame, padding=12, style="TopPanel.TFrame")
    top_panel.grid(row=0, column=0, sticky="new")
    top_panel.columnconfigure((0,1,2,3), weight=1)  # 4 раздела горизонтально

    ttk.Label(top_panel, text='Риск-анализатор ПАО "МАГНИТ"', style="Title.TLabel")\
        .grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,8))

    # ----------- 1. Управление -----------
    frame_manage = ttk.Frame(top_panel, style="TopPanel.TFrame", padding=6)
    frame_manage.grid(row=1, column=0, sticky="nwe", padx=4)
    frame_manage.columnconfigure(0, weight=1)
    ttk.Label(frame_manage, text="Управление структурой объектов", style="Section.TLabel").grid(row=0, column=0, sticky="w")
    app.entry_name = ttk.Entry(frame_manage)
    app.entry_name.grid(row=1, column=0, sticky="we", pady=2)
    app.entry_name.insert(0, "Новый объект/система")
    ttk.Button(frame_manage, text="Добавить", style="Accent.TButton", command=lambda: on_add(app)).grid(row=2, column=0, sticky="we", pady=1)
    ttk.Button(frame_manage, text="Переименовать", style="Ghost.TButton", command=lambda: on_rename(app)).grid(row=3, column=0, sticky="we", pady=1)
    ttk.Button(frame_manage, text="Удалить выбранный", style="Danger.TButton", command=lambda: on_delete(app)).grid(row=4, column=0, sticky="we", pady=1)
    ttk.Button(frame_manage, text="Обновить параметры", style="Accent.TButton", command=lambda: on_recalc(app)).grid(row=5, column=0, sticky="we", pady=1)

    # ----------- 2. Параметры -----------
    frame_params = ttk.Frame(top_panel, style="TopPanel.TFrame", padding=6)
    frame_params.grid(row=1, column=1, sticky="nwe", padx=4)
    frame_params.columnconfigure(0, weight=1)
    ttk.Label(frame_params, text="Параметры риска", style="Section.TLabel").grid(row=0, column=0, sticky="w")
    app.entry_prob = ttk.Entry(frame_params); app.entry_prob.grid(row=1, column=0, sticky="we", pady=1)
    app.entry_loss_min = ttk.Entry(frame_params); app.entry_loss_min.grid(row=2, column=0, sticky="we", pady=1)
    app.entry_loss_max = ttk.Entry(frame_params); app.entry_loss_max.grid(row=3, column=0, sticky="we", pady=1)
    app.entry_severity = ttk.Entry(frame_params); app.entry_severity.grid(row=4, column=0, sticky="we", pady=1)
    app.btn_save_risk = ttk.Button(frame_params, text="Сохранить параметры", style="Accent.TButton", command=lambda: on_save_risk(app))
    app.btn_save_risk.grid(row=5, column=0, sticky="we", pady=2)
    app.label_root_hint = ttk.Label(frame_params, text="Для корневого узла параметры риска не задаются", foreground="#9ca3af", background="#ffffff", wraplength=150)
    app.label_root_hint.grid(row=6, column=0, sticky="w", pady=2)

    # ----------- 3. Генерация отчёта -----------
    frame_report = ttk.Frame(top_panel, style="TopPanel.TFrame", padding=6)
    frame_report.grid(row=1, column=2, sticky="nwe", padx=4)
    frame_report.columnconfigure(0, weight=1)

    ttk.Label(frame_report, text="Генерация отчёта", style="Section.TLabel").grid(row=0, column=0, sticky="w")

    # --- Выбор столбца и направления сортировки ---
    ttk.Label(frame_report, text="Сортировать PDF по:", font=("Segoe UI", 9, "bold"), background="#ffffff") \
        .grid(row=1, column=0, sticky="w", pady=(4, 0))

    columns_options = ["Объект", "Вероятность", "Мин. потери", "Макс. потери", "Ожидаемый мин. потери", "Ожидаемый макс. потери", "Вес", "Риск"]
    app.pdf_sort_column = tk.StringVar(value="Риск")  # по умолчанию "Risk"
    ttk.Combobox(frame_report, textvariable=app.pdf_sort_column, values=columns_options, state="readonly") \
        .grid(row=2, column=0, sticky="we", pady=1)

    app.pdf_sort_order = tk.StringVar(value="Убыванию")  # по умолчанию убывание
    ttk.Combobox(frame_report, textvariable=app.pdf_sort_order, values=["Возрастанию", "Убыванию"], state="readonly") \
        .grid(row=3, column=0, sticky="we", pady=1)

    # --- Кнопка генерации PDF с сортировкой ---
    ttk.Button(frame_report, text="Сделать PDF", style="Accent.TButton",
               command=lambda: on_report(app, sort_column=app.pdf_sort_column.get(), sort_order=app.pdf_sort_order.get())) \
        .grid(row=4, column=0, sticky="we", pady=2)

    # Проверка наличия reportlab
    if not REPORTLAB_AVAILABLE:
        ttk.Label(frame_report,
                  text="(для PDF установите reportlab: pip install reportlab)",
                  foreground="#dc2626",
                  background="#ffffff").grid(row=5, column=0, sticky="w", pady=(2, 6))

    # ----------- 4. Итоговая оценка -----------
    frame_total = ttk.Frame(top_panel, style="TopPanel.TFrame", padding=6)
    frame_total.grid(row=1, column=3, sticky="nwe", padx=4)
    frame_total.columnconfigure(0, weight=1)
    ttk.Label(frame_total, text="Итоговая оценка группы", style="Section.TLabel").grid(row=0, column=0, sticky="w")
    app.label_total = ttk.Label(frame_total, text="ΣLower: 0.00 руб.\nΣUpper: 0.00 руб.", font=("Segoe UI",10,"bold"), background="#ffffff", foreground="#111827")
    app.label_total.grid(row=1, column=0, sticky="w", pady=2)

    # -------------------- НИЖНЯЯ ПАНЕЛЬ (дерево) --------------------
    bottom_panel = ttk.Frame(main_frame, padding=10)
    bottom_panel.grid(row=1, column=0, sticky="nsew")
    app.right_frame = bottom_panel
    _build_treeview(app)
    enable_tree_sorting(app.tree)

    app.tree.bind("<<TreeviewSelect>>", lambda e: on_select(app))
    on_select(app)

def enable_tree_sorting(tree):
    """Сортировка Treeview по колонкам, включая #0 (Объект), с рекурсией и сохранением иерархии."""
    sort_states = {"#0": False}  # состояние сортировки для #0
    for col in tree["columns"]:
        sort_states[col] = False

    def sort_column(col):
        reverse = sort_states[col]

        def get_value(iid):
            if col == "#0":
                return tree.item(iid, "text").lower()
            else:
                val = tree.set(iid, col)
                try:
                    return float(val)
                except ValueError:
                    return val.lower()

        def sort_level(item_ids):
            arr = [(get_value(iid), iid) for iid in item_ids]
            arr.sort(key=lambda x: x[0], reverse=reverse)

            for index, (_, iid) in enumerate(arr):
                tree.move(iid, tree.parent(iid), index)
                sort_level(tree.get_children(iid))

        sort_level(tree.get_children(""))
        sort_states[col] = not reverse

    # Навесить колбэки
    tree.heading("#0", text="Объект", command=lambda: sort_column("#0"))
    for col in tree["columns"]:
        tree.heading(col, command=lambda c=col: sort_column(c))

def _recalc_parents_only(app):
    """Пересчитывает только родительские узлы от всех листьев вверх."""
    for node_id in app.nodes:
        recalc_tree_up(app, node_id)
    _refresh_tree(app)

def ui_on_duplicate(app):
    if app.selected_id is None or app.selected_id == 1:
        return
    import copy
    old_node = app.nodes[app.selected_id]

    def duplicate_node(node_id, parent_id):
        nonlocal app
        old = app.nodes[node_id]
        new_id = app.next_id
        app.next_id += 1
        new_node = copy.deepcopy(old)
        new_node.id = new_id
        new_node.parent_id = parent_id
        new_node.children = []
        app.nodes[new_id] = new_node

        if parent_id:
            app.nodes[parent_id].children.append(new_id)

        for cid in old.children:
            duplicate_node(cid, new_id)

        return new_id

    new_root_id = duplicate_node(app.selected_id, app.nodes[app.selected_id].parent_id)
    _refresh_tree(app)

def ui_on_move_up(app):
    if app.selected_id is None or app.selected_id == 1:
        return
    node = app.nodes[app.selected_id]
    parent = app.nodes.get(node.parent_id)
    if not parent:
        return
    idx = parent.children.index(node.id)
    if idx > 0:
        parent.children[idx], parent.children[idx-1] = parent.children[idx-1], parent.children[idx]
        _refresh_tree(app)

def ui_on_move_down(app):
    if app.selected_id is None or app.selected_id == 1:
        return
    node = app.nodes[app.selected_id]
    parent = app.nodes.get(node.parent_id)
    if not parent:
        return
    idx = parent.children.index(node.id)
    if idx < len(parent.children) - 1:
        parent.children[idx], parent.children[idx+1] = parent.children[idx+1], parent.children[idx]
        _refresh_tree(app)

def ui_on_toggle_expand(app):
    selected = app.tree.selection()
    if not selected:
        return
    for item in selected:
        is_open = app.tree.item(item, "open")
        app.tree.item(item, open=not is_open)

def ui_on_search(app):
    query = app.entry_name.get().strip().lower()
    if not query:
        return
    for item, node_id in app.item_to_id.items():
        node = app.nodes[node_id]
        if query in node.name.lower():
            app.tree.selection_set(item)
            app.tree.see(item)
            app.selected_id = node_id
            _sync_inputs_with_selection(app)
            break

def ui_on_undo(app):
    # Заглушка
    print("Undo not implemented yet")

def ui_on_redo(app):
    # Заглушка
    print("Redo not implemented yet")

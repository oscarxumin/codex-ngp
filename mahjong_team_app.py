#!/usr/bin/env python3
import itertools
import json
import os
import uuid
from datetime import date, datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "mahjong_data.json")


def today_text():
    return date.today().isoformat()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def empty_data():
    return {
        "customers": [],
        "custom_fields": ["牌技", "常来时段", "备注标签"],
        "signups": {},
        "created_at": now_text(),
        "updated_at": now_text(),
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return empty_data()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    base = empty_data()
    base.update(data)
    base.setdefault("customers", [])
    base.setdefault("custom_fields", [])
    base.setdefault("signups", {})
    return base


def save_data(data):
    data["updated_at"] = now_text()
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


class ScrollFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._fit_width)

    def _fit_width(self, event):
        self.canvas.itemconfig(self.window, width=event.width)


class CustomerDialog(tk.Toplevel):
    def __init__(self, master, data, customer=None):
        super().__init__(master)
        self.title("客户资料")
        self.resizable(False, False)
        self.data = data
        self.customer = customer
        self.result = None
        self.conflict_vars = {}
        self.attr_vars = {}

        self.name_var = tk.StringVar(value=(customer or {}).get("name", ""))
        self.phone_var = tk.StringVar(value=(customer or {}).get("phone", ""))
        self.available_var = tk.BooleanVar(value=(customer or {}).get("available", True))
        self.notes_text = None

        root = ttk.Frame(self, padding=16)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="姓名").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.name_var, width=32).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(root, text="电话/微信").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.phone_var, width=32).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(root, text="默认可报名", variable=self.available_var).grid(
            row=2, column=1, sticky="w", pady=4
        )

        attrs = (customer or {}).get("attrs", {})
        row = 3
        for field in self.data["custom_fields"]:
            ttk.Label(root, text=field).grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=attrs.get(field, ""))
            self.attr_vars[field] = var
            ttk.Entry(root, textvariable=var, width=32).grid(row=row, column=1, sticky="ew", pady=4)
            row += 1

        ttk.Label(root, text="备注").grid(row=row, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(root, width=34, height=4)
        self.notes_text.insert("1.0", (customer or {}).get("notes", ""))
        self.notes_text.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ttk.Label(root, text="不能同桌").grid(row=row, column=0, sticky="nw", pady=4)
        conflict_box = ttk.Frame(root)
        conflict_box.grid(row=row, column=1, sticky="ew", pady=4)
        current_id = (customer or {}).get("id")
        current_conflicts = set((customer or {}).get("conflicts", []))
        shown = 0
        for other in sorted(self.data["customers"], key=lambda item: item.get("name", "")):
            if other.get("id") == current_id:
                continue
            var = tk.BooleanVar(value=other.get("id") in current_conflicts)
            self.conflict_vars[other["id"]] = var
            ttk.Checkbutton(conflict_box, text=other.get("name", "未命名"), variable=var).grid(
                row=shown // 2, column=shown % 2, sticky="w", padx=(0, 14), pady=2
            )
            shown += 1
        if shown == 0:
            ttk.Label(conflict_box, text="暂无其他客户").grid(row=0, column=0, sticky="w")
        row += 1

        buttons = ttk.Frame(root)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="取消", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="保存", command=self.save).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(master)
        self.grab_set()
        self.wait_visibility()
        self.focus()

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("缺少姓名", "请先填写客户姓名。", parent=self)
            return
        item = dict(self.customer or {})
        item["id"] = item.get("id") or str(uuid.uuid4())
        item["name"] = name
        item["phone"] = self.phone_var.get().strip()
        item["available"] = self.available_var.get()
        item["notes"] = self.notes_text.get("1.0", "end").strip()
        item["attrs"] = {field: var.get().strip() for field, var in self.attr_vars.items()}
        item["conflicts"] = [
            customer_id for customer_id, var in self.conflict_vars.items() if var.get()
        ]
        item["updated_at"] = now_text()
        item.setdefault("created_at", now_text())
        self.result = item
        self.destroy()


class MahjongTeamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("新天地棋牌组队系统")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.data = load_data()
        self.selected_customer_id = None
        self.current_date_var = tk.StringVar(value=today_text())
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.customer_list = None
        self.signup_list = None
        self.team_text = None
        self.detail_vars = {}

        self._setup_style()
        self._build_ui()
        self.refresh_all()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f7f7f5")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f7f7f5", foreground="#202124")
        style.configure("Panel.TLabel", background="#ffffff", foreground="#202124")
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"), background="#f7f7f5")
        style.configure("Section.TLabel", font=("Helvetica", 12, "bold"), background="#ffffff")
        style.configure("TButton", padding=(10, 6))
        style.configure("Accent.TButton", padding=(12, 7))
        style.configure("Treeview", rowheight=28, font=("Helvetica", 12))
        style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

    def _build_ui(self):
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="新天地棋牌组队系统", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status_var).grid(row=0, column=1, sticky="e")

        tabs = ttk.Notebook(main)
        tabs.grid(row=1, column=0, sticky="nsew")
        self.library_tab = ttk.Frame(tabs, padding=12)
        self.signup_tab = ttk.Frame(tabs, padding=12)
        self.team_tab = ttk.Frame(tabs, padding=12)
        tabs.add(self.library_tab, text="客户总库")
        tabs.add(self.signup_tab, text="今日报名名单")
        tabs.add(self.team_tab, text="自动组队")

        self._build_library_tab()
        self._build_signup_tab()
        self._build_team_tab()

    def _build_library_tab(self):
        tab = self.library_tab
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="搜索").pack(side="left")
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=24)
        search.pack(side="left", padx=(8, 10))
        search.bind("<KeyRelease>", lambda _event: self.refresh_customer_list())
        ttk.Button(toolbar, text="新增客户", command=self.add_customer, style="Accent.TButton").pack(side="left")
        ttk.Button(toolbar, text="编辑客户", command=self.edit_customer).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="删除客户", command=self.delete_customer).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="自定义属性", command=self.manage_fields).pack(side="left", padx=(8, 0))

        columns = ("name", "phone", "available", "attrs")
        self.customer_list = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        self.customer_list.heading("name", text="姓名")
        self.customer_list.heading("phone", text="电话/微信")
        self.customer_list.heading("available", text="默认状态")
        self.customer_list.heading("attrs", text="自定义属性")
        self.customer_list.column("name", width=120)
        self.customer_list.column("phone", width=150)
        self.customer_list.column("available", width=90)
        self.customer_list.column("attrs", width=360)
        self.customer_list.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.customer_list.bind("<<TreeviewSelect>>", self.on_customer_select)
        self.customer_list.bind("<Double-1>", lambda _event: self.edit_customer())

        detail = ttk.Frame(tab, style="Panel.TFrame", padding=14)
        detail.grid(row=1, column=1, sticky="nsew")
        detail.columnconfigure(1, weight=1)
        ttk.Label(detail, text="客户详情", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        labels = [
            ("name", "姓名"),
            ("phone", "电话/微信"),
            ("available", "默认状态"),
            ("conflicts", "不能同桌"),
            ("attrs", "属性"),
            ("notes", "备注"),
        ]
        for row, (key, label) in enumerate(labels, start=1):
            ttk.Label(detail, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="nw", pady=5)
            var = tk.StringVar(value="-")
            self.detail_vars[key] = var
            ttk.Label(detail, textvariable=var, style="Panel.TLabel", wraplength=330).grid(
                row=row, column=1, sticky="ew", pady=5
            )

    def _build_signup_tab(self):
        tab = self.signup_tab
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="报名日期").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.current_date_var, width=14).pack(side="left", padx=(8, 8))
        ttk.Button(toolbar, text="切换日期", command=self.refresh_all).pack(side="left")
        ttk.Button(toolbar, text="使用今天", command=self.set_today).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="把默认可报名客户加入当天", command=self.add_available_to_signup).pack(side="left", padx=(8, 0))

        left = ttk.Frame(tab, style="Panel.TFrame", padding=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="客户总库", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.available_list = ttk.Treeview(left, columns=("name", "phone"), show="headings", selectmode="extended")
        self.available_list.heading("name", text="姓名")
        self.available_list.heading("phone", text="电话/微信")
        self.available_list.column("name", width=150)
        self.available_list.column("phone", width=180)
        self.available_list.grid(row=1, column=0, sticky="nsew")
        ttk.Button(left, text="加入当天报名名单", command=self.add_selected_to_signup).grid(
            row=2, column=0, sticky="ew", pady=(10, 0)
        )

        right = ttk.Frame(tab, style="Panel.TFrame", padding=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="当天报名名单", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.signup_list = ttk.Treeview(right, columns=("name", "phone", "conflicts"), show="headings", selectmode="extended")
        self.signup_list.heading("name", text="姓名")
        self.signup_list.heading("phone", text="电话/微信")
        self.signup_list.heading("conflicts", text="冲突提醒")
        self.signup_list.column("name", width=140)
        self.signup_list.column("phone", width=160)
        self.signup_list.column("conflicts", width=220)
        self.signup_list.grid(row=1, column=0, sticky="nsew")
        actions = ttk.Frame(right, style="Panel.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="从名单移除", command=self.remove_selected_from_signup).pack(side="left")
        ttk.Button(actions, text="清空当天名单", command=self.clear_signup).pack(side="left", padx=(8, 0))

    def _build_team_tab(self):
        tab = self.team_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="组队日期").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.current_date_var, width=14).pack(side="left", padx=(8, 8))
        ttk.Button(toolbar, text="刷新", command=self.refresh_all).pack(side="left")
        ttk.Button(toolbar, text="自动四人组队", command=self.generate_teams, style="Accent.TButton").pack(side="left", padx=(8, 0))

        frame = ttk.Frame(tab, style="Panel.TFrame", padding=12)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="组队结果", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.team_text = tk.Text(frame, font=("Menlo", 13), wrap="word", height=20, bg="#ffffff", relief="flat")
        self.team_text.grid(row=1, column=0, sticky="nsew")

    def customers_by_id(self):
        return {item["id"]: item for item in self.data["customers"]}

    def current_signup_ids(self):
        day = self.current_date_var.get().strip() or today_text()
        self.current_date_var.set(day)
        self.data["signups"].setdefault(day, [])
        return self.data["signups"][day]

    def refresh_all(self):
        self.refresh_customer_list()
        self.refresh_signup_lists()
        self.refresh_detail()
        day = self.current_date_var.get().strip() or today_text()
        count = len(self.data["signups"].get(day, []))
        self.status_var.set(f"{day} 已报名 {count} 人，客户总库 {len(self.data['customers'])} 人")

    def refresh_customer_list(self):
        query = self.search_var.get().strip().lower()
        for row in self.customer_list.get_children():
            self.customer_list.delete(row)
        for customer in sorted(self.data["customers"], key=lambda item: item.get("name", "")):
            text = " ".join(
                [customer.get("name", ""), customer.get("phone", "")]
                + list(customer.get("attrs", {}).values())
            ).lower()
            if query and query not in text:
                continue
            attrs = "；".join(
                f"{key}:{value}" for key, value in customer.get("attrs", {}).items() if value
            )
            self.customer_list.insert(
                "",
                "end",
                iid=customer["id"],
                values=(
                    customer.get("name", ""),
                    customer.get("phone", ""),
                    "可报名" if customer.get("available", True) else "暂停",
                    attrs,
                ),
            )

    def refresh_signup_lists(self):
        by_id = self.customers_by_id()
        signup_ids = set(self.current_signup_ids())
        for tree in (self.available_list, self.signup_list):
            for row in tree.get_children():
                tree.delete(row)

        for customer in sorted(self.data["customers"], key=lambda item: item.get("name", "")):
            if customer["id"] not in signup_ids:
                self.available_list.insert(
                    "", "end", iid=customer["id"], values=(customer.get("name", ""), customer.get("phone", ""))
                )

        for customer_id in self.current_signup_ids():
            customer = by_id.get(customer_id)
            if not customer:
                continue
            conflicts = [
                by_id[other_id].get("name", "")
                for other_id in customer.get("conflicts", [])
                if other_id in signup_ids and other_id in by_id
            ]
            self.signup_list.insert(
                "",
                "end",
                iid=customer_id,
                values=(customer.get("name", ""), customer.get("phone", ""), "、".join(conflicts) or "-"),
            )

    def refresh_detail(self):
        by_id = self.customers_by_id()
        customer = by_id.get(self.selected_customer_id)
        if not customer:
            for var in self.detail_vars.values():
                var.set("-")
            return
        self.detail_vars["name"].set(customer.get("name", "-"))
        self.detail_vars["phone"].set(customer.get("phone", "-") or "-")
        self.detail_vars["available"].set("默认可报名" if customer.get("available", True) else "暂停报名")
        conflict_names = [
            by_id[item].get("name", "")
            for item in customer.get("conflicts", [])
            if item in by_id
        ]
        self.detail_vars["conflicts"].set("、".join(conflict_names) or "-")
        attrs = "；".join(
            f"{key}: {value}" for key, value in customer.get("attrs", {}).items() if value
        )
        self.detail_vars["attrs"].set(attrs or "-")
        self.detail_vars["notes"].set(customer.get("notes", "") or "-")

    def on_customer_select(self, _event=None):
        selected = self.customer_list.selection()
        self.selected_customer_id = selected[0] if selected else None
        self.refresh_detail()

    def add_customer(self):
        dialog = CustomerDialog(self, self.data)
        self.wait_window(dialog)
        if not dialog.result:
            return
        self.data["customers"].append(dialog.result)
        self.sync_conflicts(dialog.result)
        save_data(self.data)
        self.refresh_all()

    def edit_customer(self):
        selected = self.customer_list.selection()
        if selected:
            self.selected_customer_id = selected[0]
        if not self.selected_customer_id:
            messagebox.showinfo("请选择客户", "请先在客户总库里选中一个客户。")
            return
        customer = self.customers_by_id().get(self.selected_customer_id)
        if not customer:
            return
        dialog = CustomerDialog(self, self.data, customer)
        self.wait_window(dialog)
        if not dialog.result:
            return
        for index, item in enumerate(self.data["customers"]):
            if item["id"] == dialog.result["id"]:
                self.data["customers"][index] = dialog.result
                break
        self.sync_conflicts(dialog.result)
        save_data(self.data)
        self.refresh_all()

    def delete_customer(self):
        selected = self.customer_list.selection()
        if selected:
            self.selected_customer_id = selected[0]
        if not self.selected_customer_id:
            messagebox.showinfo("请选择客户", "请先选择要删除的客户。")
            return
        by_id = self.customers_by_id()
        customer = by_id.get(self.selected_customer_id)
        if not customer:
            return
        if not messagebox.askyesno("确认删除", f"确定删除客户“{customer.get('name', '')}”吗？"):
            return
        delete_id = self.selected_customer_id
        self.data["customers"] = [item for item in self.data["customers"] if item["id"] != delete_id]
        for item in self.data["customers"]:
            item["conflicts"] = [cid for cid in item.get("conflicts", []) if cid != delete_id]
        for day, ids in self.data["signups"].items():
            self.data["signups"][day] = [cid for cid in ids if cid != delete_id]
        self.selected_customer_id = None
        save_data(self.data)
        self.refresh_all()

    def manage_fields(self):
        current = "\n".join(self.data["custom_fields"])
        text = simpledialog.askstring(
            "自定义属性",
            "每行一个属性，例如：牌技、常来时段、消费习惯。",
            initialvalue=current,
            parent=self,
        )
        if text is None:
            return
        fields = []
        for line in text.splitlines():
            field = line.strip()
            if field and field not in fields:
                fields.append(field)
        old_fields = set(self.data["custom_fields"])
        self.data["custom_fields"] = fields
        for customer in self.data["customers"]:
            attrs = customer.setdefault("attrs", {})
            for field in fields:
                attrs.setdefault(field, "")
            for field in list(attrs.keys()):
                if field not in fields and field in old_fields:
                    attrs.pop(field, None)
        save_data(self.data)
        self.refresh_all()
        messagebox.showinfo("已保存", "自定义属性已更新。新属性会出现在客户编辑窗口里。")

    def sync_conflicts(self, customer):
        customer_id = customer["id"]
        selected = set(customer.get("conflicts", []))
        for other in self.data["customers"]:
            if other["id"] == customer_id:
                continue
            conflicts = set(other.get("conflicts", []))
            if other["id"] in selected:
                conflicts.add(customer_id)
            else:
                conflicts.discard(customer_id)
            other["conflicts"] = sorted(conflicts)

    def set_today(self):
        self.current_date_var.set(today_text())
        self.refresh_all()

    def add_selected_to_signup(self):
        selected = self.available_list.selection()
        if not selected:
            messagebox.showinfo("请选择客户", "请先从客户总库里选择要加入当天名单的人。")
            return
        signup_ids = self.current_signup_ids()
        for customer_id in selected:
            if customer_id not in signup_ids:
                signup_ids.append(customer_id)
        save_data(self.data)
        self.refresh_all()

    def add_available_to_signup(self):
        signup_ids = self.current_signup_ids()
        for customer in self.data["customers"]:
            if customer.get("available", True) and customer["id"] not in signup_ids:
                signup_ids.append(customer["id"])
        save_data(self.data)
        self.refresh_all()

    def remove_selected_from_signup(self):
        selected = set(self.signup_list.selection())
        if not selected:
            messagebox.showinfo("请选择客户", "请先从当天报名名单里选择要移除的人。")
            return
        signup_ids = self.current_signup_ids()
        self.data["signups"][self.current_date_var.get().strip()] = [
            customer_id for customer_id in signup_ids if customer_id not in selected
        ]
        save_data(self.data)
        self.refresh_all()

    def clear_signup(self):
        day = self.current_date_var.get().strip() or today_text()
        if not messagebox.askyesno("确认清空", f"确定清空 {day} 的报名名单吗？"):
            return
        self.data["signups"][day] = []
        save_data(self.data)
        self.refresh_all()

    def has_conflict(self, customer_a, customer_b):
        return (
            customer_b["id"] in customer_a.get("conflicts", [])
            or customer_a["id"] in customer_b.get("conflicts", [])
        )

    def valid_group(self, group):
        for a, b in itertools.combinations(group, 2):
            if self.has_conflict(a, b):
                return False
        return True

    def score_group(self, group):
        score = 0
        for customer in group:
            attrs = customer.get("attrs", {})
            if attrs.get("牌技"):
                score += 1
            if attrs.get("常来时段"):
                score += 1
        return score

    def generate_teams(self):
        by_id = self.customers_by_id()
        signup_ids = [cid for cid in self.current_signup_ids() if cid in by_id]
        people = [by_id[cid] for cid in signup_ids]
        if len(people) < 4:
            messagebox.showinfo("人数不足", "当天报名人数少于 4 人，暂时不能组成一桌。")
            return

        groups, leftovers = self.make_groups(people)
        day = self.current_date_var.get().strip() or today_text()
        lines = [f"{day} 自动组队结果", "=" * 28, ""]
        if groups:
            for index, group in enumerate(groups, start=1):
                lines.append(f"第 {index} 桌")
                for customer in group:
                    attrs = "；".join(
                        f"{key}:{value}" for key, value in customer.get("attrs", {}).items() if value
                    )
                    phone = customer.get("phone", "")
                    detail = " / ".join(part for part in [phone, attrs] if part)
                    lines.append(f"  - {customer.get('name', '')}{'（' + detail + '）' if detail else ''}")
                lines.append("")
        else:
            lines.append("没有找到不冲突的四人组合。")
            lines.append("")

        if leftovers:
            lines.append("未成桌")
            for customer in leftovers:
                conflict_names = [
                    by_id[cid].get("name", "")
                    for cid in customer.get("conflicts", [])
                    if cid in signup_ids and cid in by_id
                ]
                note = f"；冲突：{'、'.join(conflict_names)}" if conflict_names else ""
                lines.append(f"  - {customer.get('name', '')}{note}")
            lines.append("")

        lines.append("说明：系统只从当天报名名单组队；任意两人存在“不能同桌”关系时不会分到同一桌。")
        self.team_text.delete("1.0", "end")
        self.team_text.insert("1.0", "\n".join(lines))
        self.refresh_all()

    def make_groups(self, people):
        remaining = list(people)
        groups = []
        while len(remaining) >= 4:
            candidates = [combo for combo in itertools.combinations(remaining, 4) if self.valid_group(combo)]
            if not candidates:
                break
            best = max(candidates, key=self.score_group)
            groups.append(list(best))
            chosen_ids = {item["id"] for item in best}
            remaining = [item for item in remaining if item["id"] not in chosen_ids]
        return groups, remaining


if __name__ == "__main__":
    app = MahjongTeamApp()
    app.mainloop()

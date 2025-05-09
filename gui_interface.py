"""
Interface graphique utilisateur en français pour le gestionnaire de stock (Refonte)
Intègre l'authentification, les statistiques, les sauvegardes et les notifications.
"""

from notification_manager import NotificationManager
from backup_manager import BackupManager
from stats_manager import StatsManager
from auth_manager import AuthManager
# Sera adapté ou moins utilisé directement par l'UI
from stock_functions import StockManager
from database_design import DatabaseManager
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, Menu
import os
import sys
from datetime import datetime
import pandas as pd
from tkinter import font as tkfont
from PIL import Image, ImageTk

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LoginDialog(simpledialog.Dialog):
    """Boîte de dialogue pour la connexion de l'utilisateur."""

    def __init__(self, parent, title="Connexion"):
        self.username_entry = None
        self.pin_entry = None
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Nom d'utilisateur:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_entry = ttk.Entry(master, width=25)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="Code PIN:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.pin_entry = ttk.Entry(master, show="*", width=25)
        self.pin_entry.grid(row=1, column=1, padx=5, pady=5)

        self.username_entry.focus_set()
        return self.username_entry  # initial focus

    def apply(self):
        username = self.username_entry.get()
        pin = self.pin_entry.get()
        if username and pin:
            self.result = (username, pin)
        else:
            self.result = None


class ModernStockManagerApp:
    """Application de gestion de stock refondue avec interface graphique moderne."""

    def __init__(self, root):
        self.root = root
        # Utilise le chemin par défaut "data/stock_database.db"
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        # S'assure que toutes les tables, y compris utilisateurs, sont créées
        self.db_manager.create_tables()
        self.db_manager.migrate_old_database()  # Applique les migrations si nécessaire

        self.auth_manager = AuthManager(self.db_manager)
        # StockManager aura besoin de l'auth_manager pour l'id_utilisateur
        self.stock_logic = StockManager(self.db_manager, self.auth_manager)
        self.stats_manager = StatsManager(self.db_manager)
        self.backup_manager = BackupManager(self.db_manager.db_file)
        self.notification_manager = NotificationManager(self.db_manager)

        self.current_user_label = None
        self.notifications_area = None  # Pour afficher les notifications

        if not self.perform_login():
            self.root.destroy()
            return

        self.setup_main_window()
        self.check_initial_notifications()
        self.schedule_periodic_checks()

    def search_articles(self):
        """Recherche des articles selon le terme entré dans la barre de recherche"""
        search_term = self.search_var.get().strip()
        if not search_term:
            # Si la recherche est vide, afficher tous les articles
            self.load_articles()
            self.update_status("Affichage de tous les articles.")
            return

        # Vider la liste actuelle
        for i in self.article_tree.get_children():
            self.article_tree.delete(i)

        # Effectuer la recherche
        articles = self.stock_logic.search_articles(search_term)

        # Afficher les résultats
        if articles:
            for article in articles:
                values = (
                    article.get('reference', ''),
                    article.get('description', ''),
                    article.get('quantite', 0),
                    article.get('quantite_minimale', 0),
                    article.get('position', '')
                )
                tag = 'low_stock' if article.get('quantite', 0) < article.get(
                    'quantite_minimale', 0) else 'normal_stock'
                self.article_tree.insert(
                    "", tk.END, values=values, tags=(tag,))

            self.update_status(
                f"{len(articles)} article(s) trouvé(s) pour '{search_term}'.")
        else:
            self.update_status(f"Aucun article trouvé pour '{search_term}'.")

    def reset_search(self):
        """Réinitialise la recherche et affiche tous les articles"""
        self.search_var.set("")
        self.load_articles()
        self.update_status("Recherche réinitialisée.")

    def perform_login(self):
        """Affiche la boîte de dialogue de connexion et gère la tentative de connexion."""
        # Vérifier si un utilisateur admin existe, sinon en créer un par défaut
        if not self.db_manager.get_user_by_username("admin"):
            self.db_manager.add_user("admin", "admin123", "admin")
            messagebox.showinfo(
                "Configuration initiale", "Un utilisateur 'admin' avec le PIN 'admin123' a été créé. Veuillez le changer.")

        login_attempt = 0
        max_attempts = 3
        while login_attempt < max_attempts:
            dialog = LoginDialog(self.root)
            if dialog.result:
                username, pin = dialog.result
                if self.auth_manager.login(username, pin):
                    return True
                else:
                    messagebox.showerror(
                        "Échec de la connexion", f"Nom d'utilisateur ou PIN incorrect. Tentatives restantes: {max_attempts - login_attempt - 1}")
                    login_attempt += 1
            else:  # L'utilisateur a fermé la boîte de dialogue
                return False
        messagebox.showerror("Échec de la connexion",
                             "Nombre maximal de tentatives atteint.")
        return False

    def setup_main_window(self):
        """Configure la fenêtre principale de l'application après une connexion réussie."""
        self.root.title(
            f"Gestionnaire de Stock Pro - Swisspro (Utilisateur: {self.auth_manager.get_current_user()['username']})")
        self.root.geometry("1366x768")  # Taille légèrement augmentée
        self.root.minsize(1100, 650)

        self.colors = {
            'primary': '#1F618D',    # Bleu foncé
            'secondary': '#5DADE2',  # Bleu clair
            'accent': '#E74C3C',     # Rouge
            'background': '#F4F6F7',  # Gris clair
            'text': '#212F3C',       # Texte sombre
            'success': '#2ECC71',    # Vert
            'warning': '#F39C12',    # Orange
            'danger': '#E74C3C',     # Rouge (identique à accent)
            'info': '#3498DB'       # Bleu info
        }

        self.setup_style()
        self.create_menu()
        self.setup_ui()
        self.load_articles()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_style(self):
        self.style = ttk.Style()
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Roboto", size=10)  # Police plus moderne
        self.root.option_add("*Font", default_font)

        # Thème de base plus moderne que 'default'
        self.style.theme_use('clam')

        self.style.configure("TFrame", background=self.colors['background'])
        self.style.configure(
            "TLabel", background=self.colors['background'], foreground=self.colors['text'], font=("Roboto", 10))
        self.style.configure("Header.TLabel", font=(
            "Roboto Medium", 16), foreground=self.colors['primary'])
        self.style.configure("Status.TLabel", font=("Roboto Light", 9))
        self.style.configure("Accent.TLabel", foreground=self.colors['accent'])

        button_font = ("Roboto Medium", 10)
        self.style.configure(
            "TButton", background=self.colors['secondary'], foreground='white', font=button_font, borderwidth=0, padding=(10, 5))
        self.style.map("TButton",
                       background=[('active', self.colors['primary']),
                                   ('pressed', self.colors['primary'])],
                       relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

        for style_name, color_key in [
            ("Primary.TButton", 'primary'), ("Success.TButton", 'success'),
            ("Warning.TButton", 'warning'), ("Danger.TButton", 'danger'),
                ("Info.TButton", 'info')]:
            self.style.configure(
                style_name, background=self.colors[color_key], foreground='white')
            self.style.map(style_name, background=[('active', self.shade_color(
                self.colors[color_key], -0.2)), ('pressed', self.shade_color(self.colors[color_key], -0.2))])

        self.style.configure("TEntry", foreground=self.colors['text'], fieldbackground='white', font=(
            "Roboto", 10), padding=5)
        self.style.configure("TCombobox", foreground=self.colors['text'], fieldbackground='white', font=(
            "Roboto", 10), padding=5)

        self.style.configure("Treeview", background='white',
                             foreground=self.colors['text'], rowheight=30, fieldbackground='white', font=("Roboto", 10))
        self.style.map("Treeview", background=[
                       ('selected', self.colors['secondary'])], foreground=[('selected', 'white')])
        self.style.configure("Treeview.Heading", background=self.colors['primary'], foreground='white', font=(
            "Roboto Medium", 10), padding=5, relief='flat')
        self.style.map("Treeview.Heading", background=[
                       ('active', self.colors['secondary'])])

        self.root.configure(background=self.colors['background'])

    def shade_color(self, hex_color, factor):
        """Assombrit ou éclaircit une couleur hexadécimale."""
        r, g, b = tuple(int(hex_color.lstrip(
            '#')[i:i+2], 16) for i in (0, 2, 4))
        r = int(max(0, min(255, r + 255 * factor)))
        g = int(max(0, min(255, g + 255 * factor)))
        b = int(max(0, min(255, b + 255 * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # Menu Fichier
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Importer depuis Excel...",
                              command=self.import_excel_secure)
        file_menu.add_command(label="Exporter tout (Excel)...",
                              command=lambda: self.export_data_to_excel(all_data=True))
        file_menu.add_command(label="Exporter sélection (Excel)...",
                              command=lambda: self.export_data_to_excel(all_data=False))
        file_menu.add_command(
            label="Exporter articles à commander (Excel)...", command=self.export_low_stock_to_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Changer d'utilisateur",
                              command=self.logout_and_relogin)
        file_menu.add_command(label="Quitter", command=self.on_closing)
        menubar.add_cascade(label="Fichier", menu=file_menu)

        # Menu Stock
        stock_menu = Menu(menubar, tearoff=0)
        stock_menu.add_command(label="Nouvel Article...",
                               command=self.add_new_article_dialog)
        stock_menu.add_command(
            label="Modifier Article Sélectionné...", command=self.edit_selected_article_dialog)
        stock_menu.add_command(
            label="Supprimer Article Sélectionné", command=self.delete_selected_article)
        stock_menu.add_separator()
        stock_menu.add_command(
            label="Ajouter Stock...", command=lambda: self.add_or_remove_stock_dialog("AJOUT"))
        stock_menu.add_command(
            label="Retirer Stock...", command=lambda: self.add_or_remove_stock_dialog("RETRAIT"))
        stock_menu.add_command(
            label="Historique de l'article...", command=self.show_article_history_dialog)
        menubar.add_cascade(label="Stock", menu=stock_menu)

        # Menu Outils
        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Statistiques...",
                               command=self.show_statistics_window)
        tools_menu.add_command(label="Sauvegardes...",
                               command=self.show_backup_window)
        menubar.add_cascade(label="Outils", menu=tools_menu)

        # Menu Administration (visible seulement pour les admins)
        if self.auth_manager.is_admin():
            admin_menu = Menu(menubar, tearoff=0)
            admin_menu.add_command(
                label="Gérer les utilisateurs...", command=self.show_user_management_window)
            # admin_menu.add_command(label="Paramètres de l'application...") # Placeholder
            menubar.add_cascade(label="Administration", menu=admin_menu)

        # Menu Aide
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="À propos...",
                              command=self.show_about_dialog)
        menubar.add_cascade(label="Aide", menu=help_menu)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Section Supérieure: Header et Recherche
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 15))
        self.create_header(top_frame)
        self.create_search_bar(top_frame)

        # Section Centrale: Liste des articles et Détails/Actions
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(fill=tk.BOTH, expand=True)

        # Panneau pour la liste des articles (plus grand)
        list_panel = ttk.Frame(center_frame)
        list_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.create_article_list(list_panel)

        # Panneau pour les détails et actions rapides (plus petit)
        details_actions_panel = ttk.Frame(center_frame, width=350)
        details_actions_panel.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        # Empêche le redimensionnement par les enfants
        details_actions_panel.pack_propagate(False)
        self.create_article_details_form(details_actions_panel)  # Remplacé
        # Nouveaux boutons d'action rapide
        self.create_quick_actions(details_actions_panel)

        # Section Inférieure: Barre d'état et Notifications
        bottom_frame = ttk.Frame(self.root, padding=(
            10, 5), relief='sunken', borderwidth=1)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.create_status_bar(bottom_frame)
        self.create_notifications_area(bottom_frame)

    def create_header(self, parent):
        header_content_frame = ttk.Frame(parent)
        header_content_frame.pack(fill=tk.X)
        try:
            # Assurez-vous que ce chemin est correct
            logo_path = os.path.join("data", "logo.jpg")
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path).resize(
                    (120, 40), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                ttk.Label(header_content_frame, image=self.logo_photo,
                          background=self.colors['background']).pack(side=tk.LEFT, padx=(0, 10))
        except Exception as e:
            print(f"Erreur chargement logo: {e}")

        ttk.Label(header_content_frame, text="GESTIONNAIRE DE STOCK PRO",
                  style="Header.TLabel").pack(side=tk.LEFT)
        self.current_user_label = ttk.Label(
            header_content_frame, text=f"Utilisateur: {self.auth_manager.get_current_user()['username']} ({self.auth_manager.get_current_user()['role']})", style="Status.TLabel")
        self.current_user_label.pack(side=tk.RIGHT, padx=10)

    def create_search_bar(self, parent):
        search_frame = ttk.Frame(parent, padding=(0, 10))
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="Rechercher:").pack(
            side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        search_entry.bind("<Return>", lambda e: self.search_articles())
        ttk.Button(search_frame, text="Chercher", command=self.search_articles,
                   style="Info.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Réinitialiser",
                   command=self.reset_search).pack(side=tk.LEFT)

    def create_article_list(self, parent):
        list_frame_container = ttk.LabelFrame(
            parent, text="Inventaire des Articles", padding=10)
        list_frame_container.pack(fill=tk.BOTH, expand=True)

        columns = ("reference", "description", "quantite",
                   "quantite_minimale", "position")
        self.article_tree = ttk.Treeview(
            list_frame_container, columns=columns, show="headings", selectmode="browse")

        col_map = {
            "reference": ("Référence", 120),
            "description": ("Description", 300),
            "quantite": ("Quantité", 80),
            "quantite_minimale": ("Qté Min.", 80),
            "position": ("Position", 100)
        }

        for col_id, (col_text, col_width) in col_map.items():
            self.article_tree.heading(
                col_id, text=col_text, command=lambda c=col_id: self.sort_treeview(c, False))
            self.article_tree.column(
                col_id, width=col_width, anchor=tk.W if col_id == "description" else tk.CENTER)

        # Tags pour le style des lignes (stock bas)
        self.article_tree.tag_configure(
            'low_stock', foreground=self.colors['danger'], font=('Roboto Medium', 10))
        self.article_tree.tag_configure(
            'normal_stock', foreground=self.colors['text'])

        scrollbar_y = ttk.Scrollbar(
            list_frame_container, orient=tk.VERTICAL, command=self.article_tree.yview)
        scrollbar_x = ttk.Scrollbar(
            list_frame_container, orient=tk.HORIZONTAL, command=self.article_tree.xview)
        self.article_tree.configure(
            yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.article_tree.pack(fill=tk.BOTH, expand=True)
        self.article_tree.bind("<<TreeviewSelect>>", self.on_article_select)

    def create_article_details_form(self, parent):
        details_frame = ttk.LabelFrame(
            parent, text="Détails de l'Article Sélectionné", padding=15)
        details_frame.pack(fill=tk.X, pady=(0, 10))

        self.detail_vars = {}
        fields = [
            ("Référence:", "reference", False), ("Description:", "description", True),
            ("Quantité Actuelle:", "quantite",
             False), ("Quantité Minimale:", "quantite_minimale", True),
            ("Position:", "position", True), ("Date Création:", "date_creation", False),
            ("Dern. Modif.:", "date_modification", False)
        ]

        for i, (label_text, key, editable) in enumerate(fields):
            ttk.Label(details_frame, text=label_text).grid(
                row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar()
            self.detail_vars[key] = var
            entry_state = 'readonly' if not editable else 'normal'
            # Pour les champs non éditables ici, on utilise un Label pour un meilleur aspect
            if not editable:
                detail_widget = ttk.Label(
                    details_frame, textvariable=var, anchor=tk.W, relief='groove', padding=2)
            else:
                detail_widget = ttk.Entry(
                    details_frame, textvariable=var, state=entry_state, width=25)
            detail_widget.grid(row=i, column=1, sticky=tk.EW, pady=3, padx=5)

        # Permet à la colonne des entrées de s'étendre
        details_frame.columnconfigure(1, weight=1)

    def create_quick_actions(self, parent):
        actions_frame = ttk.LabelFrame(
            parent, text="Actions Rapides", padding=15)
        actions_frame.pack(fill=tk.X, pady=10)

        ttk.Button(actions_frame, text="Ajouter Stock", command=lambda: self.add_or_remove_stock_dialog(
            "AJOUT"), style="Success.TButton").pack(fill=tk.X, pady=3)
        ttk.Button(actions_frame, text="Retirer Stock", command=lambda: self.add_or_remove_stock_dialog(
            "RETRAIT"), style="Warning.TButton").pack(fill=tk.X, pady=3)
        ttk.Button(actions_frame, text="Modifier Article",
                   command=self.edit_selected_article_dialog).pack(fill=tk.X, pady=3)
        ttk.Button(actions_frame, text="Historique Article",
                   command=self.show_article_history_dialog, style="Info.TButton").pack(fill=tk.X, pady=3)

    def create_status_bar(self, parent):
        self.status_var = tk.StringVar()
        self.status_var.set("Prêt.")
        status_label = ttk.Label(
            parent, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_notifications_area(self, parent):
        self.notifications_area = ttk.Label(
            parent, text="", style="Accent.TLabel", anchor=tk.E)
        self.notifications_area.pack(side=tk.RIGHT, fill=tk.X)

    def load_articles(self, sort_by=None, sort_desc=False):
        for i in self.article_tree.get_children():
            self.article_tree.delete(i)

        # Devrait retourner une liste de dictionnaires
        articles_data = self.stock_logic.get_all_articles()

        if sort_by:
            articles_data.sort(key=lambda x: x.get(
                sort_by, ''), reverse=sort_desc)

        for article in articles_data:
            values = (
                article.get('reference', ''), article.get('description', ''),
                article.get('quantite', 0), article.get(
                    'quantite_minimale', 0),
                article.get('position', '')
            )
            tag = 'low_stock' if article.get('quantite', 0) < article.get(
                'quantite_minimale', 0) else 'normal_stock'
            self.article_tree.insert("", tk.END, values=values, tags=(tag,))
        self.update_status(f"{len(articles_data)} articles chargés.")

    def sort_treeview(self, col, descending):
        data = [(self.article_tree.set(child, col), child)
                for child in self.article_tree.get_children('')]
        # Tenter de convertir en nombre si possible pour un tri numérique correct
        try:
            data.sort(key=lambda t: float(
                t[0]) if t[0] else -float('inf'), reverse=descending)
        except ValueError:
            # Tri alphabétique sinon
            data.sort(key=lambda t: str(t[0]).lower(), reverse=descending)

        for index, (val, child) in enumerate(data):
            self.article_tree.move(child, '', index)
        self.article_tree.heading(
            col, command=lambda: self.sort_treeview(col, not descending))

    def on_article_select(self, event=None):
        selected_items = self.article_tree.selection()
        if not selected_items:
            # Effacer les détails si rien n'est sélectionné
            for key in self.detail_vars:
                self.detail_vars[key].set("")
            self.selected_article_reference = None
            return

        selected_item = selected_items[0]
        self.selected_article_reference = self.article_tree.item(selected_item)[
            'values'][0]

        article_data = self.stock_logic.get_article_by_reference(
            self.selected_article_reference)
        if article_data:
            for key, var in self.detail_vars.items():
                value = article_data.get(key, "")
                if isinstance(value, datetime) or ("date" in key and value):
                    try:
                        var.set(pd.to_datetime(
                            value).strftime('%d/%m/%Y %H:%M'))
                    except:
                        var.set(str(value))
                else:
                    var.set(str(value) if value is not None else "")
            self.update_status(
                f"Article sélectionné: {article_data['reference']}")
        else:
            # Réinitialiser si l'article n'est pas trouvé
            self.selected_article_reference = None
            for key in self.detail_vars:
                self.detail_vars[key].set("")

    def update_status(self, message):
        self.status_var.set(message)

    def refresh_data_and_ui(self):
        self.load_articles()
        self.on_article_select()  # Pour rafraîchir les détails si un article était sélectionné
        self.check_notifications()  # Vérifier et afficher les notifications

    # --- Fonctions de gestion des notifications ---
    def check_initial_notifications(self):
        # Appelé une fois au démarrage après la connexion
        self.check_notifications()

    def schedule_periodic_checks(self):
        # Vérifier les notifications toutes les 5 minutes (300000 ms)
        self.root.after(300000, self.periodic_check_runner)

    def periodic_check_runner(self):
        self.check_notifications()
        # Re-planifier
        self.schedule_periodic_checks()

    def check_notifications(self):
        try:
            articles_to_notify = self.notification_manager.check_low_stock_articles()
            if articles_to_notify:
                # Afficher une notification non bloquante (par exemple, dans la barre d'état ou une petite fenêtre)
                # Pour l'instant, on met à jour une zone de texte dédiée
                notif_text = f"ALERTE STOCK BAS: {len(articles_to_notify)} article(s) critiques! "
                notif_details = []
                for art in articles_to_notify[:3]:  # Afficher les 3 premiers
                    notif_details.append(
                        f"{art['reference']} (Qté: {art['quantite_actuelle']})")
                self.notifications_area.config(
                    text=notif_text + ", ".join(notif_details) + ("..." if len(articles_to_notify) > 3 else ""))

                # Optionnel: afficher un messagebox pour la première notification de la session ou si critique
                # messagebox.showwarning("Stock Bas", f"{len(articles_to_notify)} article(s) sont en dessous du seuil minimum.")

                # Marquer comme notifié pour éviter spam (la logique est dans NotificationManager)
                # for art_notif in articles_to_notify:
                #    self.notification_manager.record_notification_sent(art_notif['reference'])
            else:
                self.notifications_area.config(text="")
        except Exception as e:
            print(f"Erreur lors de la vérification des notifications: {e}")
            self.notifications_area.config(text="Erreur notifications")

    # --- Dialogues et Actions --- (Doivent être adaptés pour utiliser self.stock_logic)
    def add_new_article_dialog(self):
        # ... (Implémentation du dialogue d'ajout, appelant self.stock_logic.add_article)
        # Doit récupérer l'ID de l'utilisateur actuel via self.auth_manager.get_current_user()['id']
        dialog = ArticleDialog(self.root, title="Nouvel Article",
                               stock_logic=self.stock_logic, auth_manager=self.auth_manager)
        if dialog.result:
            self.refresh_data_and_ui()
            messagebox.showinfo("Succès", "Article ajouté avec succès.")

    def edit_selected_article_dialog(self):
        if not self.selected_article_reference:
            messagebox.showwarning(
                "Aucune sélection", "Veuillez sélectionner un article à modifier.")
            return
        article_data = self.stock_logic.get_article_by_reference(
            self.selected_article_reference)
        if not article_data:
            messagebox.showerror(
                "Erreur", "Impossible de charger les données de l'article sélectionné.")
            return

        dialog = ArticleDialog(self.root, title="Modifier Article", article_data=article_data,
                               stock_logic=self.stock_logic, auth_manager=self.auth_manager)
        if dialog.result:
            self.refresh_data_and_ui()
            messagebox.showinfo("Succès", "Article modifié avec succès.")

    def delete_selected_article(self):
        if not self.selected_article_reference:
            messagebox.showwarning(
                "Aucune sélection", "Veuillez sélectionner un article à supprimer.")
            return
        if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir supprimer l'article {self.selected_article_reference}?"):
            if self.stock_logic.delete_article(self.selected_article_reference):
                self.refresh_data_and_ui()
                messagebox.showinfo("Succès", "Article supprimé.")
            else:
                messagebox.showerror(
                    "Erreur", "La suppression de l'article a échoué.")

    def add_or_remove_stock_dialog(self, mode="AJOUT"):
        if not self.selected_article_reference:
            messagebox.showwarning(
                "Aucune sélection", "Veuillez sélectionner un article.")
            return

        title = "Ajouter au Stock" if mode == "AJOUT" else "Retirer du Stock"
        dialog = StockMovementDialog(self.root, title=title, reference=self.selected_article_reference,
                                     mode=mode, stock_logic=self.stock_logic, auth_manager=self.auth_manager)
        if dialog.result:
            self.refresh_data_and_ui()
            messagebox.showinfo(
                "Succès", f"Stock mis à jour pour {self.selected_article_reference}.")

    def show_article_history_dialog(self):
        if not self.selected_article_reference:
            messagebox.showwarning(
                "Aucune sélection", "Veuillez sélectionner un article pour voir son historique.")
            return
        HistoryDialog(self.root, self.selected_article_reference,
                      self.stock_logic)

    def import_excel_secure(self):
        # Le mot de passe pour l'import/export n'est plus géré ici, car l'accès est contrôlé par l'authentification utilisateur.
        # Si une protection supplémentaire est souhaitée pour cette action spécifique, elle doit être réévaluée.
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=(("Fichiers Excel", "*.xlsx *.xls"),
                       ("Tous les fichiers", "*.*"))
        )
        if not file_path:
            return

        success, message, stats = self.stock_logic.import_from_excel(file_path)
        if success:
            self.refresh_data_and_ui()
            messagebox.showinfo(
                "Importation Réussie", f"{message}\nAjoutés: {stats['added']}, Mis à jour: {stats['updated']}, Erreurs: {stats['errors']}")
        else:
            messagebox.showerror("Échec de l'importation", message)

    def export_data_to_excel(self, all_data=True):
        # ... (Implémenter l'exportation, potentiellement dans stock_logic ou ici)
        # Pour l'instant, un placeholder
        articles_to_export = []
        if all_data:
            articles_to_export = self.stock_logic.get_all_articles()
        elif self.selected_article_reference:
            article = self.stock_logic.get_article_by_reference(
                self.selected_article_reference)
            if article:
                articles_to_export.append(article)
        else:
            messagebox.showwarning(
                "Exportation de la sélection", "Aucun article sélectionné pour l'exportation.")
            return

        if not articles_to_export:
            messagebox.showinfo("Exportation", "Aucun article à exporter.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Enregistrer sous...",
            defaultextension=".xlsx",
            filetypes=(("Fichiers Excel", "*.xlsx"),)
        )
        if not file_path:
            return

        try:
            df = pd.DataFrame(articles_to_export)
            # Sélectionner et ordonner les colonnes pour l'export
            cols_to_export = ['reference', 'description', 'quantite',
                              'quantite_minimale', 'position', 'date_creation', 'date_modification']
            df = df[[col for col in cols_to_export if col in df.columns]]
            df.to_excel(file_path, index=False)
            messagebox.showinfo(
                "Exportation Réussie", f"Données exportées avec succès vers {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur d'exportation",
                                 f"Une erreur est survenue: {e}")

    def export_low_stock_to_excel(self):
        low_stock_articles = self.stock_logic.get_low_stock_articles()
        if not low_stock_articles:
            messagebox.showinfo("Exportation Stock Bas",
                                "Aucun article en stock bas à exporter.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Enregistrer les articles à commander sous...",
            defaultextension=".xlsx",
            filetypes=(("Fichiers Excel", "*.xlsx"),)
        )
        if not file_path:
            return
        try:
            df = pd.DataFrame(low_stock_articles)
            cols_to_export = ['reference', 'description',
                              'quantite', 'quantite_minimale', 'position']
            df = df[[col for col in cols_to_export if col in df.columns]]
            df['a_commander'] = df['quantite_minimale'] - \
                df['quantite']  # Calcul de la quantité à commander
            df.to_excel(file_path, index=False)
            messagebox.showinfo(
                "Exportation Réussie", f"Articles à commander exportés vers {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur d'exportation",
                                 f"Une erreur est survenue: {e}")

    def show_statistics_window(self):
        StatisticsWindow(self.root, self.stats_manager)

    def show_backup_window(self):
        BackupWindow(self.root, self.backup_manager)

    def show_user_management_window(self):
        if self.auth_manager.is_admin():
            UserManagementWindow(self.root, self.db_manager, self.auth_manager)
        else:
            messagebox.showerror(
                "Accès Refusé", "Cette fonctionnalité est réservée aux administrateurs.")

    def show_about_dialog(self):
        messagebox.showinfo("À propos de Gestionnaire de Stock Pro",
                            "Version: 2.0 (Refonte)\n"
                            "Développé par: Manus AI pour Swisspro\n"
                            "Une application pour gérer votre inventaire efficacement.")

    def logout_and_relogin(self):
        self.auth_manager.logout()
        # Fermer la fenêtre principale actuelle et tenter de relancer le processus de connexion
        # Cela nécessite de relancer l'application ou de recréer la fenêtre principale
        self.root.destroy()
        # Pour une vraie relance, il faudrait que run_app.py gère une boucle ou soit appelé à nouveau
        # Pour simplifier ici, on quitte. Une meilleure gestion serait de recréer la fenêtre de login.
        # Ou, plus simplement, on pourrait juste fermer la fenêtre principale et l'utilisateur doit relancer manuellement.
        # Pour une expérience utilisateur fluide, il faudrait une fonction qui réinitialise l'état de l'application.
        # Pour l'instant, on va juste recréer la fenêtre principale si possible.
        new_root = tk.Tk()
        app = ModernStockManagerApp(new_root)  # Ceci va redemander le login
        # new_root.mainloop() # Mainloop est déjà géré par l'instance principale

    def on_closing(self):
        if messagebox.askokcancel("Quitter", "Êtes-vous sûr de vouloir quitter Gestionnaire de Stock Pro?"):
            self.db_manager.close()
            self.root.destroy()
            sys.exit(0)  # Assure une sortie propre

# --- Dialogues Spécifiques (Article, Mouvement, Historique, etc.) ---


class ArticleDialog(simpledialog.Dialog):
    def __init__(self, parent, title, stock_logic, auth_manager, article_data=None):
        self.stock_logic = stock_logic
        self.auth_manager = auth_manager
        # None pour un nouvel article, données existantes pour modification
        self.article_data = article_data
        self.fields = {}
        super().__init__(parent, title)

    def body(self, master):
        labels = ["Référence:", "Description:",
                  "Quantité Initiale:", "Quantité Minimale:", "Position:"]
        keys = ["reference", "description", "quantite",
                "quantite_minimale", "position"]

        # Pour la modification, la référence n'est pas modifiable et la quantité est gérée par mouvements
        # Pour un nouvel article, la quantité est la quantité initiale.

        for i, (text, key) in enumerate(zip(labels, keys)):
            ttk.Label(master, text=text).grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(master, width=30)
            initial_value = ""
            entry_state = tk.NORMAL

            if self.article_data:  # Mode modification
                initial_value = self.article_data.get(key, "")
                if key == "reference":
                    entry_state = tk.DISABLED  # Non modifiable
                if key == "quantite":  # La quantité n'est pas modifiée directement ici
                    labels[i] = "Quantité Actuelle:"
                    entry_state = tk.DISABLED
            elif key == "quantite":  # Mode ajout, c'est la quantité initiale
                pass  # Reste modifiable

            entry.insert(0, str(initial_value))
            entry.config(state=entry_state)
            entry.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=2)
            self.fields[key] = entry

        if self.article_data:  # Focus sur la description en mode modif
            self.fields["description"].focus_set()
        else:  # Focus sur la référence en mode ajout
            self.fields["reference"].focus_set()

        master.columnconfigure(1, weight=1)
        return self.fields[keys[0]]  # initial focus

    def validate(self):
        values = {key: entry.get().strip()
                  for key, entry in self.fields.items()}
        if not values["reference"]:
            messagebox.showerror("Erreur de validation",
                                 "La référence est obligatoire.", parent=self)
            return False
        if not values["description"]:
            messagebox.showerror("Erreur de validation",
                                 "La description est obligatoire.", parent=self)
            return False
        try:
            if not self.article_data or self.fields["quantite"].cget("state") == tk.NORMAL:
                qty = int(values.get("quantite", 0) or 0)
                if qty < 0:
                    raise ValueError("La quantité ne peut pas être négative.")
            min_qty = int(values.get("quantite_minimale", 0) or 0)
            if min_qty < 0:
                raise ValueError(
                    "La quantité minimale ne peut pas être négative.")
        except ValueError as e:
            messagebox.showerror("Erreur de validation",
                                 f"Valeur numérique invalide: {e}", parent=self)
            return False
        return True

    def apply(self):
        values = {key: entry.get().strip()
                  for key, entry in self.fields.items()}
        current_user_id = self.auth_manager.get_current_user()['id']

        ref = values["reference"].upper()
        desc = values["description"]
        pos = values["position"].upper()
        min_qty = int(values.get("quantite_minimale", 0) or 0)

        if self.article_data:  # Mode modification
            success = self.stock_logic.update_article_description_position_min_qty(
                ref, desc, min_qty, pos
            )
        else:  # Mode ajout
            qty = int(values.get("quantite", 0) or 0)
            success, msg_or_code = self.stock_logic.add_article(
                ref, desc, qty, pos, min_qty)
            if not success and msg_or_code == "EXISTS":
                # Gérer la référence dupliquée (proposer d'ajouter la quantité, etc.)
                # Pour l'instant, simple erreur
                messagebox.showerror(
                    "Erreur", f"La référence '{ref}' existe déjà.", parent=self)
                self.result = False
                return

        self.result = success
        if not success:
            messagebox.showerror(
                "Erreur", "L'opération sur l'article a échoué.", parent=self)


class StockMovementDialog(simpledialog.Dialog):
    # ... (Implémentation similaire à ArticleDialog pour ajouter/retirer stock)
    # Champs: Quantité, Projet (optionnel), Travailleur (optionnel, ou auto-rempli)
    def __init__(self, parent, title, reference, mode, stock_logic, auth_manager):
        self.reference = reference
        self.mode = mode  # "AJOUT" ou "RETRAIT"
        self.stock_logic = stock_logic
        self.auth_manager = auth_manager
        self.fields = {}
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text=f"Article: {self.reference}").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        ttk.Label(master, text="Quantité:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields["quantite"] = ttk.Entry(master, width=15)
        self.fields["quantite"].grid(
            row=1, column=1, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(master, text="Projet (optionnel):").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields["projet"] = ttk.Entry(master, width=30)
        self.fields["projet"].grid(
            row=2, column=1, sticky=tk.EW, padx=5, pady=2)

        # Travailleur pourrait être auto-rempli avec l'utilisateur connecté
        current_username = self.auth_manager.get_current_user()['username']
        ttk.Label(master, text="Travailleur:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields["travailleur"] = ttk.Entry(master, width=30)
        self.fields["travailleur"].insert(0, current_username)
        self.fields["travailleur"].grid(
            row=3, column=1, sticky=tk.EW, padx=5, pady=2)

        self.fields["quantite"].focus_set()
        master.columnconfigure(1, weight=1)
        return self.fields["quantite"]

    def validate(self):
        try:
            quantite = int(self.fields["quantite"].get())
            if quantite <= 0:
                messagebox.showerror(
                    "Validation", "La quantité doit être un nombre positif.", parent=self)
                return False
        except ValueError:
            messagebox.showerror(
                "Validation", "La quantité doit être un nombre valide.", parent=self)
            return False
        return True

    def apply(self):
        quantite = int(self.fields["quantite"].get())
        projet = self.fields["projet"].get().strip().upper() or None
        travailleur = self.fields["travailleur"].get().strip().upper()

        if self.mode == "AJOUT":
            success = self.stock_logic.add_stock(
                self.reference, quantite, projet, travailleur)
        else:  # RETRAIT
            success = self.stock_logic.remove_stock(
                self.reference, quantite, projet, travailleur)

        self.result = success
        if not success:
            messagebox.showerror(
                "Erreur", f"L'opération de {self.mode.lower()} de stock a échoué.", parent=self)


class HistoryDialog(tk.Toplevel):
    # ... (Fenêtre pour afficher l'historique des mouvements d'un article)
    def __init__(self, parent, reference, stock_logic):
        super().__init__(parent)
        self.title(f"Historique pour {reference}")
        self.geometry("900x400")
        self.transient(parent)
        self.grab_set()

        movements = stock_logic.get_article_movements(
            reference)  # Attendre une liste de dictionnaires

        cols = ["date_mouvement", "type_mouvement", "qte_avant", "qte_changee",
                "qte_apres", "projet", "travailleur", "nom_utilisateur"]
        tree = ttk.Treeview(self, columns=cols, show="headings")

        col_map = {
            "date_mouvement": ("Date", 150),
            "type_mouvement": ("Type", 100),
            "qte_avant": ("Qté Avant", 70),
            "qte_changee": ("+/- Quantité", 70),
            "qte_apres": ("Qté Après", 70),
            "projet": ("Projet", 120),
            "travailleur": ("Demandeur", 120),
            "nom_utilisateur": ("Utilisateur Sys.", 120)
        }

        for col_id, (col_text, col_width) in col_map.items():
            tree.heading(col_id, text=col_text)
            tree.column(col_id, width=col_width, anchor=tk.CENTER)

        if movements:
            for mov in movements:
                # S'assurer que les clés correspondent à ce que retourne get_article_movements
                # La méthode dans database_design.py retourne:
                # id, article_reference, date_mouvement, type_mouvement, quantite_avant_mouvement,
                # quantite_apres_mouvement, quantite_change, projet, travailleur, nom_utilisateur
                values = (
                    pd.to_datetime(mov.get('date_mouvement')).strftime(
                        '%d/%m/%Y %H:%M') if mov.get('date_mouvement') else '',
                    mov.get('type_mouvement', ''),
                    mov.get('quantite_avant_mouvement', ''),
                    mov.get('quantite_change', ''),
                    mov.get('quantite_apres_mouvement', ''),
                    mov.get('projet', ''),
                    # Ce champ est peut-être redondant avec nom_utilisateur
                    mov.get('travailleur', ''),
                    mov.get('nom_utilisateur', '')
                )
                tree.insert("", tk.END, values=values)
        else:
            tree.insert("", tk.END, values=(
                "Aucun mouvement trouvé", "", "", "", "", "", "", ""))

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        ttk.Button(self, text="Fermer", command=self.destroy).pack(pady=10)


class StatisticsWindow(tk.Toplevel):
    # ... (Fenêtre pour afficher les statistiques, graphiques, etc.)
    def __init__(self, parent, stats_manager):
        super().__init__(parent)
        self.stats_manager = stats_manager
        self.title("Statistiques du Stock")
        self.geometry("1024x600")
        self.transient(parent)
        self.grab_set()

        # TODO: Ajouter des filtres (dates, article, utilisateur)
        # TODO: Afficher des graphiques (ex: évolution stock, articles les + mouvementés)

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="Statistiques Générales",
                  font=("Roboto Medium", 14)).pack(pady=10)

        # Exemple: Afficher les stats sommaires
        df_all_movements = self.stats_manager.get_movements_dataframe()
        summary = self.stats_manager.get_summary_stats(df_all_movements)

        summary_text_area = tk.Text(main_frame, height=15, width=80, font=(
            "Roboto", 10), relief='sunken', borderwidth=1)
        summary_text_area.pack(pady=10, fill=tk.BOTH, expand=True)
        summary_text_area.insert(
            tk.END, f"Statistiques Sommaires:\n-----------------------\n")
        summary_text_area.insert(
            tk.END, f"Total Mouvements: {summary['total_mouvements']}\n")
        summary_text_area.insert(
            tk.END, f"Total Quantité Entrée: {summary['total_quantite_entree']}\n")
        summary_text_area.insert(
            tk.END, f"Total Quantité Sortie: {summary['total_quantite_sortie']}\n\n")

        summary_text_area.insert(tk.END, "Articles les plus mouvementés:\n")
        for item in summary['articles_plus_mouvementes']:
            summary_text_area.insert(
                tk.END, f"  - {item['article']}: {item['nombre_mouvements']} mouvements\n")
        summary_text_area.insert(tk.END, "\nUtilisateurs les plus actifs:\n")
        for item in summary['utilisateurs_plus_actifs']:
            summary_text_area.insert(
                tk.END, f"  - {item['utilisateur']}: {item['nombre_actions']} actions\n")
        summary_text_area.config(state=tk.DISABLED)

        # Placeholder pour graphiques
        # graph_frame = ttk.Frame(main_frame)
        # graph_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        # ttk.Label(graph_frame, text="(Zone pour les graphiques à venir)").pack()

        ttk.Button(main_frame, text="Fermer",
                   command=self.destroy).pack(pady=10)


class BackupWindow(tk.Toplevel):
    # ... (Fenêtre pour gérer les sauvegardes)
    def __init__(self, parent, backup_manager):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.title("Gestion des Sauvegardes")
        self.geometry("700x450")
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Button(main_frame, text="Créer une Sauvegarde Manuelle Maintenant",
                   command=self.create_manual_backup, style="Primary.TButton").pack(pady=10, fill=tk.X)

        list_frame = ttk.LabelFrame(
            main_frame, text="Sauvegardes Disponibles", padding=10)
        list_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.backup_listbox = tk.Listbox(
            list_frame, height=10, font=("Roboto", 10))
        self.backup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.backup_listbox.yview)
        self.backup_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.refresh_backup_list()

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(pady=10, fill=tk.X)
        ttk.Button(action_frame, text="Restaurer la Sélection", command=self.restore_selected_backup,
                   style="Warning.TButton").pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(action_frame, text="Supprimer Anciennes (max 7)",
                   command=self.manage_old_backups).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(action_frame, text="Fermer",
                   command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def refresh_backup_list(self):
        self.backup_listbox.delete(0, tk.END)
        backups = self.backup_manager.list_backups()
        for backup_file in backups:
            self.backup_listbox.insert(tk.END, os.path.basename(backup_file))

    def create_manual_backup(self):
        backup_path = self.backup_manager.create_backup(suffix="_manuel_ui")
        if backup_path:
            messagebox.showinfo(
                "Sauvegarde", f"Sauvegarde manuelle créée: {os.path.basename(backup_path)}", parent=self)
            self.refresh_backup_list()
        else:
            messagebox.showerror(
                "Sauvegarde", "Échec de la création de la sauvegarde manuelle.", parent=self)

    def restore_selected_backup(self):
        selected_indices = self.backup_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "Restauration", "Veuillez sélectionner une sauvegarde à restaurer.", parent=self)
            return
        selected_backup_name = self.backup_listbox.get(selected_indices[0])

        if messagebox.askyesno("Confirmation",
                               f"Êtes-vous sûr de vouloir restaurer la base de données à partir de '{selected_backup_name}'?\n"
                               f"L'état actuel de la base de données sera écrasé.", parent=self):
            if self.backup_manager.restore_backup(selected_backup_name):
                messagebox.showinfo(
                    "Restauration", "Base de données restaurée avec succès. Veuillez redémarrer l'application.", parent=self)
                # Idéalement, l'application devrait se fermer ou forcer une reconnexion / rechargement complet.
                self.master.master.on_closing()  # Tenter de fermer l'application principale
            else:
                messagebox.showerror(
                    "Restauration", "Échec de la restauration de la sauvegarde.", parent=self)

    def manage_old_backups(self):
        # Par défaut, conserve 7 sauvegardes "normales"
        self.backup_manager.manage_backups(max_backups=7)
        messagebox.showinfo("Gestion des Sauvegardes",
                            "Les anciennes sauvegardes ont été gérées.", parent=self)
        self.refresh_backup_list()


class UserManagementWindow(tk.Toplevel):
    # ... (Fenêtre pour ajouter/modifier/supprimer des utilisateurs - Admin seulement)
    def __init__(self, parent, db_manager, auth_manager):
        super().__init__(parent)
        self.db_manager = db_manager  # Directement pour la gestion des utilisateurs
        self.auth_manager = auth_manager  # Pour vérifier les droits, etc.
        self.title("Gestion des Utilisateurs")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Liste des utilisateurs
        user_list_frame = ttk.LabelFrame(
            main_frame, text="Utilisateurs Existants", padding=10)
        user_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        self.user_tree = ttk.Treeview(user_list_frame, columns=(
            "id", "username", "role"), show="headings")
        self.user_tree.heading("id", text="ID")
        self.user_tree.column("id", width=50, anchor=tk.CENTER)
        self.user_tree.heading("username", text="Nom d'utilisateur")
        self.user_tree.column("username", width=200)
        self.user_tree.heading("role", text="Rôle")
        self.user_tree.column("role", width=100, anchor=tk.CENTER)
        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        user_scrollbar = ttk.Scrollbar(
            user_list_frame, orient=tk.VERTICAL, command=self.user_tree.yview)
        self.user_tree.config(yscrollcommand=user_scrollbar.set)
        user_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.load_users()

        # Actions
        action_frame = ttk.Frame(main_frame, padding=(0, 10))
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Ajouter Utilisateur", command=self.add_user_dialog,
                   style="Success.TButton").pack(side=tk.LEFT, padx=5)
        # ttk.Button(action_frame, text="Modifier PIN/Rôle", command=self.edit_user_dialog).pack(side=tk.LEFT, padx=5) # Plus complexe
        ttk.Button(action_frame, text="Supprimer Utilisateur",
                   command=self.delete_user_dialog, style="Danger.TButton").pack(side=tk.LEFT, padx=5)

        ttk.Button(main_frame, text="Fermer", command=self.destroy).pack(
            pady=10, side=tk.BOTTOM)

    def load_users(self):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        try:
            self.db_manager.cursor.execute(
                "SELECT id, nom_utilisateur, role FROM utilisateurs ORDER BY nom_utilisateur")
            users = self.db_manager.cursor.fetchall()
            for user in users:
                self.user_tree.insert("", tk.END, values=user)
        except Exception as e:
            messagebox.showerror(
                "Erreur", f"Impossible de charger les utilisateurs: {e}", parent=self)

    def add_user_dialog(self):
        dialog = AddUserDialog(self, self.db_manager)
        if dialog.result:
            self.load_users()
            messagebox.showinfo("Succès", "Utilisateur ajouté.", parent=self)

    def delete_user_dialog(self):
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showwarning(
                "Sélection", "Veuillez sélectionner un utilisateur à supprimer.", parent=self)
            return
        user_id_to_delete = self.user_tree.item(selected_items[0])['values'][0]
        username_to_delete = self.user_tree.item(
            selected_items[0])['values'][1]

        # Empêcher la suppression de l'utilisateur admin actuellement connecté
        current_user = self.auth_manager.get_current_user()
        if current_user and current_user['id'] == user_id_to_delete:
            messagebox.showerror(
                "Interdit", "Vous ne pouvez pas supprimer l'utilisateur actuellement connecté.", parent=self)
            return
        if username_to_delete.lower() == 'admin' and current_user['username'].lower() != 'admin':
            messagebox.showerror(
                "Interdit", "Seul l'utilisateur 'admin' principal peut supprimer d'autres admins (ou lui-même s'il n'est pas le dernier).", parent=self)
            # Une logique plus fine serait nécessaire pour le dernier admin

        if messagebox.askyesno("Confirmation", f"Supprimer l'utilisateur '{username_to_delete}' (ID: {user_id_to_delete})?", parent=self):
            try:
                self.db_manager.cursor.execute(
                    "DELETE FROM utilisateurs WHERE id = ?", (user_id_to_delete,))
                self.db_manager.conn.commit()
                self.load_users()
                messagebox.showinfo(
                    "Succès", "Utilisateur supprimé.", parent=self)
            except Exception as e:
                messagebox.showerror(
                    "Erreur", f"Impossible de supprimer l'utilisateur: {e}", parent=self)
                self.db_manager.conn.rollback()


class AddUserDialog(simpledialog.Dialog):
    def __init__(self, parent, db_manager):
        self.db_manager = db_manager
        self.fields = {}
        super().__init__(parent, "Ajouter un Nouvel Utilisateur")

    def body(self, master):
        ttk.Label(master, text="Nom d'utilisateur:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields['username'] = ttk.Entry(master, width=25)
        self.fields['username'].grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(master, text="PIN (min. 4 chiffres):").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields['pin'] = ttk.Entry(master, show="*", width=25)
        self.fields['pin'].grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(master, text="Confirmer PIN:").grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields['pin_confirm'] = ttk.Entry(master, show="*", width=25)
        self.fields['pin_confirm'].grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(master, text="Rôle:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.fields['role'] = ttk.Combobox(
            master, values=["utilisateur", "admin"], state="readonly", width=23)
        self.fields['role'].set("utilisateur")
        self.fields['role'].grid(row=3, column=1, padx=5, pady=2)

        self.fields['username'].focus_set()
        return self.fields['username']

    def validate(self):
        username = self.fields['username'].get().strip()
        pin = self.fields['pin'].get()
        pin_confirm = self.fields['pin_confirm'].get()
        if not username or not pin or not pin_confirm:
            messagebox.showerror(
                "Validation", "Tous les champs sont obligatoires.", parent=self)
            return False
        if len(pin) < 4 or not pin.isdigit():
            messagebox.showerror(
                "Validation", "Le PIN doit contenir au moins 4 chiffres.", parent=self)
            return False
        if pin != pin_confirm:
            messagebox.showerror(
                "Validation", "Les PINs ne correspondent pas.", parent=self)
            return False
        return True

    def apply(self):
        username = self.fields['username'].get().strip()
        pin = self.fields['pin'].get()
        role = self.fields['role'].get()

        if self.db_manager.add_user(username, pin, role):
            self.result = True
        else:
            # L'erreur est déjà affichée par db_manager.add_user (ex: utilisateur existe déjà)
            self.result = False


# Point d'entrée principal de l'application (déplacé de run_app.py pour la cohésion)
if __name__ == "__main__":
    # Créer le répertoire data s'il n'existe pas (déplacé de run_app.py)
    os.makedirs("data", exist_ok=True)
    # Le fichier run_app.py pourrait maintenant juste importer et lancer ModernStockManagerApp

    root = tk.Tk()
    # La logique de login est maintenant dans __init__
    app = ModernStockManagerApp(root)
    if app.auth_manager.get_current_user():  # Si le login a réussi
        root.mainloop()
    else:
        print("Fermeture de l'application car la connexion a échoué ou a été annulée.")
        # root.destroy() est déjà appelé dans perform_login si échec

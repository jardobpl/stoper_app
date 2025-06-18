import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime, timedelta, date
import os
import json
import locale
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import shutil
import sys
import platform
import csv

# ==============================================================================
#  Stałe i Konfiguracja (CONSTANTS)
# ==============================================================================

class AppConfig:
    """Przechowuje stałe i konfiguracje aplikacji."""
    APP_NAME = "Stoper Pro"
    APP_VERSION = "3.0 Final"
    
    # Ścieżki plików zmienione na .csv
    LOG_FILE = "wynik-stoper.csv"
    CONFIG_FILE = "config-stoper.json"
    LOG_BACKUP_FILE = "wynik-stoper.csv.bak"
    APP_LOG_FILE = "log-stoper.log"

    # Kolory
    COLOR_GREEN_DARK = "#27AE60"
    COLOR_GREEN_LIGHT = "#2ECC71"
    COLOR_BLUE_SEA = "#2E86AB"
    COLOR_BLUE_ACTION = "#2196F3"
    COLOR_ORANGE_DARK = "#E67E22"
    COLOR_ORANGE_LIGHT = "#F39C12"
    COLOR_RED_DARK = "#E74C3C"
    COLOR_RED_LIGHT = "#F44336"
    COLOR_PURPLE_DARK = "#8E44AD"
    COLOR_PURPLE_VIOLET = "#800080"
    COLOR_GRAY = "#7F8C8D"
    COLOR_WHITE = "white"
    COLOR_BG_DARK = "#2C3E50"
    COLOR_FG_DARK = "#ECF0F1"

    # Czcionki
    FONT_DEFAULT = ("Helvetica", 9)
    FONT_DEFAULT_BOLD = ("Helvetica", 9, "bold")
    FONT_TIME_LABEL = ("Helvetica", 38, "bold")
    FONT_SUM_LABEL = ("Helvetica", 10, "bold")
    FONT_STATUS_INDICATOR = ("Helvetica", 8, "bold")

    # Ustawienia Timera
    RESET_CONFIRMATION_SECONDS = 600  # 10 minut

# ==============================================================================
#  Główna Klasa Aplikacji
# ==============================================================================

class StopwatchApp:
    """Ulepszona aplikacja stopera z poprawioną architekturą i funkcjonalnościami."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(AppConfig.APP_NAME)
        self.root.geometry("500x496")

        # --- Stan Aplikacji (Core State) ---
        self.is_running = False
        self.counter: float = 0.0
        self.start_timestamp: Optional[datetime] = None
        self.elapsed_time_before_pause: float = 0.0
        self.current_task: str = ""
        self.last_logged_minute_mark: int = 0
        
        # --- Stan Okien Pomocniczych ---
        self.reminder_window: Optional[tk.Toplevel] = None
        self.last_reminder_time: Optional[float] = None
        self.status_popup: Optional[tk.Toplevel] = None

        # --- Inicjalizacja ---
        self.setup_logging()
        self.config = self.load_config()
        self.daily_goal = self.config.get('daily_goal', 180)

        self.setup_locale()
        self.setup_styles()
        self.setup_ui()
        self.setup_keybindings()
        self.setup_menu()
        self.create_status_indicator()
        
        # --- Uruchomienie pętli i procesów ---
        self.update_display()
        self.reminder_check()
        self.apply_config_changes()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.center_window()

    def center_window(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

    # ==========================================================================
    #  Konfiguracja i Ustawienia (Setup Methods)
    # ==========================================================================

    def setup_logging(self) -> None:
        log_path = self.get_app_path() / AppConfig.APP_LOG_FILE
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_app_path(self) -> Path:
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent

    def setup_locale(self) -> None:
        locales_to_try = ['pl_PL.UTF-8', 'pl_PL.utf8', 'pl_PL', 'pl']
        if platform.system() == "Windows":
            locales_to_try.insert(0, 'Polish_Poland.1250')
        for loc in locales_to_try:
            try:
                locale.setlocale(locale.LC_ALL, loc)
                self.logger.info(f"Locale ustawione na: {loc}")
                return
            except locale.Error:
                continue
        self.logger.warning("Nie udało się ustawić polskiego locale.")

    def get_polish_day_name(self, date_obj: datetime.date) -> str:
        polish_days = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']
        try:
            day_name = date_obj.strftime('%A').lower()
            english_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            if day_name in english_days:
                 return polish_days[date_obj.weekday()]
            return day_name
        except Exception:
            return polish_days[date_obj.weekday()]
            
    def setup_styles(self) -> None:
        self.style = ttk.Style()
        self.style.theme_use('clam')

        btn_padding = 4
        self.style.configure("Start.TButton", foreground=AppConfig.COLOR_WHITE, background=AppConfig.COLOR_GREEN_DARK, font=AppConfig.FONT_DEFAULT_BOLD, padding=btn_padding)
        self.style.map("Start.TButton", background=[('active', AppConfig.COLOR_GREEN_LIGHT)])
        self.style.configure("Pause.TButton", foreground=AppConfig.COLOR_WHITE, background=AppConfig.COLOR_ORANGE_LIGHT, font=AppConfig.FONT_DEFAULT_BOLD, padding=btn_padding)
        self.style.map("Pause.TButton", background=[('active', AppConfig.COLOR_ORANGE_DARK)])
        self.style.configure("Reset.TButton", foreground=AppConfig.COLOR_WHITE, background=AppConfig.COLOR_RED_LIGHT, font=AppConfig.FONT_DEFAULT_BOLD, padding=btn_padding)
        self.style.map("Reset.TButton", background=[('active', AppConfig.COLOR_RED_DARK)])
        self.style.configure("Save.TButton", foreground=AppConfig.COLOR_WHITE, background=AppConfig.COLOR_BLUE_ACTION, font=AppConfig.FONT_DEFAULT_BOLD, padding=btn_padding)
        self.style.map("Save.TButton", background=[('active', '#4DABF5')])

    def setup_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self.time_label = tk.Label(main_frame, text="00:00:00", font=AppConfig.FONT_TIME_LABEL, fg=AppConfig.COLOR_BLUE_SEA)
        self.time_label.grid(row=0, column=0, pady=10, sticky=tk.EW)

        task_frame = ttk.LabelFrame(main_frame, text="Zadanie", padding="5")
        task_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        task_frame.columnconfigure(0, weight=1)
        self.task_var = tk.StringVar()
        self.task_entry = ttk.Entry(task_frame, textvariable=self.task_var, font=AppConfig.FONT_DEFAULT)
        self.task_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        self.task_entry.bind('<Return>', lambda e: self.start())

        controls_frame = ttk.LabelFrame(main_frame, text="Kontrola", padding="5")
        controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        controls_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.start_button = ttk.Button(controls_frame, text="Start", command=self.start, style="Start.TButton")
        self.start_button.grid(row=0, column=0, padx=5, sticky=tk.EW)
        self.pause_button = ttk.Button(controls_frame, text="Pauza", command=self.stop, style="Pause.TButton", state="disabled")
        self.pause_button.grid(row=0, column=1, padx=5, sticky=tk.EW)
        self.reset_button = ttk.Button(controls_frame, text="Reset", command=self.reset, style="Reset.TButton")
        self.reset_button.grid(row=0, column=2, padx=5, sticky=tk.EW)
        self.add_button = ttk.Button(controls_frame, text="Zapisz", command=self.add_to_log, style="Save.TButton")
        self.add_button.grid(row=0, column=3, padx=5, sticky=tk.EW)

        adjust_frame = ttk.LabelFrame(main_frame, text="Korekta czasu", padding="5")
        adjust_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        adjust_frame.columnconfigure((0, 1, 2, 3), weight=1)
        ttk.Button(adjust_frame, text="+5 min", command=lambda: self.adjust_time(300)).grid(row=0, column=0, padx=2, sticky=tk.EW)
        ttk.Button(adjust_frame, text="+1 min", command=lambda: self.adjust_time(60)).grid(row=0, column=1, padx=2, sticky=tk.EW)
        ttk.Button(adjust_frame, text="-1 min", command=lambda: self.adjust_time(-60)).grid(row=0, column=2, padx=2, sticky=tk.EW)
        ttk.Button(adjust_frame, text="-5 min", command=lambda: self.adjust_time(-300)).grid(row=0, column=3, padx=2, sticky=tk.EW)

        info_frame = ttk.LabelFrame(main_frame, text="Informacje", padding="5")
        info_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        info_frame.columnconfigure(0, weight=1)
        self.start_time_label = ttk.Label(info_frame, text="Czas startu: --")
        self.start_time_label.grid(row=0, column=0, sticky=tk.W, pady=1)
        self.progress_label = ttk.Label(info_frame, text="Postęp dnia")
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
        self.progress_bar = ttk.Progressbar(info_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=1)
        self.sum_label = ttk.Label(info_frame, text="Suma: 0 min (0.00%)", font=AppConfig.FONT_SUM_LABEL)
        self.sum_label.grid(row=3, column=0, sticky=tk.W, pady=1)

        quick_frame = ttk.LabelFrame(main_frame, text="Szybkie akcje", padding="5")
        quick_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        quick_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(quick_frame, text="Historia", command=self.show_history).grid(row=0, column=0, padx=5, sticky=tk.EW)
        ttk.Button(quick_frame, text="Statystyki", command=self.show_statistics).grid(row=0, column=1, padx=5, sticky=tk.EW)

    def setup_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plik", menu=file_menu)
        file_menu.add_command(label="Eksportuj dane...", command=self.export_data)
        file_menu.add_command(label="Importuj dane...", command=self.import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Wyjście", command=self.on_closing)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Narzędzia", menu=tools_menu)
        tools_menu.add_command(label="Konfiguracja", command=self.show_config, accelerator="Ctrl+,")
        tools_menu.add_command(label="Historia", command=self.show_history, accelerator="Ctrl+H")
        tools_menu.add_command(label="Statystyki", command=self.show_statistics, accelerator="Ctrl+T")
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Pomoc", menu=help_menu)
        help_menu.add_command(label="Skróty klawiszowe", command=self.show_shortcuts, accelerator="F1")
        help_menu.add_command(label="O aplikacji", command=self.show_about)

    def setup_keybindings(self) -> None:
        bindings = {
            '<Control-s>': lambda e: self.start(),
            '<Control-p>': lambda e: self.stop(),
            '<Control-r>': lambda e: self.reset(),
            '<Control-Return>': lambda e: self.add_to_log(),
            '<Control-h>': lambda e: self.show_history(),
            '<Control-comma>': lambda e: self.show_config(),
            '<Control-t>': lambda e: self.show_statistics(),
            '<F1>': lambda e: self.show_shortcuts(),
            '<space>': lambda e: self.toggle_start_stop(),
            '<Escape>': lambda e: self.reset()
        }
        for key, command in bindings.items():
            self.root.bind_all(key, command)

    # ==========================================================================
    #  Główna Logika Stoper (Core Logic)
    # ==========================================================================
    
    def start(self) -> None:
        if self.is_running: return
        self.is_running = True
        self.current_task = self.task_var.get().strip()
        if self.start_timestamp is None:
            self.start_timestamp = datetime.now()
        else: # Wznowienie po pauzie
            self.start_timestamp = datetime.now()

        self.logger.info(f"Stoper wystartował/wznowiony - Zadanie: {self.current_task or 'Brak'}")
        self.refresh_start_time_label()
        self.update_ui_state()
        self.hide_reminder()

    def stop(self) -> None:
        if not self.is_running: return
        self.is_running = False
        if self.start_timestamp:
            elapsed = (datetime.now() - self.start_timestamp).total_seconds()
            self.elapsed_time_before_pause += elapsed
            self.counter = self.elapsed_time_before_pause
        self.logger.info("Stoper zatrzymany (pauza)")
        self.update_ui_state()

    def reset(self) -> None:
        if self.counter > AppConfig.RESET_CONFIRMATION_SECONDS:
            if not messagebox.askyesno("Potwierdzenie", 
                        f"Czy na pewno chcesz zresetować {int(self.counter // 60)} minut?"):
                return
        self.is_running = False
        self.counter = 0.0
        self.start_timestamp = None
        self.elapsed_time_before_pause = 0.0
        self.current_task = ""
        self.task_var.set("")
        self.last_logged_minute_mark = 0
        self.refresh_time_label()
        self.refresh_start_time_label()
        self.update_progress()
        self.update_ui_state()
        self.logger.info("Stoper zresetowany")

    def toggle_start_stop(self) -> None:
        if self.is_running: self.stop()
        else: self.start()

    def adjust_time(self, seconds: int) -> None:
        self.counter = max(0, self.counter + seconds)
        self.elapsed_time_before_pause = max(0, self.elapsed_time_before_pause + seconds)
        self.refresh_time_label()
        self.logger.info(f"Czas skorygowany o {seconds/60:.1f} minut")
        
    # ==========================================================================
    #  Aktualizacja Interfejsu (UI Updates)
    # ==========================================================================

    def update_display(self) -> None:
        if self.is_running and self.start_timestamp:
            elapsed = (datetime.now() - self.start_timestamp).total_seconds()
            self.counter = self.elapsed_time_before_pause + elapsed

            # Logowanie co 5 minut
            current_five_minute_interval = int(self.counter) // 300
            if current_five_minute_interval > self.last_logged_minute_mark:
                self.last_logged_minute_mark = current_five_minute_interval
                formatted_time = self.format_time(self.counter)
                self.logger.info(f"Stoper aktywny. Czas: {formatted_time}")

        self.refresh_time_label()
        self.update_time_color()
        self.update_status_indicator()
        if int(self.counter) % 5 == 0: self.update_progress()
        self.root.after(200, self.update_display)

    def update_ui_state(self):
        if self.is_running:
            self.start_button.config(text="Uruchomiony", state="disabled")
            self.pause_button.config(state="normal")
            self.task_entry.config(state="disabled")
        else:
            start_text = "Wznów" if self.counter > 0 else "Start"
            self.start_button.config(text=start_text, state="normal")
            self.pause_button.config(state="disabled")
            self.task_entry.config(state="normal")

    def format_time(self, total_seconds: float) -> str:
        total_seconds = int(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def format_duration(self, duration: timedelta) -> str:
        s = int(duration.total_seconds())
        h, rem = divmod(s, 3600)
        m, _ = divmod(rem, 60)
        return f"{h}h {m}m" if h > 0 else f"{m}m"

    def refresh_time_label(self) -> None:
        formatted_time = self.format_time(self.counter)
        self.time_label.config(text=formatted_time)
        minutes = int(self.counter // 60)
        status = "▶" if self.is_running else "⏸"
        self.root.title(f"{AppConfig.APP_NAME} - {status} {minutes}m")

    def refresh_start_time_label(self) -> None:
        if self.elapsed_time_before_pause == 0 and not self.is_running:
            self.start_time_label.config(text="Czas startu: --", foreground=AppConfig.COLOR_GRAY)
            return
        
        start_time_to_show = self.start_timestamp or datetime.now()
        first_start_time = start_time_to_show - timedelta(seconds=self.elapsed_time_before_pause)
        formatted = first_start_time.strftime("%Y-%m-%d %H:%M:%S")
        duration = datetime.now() - first_start_time

        self.start_time_label.config(text=f"Start: {formatted} (przed {self.format_duration(duration)})", foreground=AppConfig.COLOR_PURPLE_DARK)

    def update_time_color(self) -> None:
        if self.is_running: color = AppConfig.COLOR_GREEN_DARK
        elif self.counter > 0: color = AppConfig.COLOR_ORANGE_DARK
        else: color = AppConfig.COLOR_BLUE_SEA
        self.time_label.config(fg=color)

    def update_progress(self) -> None:
        total_minutes = self.read_and_sum_today()
        current_minutes = int(self.counter // 60)
        total_with_current = total_minutes + current_minutes
        percentage = (total_with_current / self.daily_goal) * 100 if self.daily_goal > 0 else 0

        # Propozycja 3: Status słowny
        if percentage < 25:
            status = "(Początek)"
        elif percentage < 75:
            status = "(Dobra passa)"
        elif percentage < 100:
            status = "(Już prawie!)"
        else:
            status = "(Cel osiągnięty!)"

        self.progress_bar["value"] = min(percentage, 100)
        color = self.get_progress_color(percentage)
        self.style.configure("Custom.Horizontal.TProgressbar", troughcolor=AppConfig.COLOR_FG_DARK, background=color)
        self.progress_bar.configure(style="Custom.Horizontal.TProgressbar")
        
        # Aktualizacja etykiety "Postęp dnia" z emoji
        self.progress_label.config(text=f"Postęp dnia {status}")
        
        self.sum_label.config(
            text=f"Suma: {total_with_current} min ({percentage:.1f}% celu: {self.daily_goal} min)",
            foreground=color
        )

    def get_progress_color(self, percentage: float) -> str:
        if percentage < 25: return AppConfig.COLOR_RED_DARK
        elif percentage < 50: return AppConfig.COLOR_ORANGE_LIGHT
        elif percentage < 75: return AppConfig.COLOR_GREEN_LIGHT
        else: return AppConfig.COLOR_GREEN_DARK

    # ==========================================================================
    #  Obsługa Plików i Danych (File Handling & Data)
    # ==========================================================================
    
    def add_to_log(self) -> None:
        minutes = int(self.counter // 60)
        if minutes < 1:
            messagebox.showwarning("Uwaga", "Czas musi wynosić co najmniej 1 minutę, aby go zapisać.")
            return
        if self.is_running: self.stop()
        if self.save_to_log(minutes):
            messagebox.showinfo("Sukces", f"Zapisano {minutes} minut do logu.")
            if self.config.get('auto_save', True): self.reset()
            self.update_progress()
        else:
            messagebox.showerror("Błąd", "Nie udało się zapisać do logu.")

    def save_to_log(self, minutes: int) -> bool:
        log_path = self.get_app_path() / AppConfig.LOG_FILE
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_desc = self.current_task if self.current_task else "Bez opisu"
        
        file_exists = log_path.exists() and log_path.stat().st_size > 0

        try:
            if log_path.exists() and log_path.stat().st_size > 1024 * 1024: # Backup if > 1MB
                backup_path = self.get_app_path() / AppConfig.LOG_BACKUP_FILE
                shutil.copy2(log_path, backup_path)
            
            with open(log_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_ALL)
                
                if not file_exists:
                    writer.writerow(["Data", "Minuty", "Zadanie"]) # Nagłówek
                
                writer.writerow([timestamp, minutes, task_desc])

            self.logger.info(f"Zapisano {minutes} minut do logu CSV - Zadanie: {task_desc}")
            return True
        except IOError as e:
            self.logger.error(f"Błąd zapisu do logu CSV: {e}")
            return False

    def read_and_sum_today(self) -> int:
        log_path = self.get_app_path() / AppConfig.LOG_FILE
        if not log_path.exists(): return 0
        total, today = 0, datetime.now().date()
        try:
            with open(log_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f, delimiter=';')
                next(reader, None) # Pomiń nagłówek
                
                for line_num, row in enumerate(reader, 2):
                    if not row: continue
                    if len(row) < 3:
                        self.logger.warning(f"Nieprawidłowa liczba kolumn w linii {line_num}: {row}")
                        continue
                    try:
                        entry_date = datetime.strptime(row[0].split(" ")[0], "%Y-%m-%d").date()
                        if entry_date == today:
                            total += int(row[1])
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Błąd parsowania linii {line_num}: {e}")
        except IOError as e:
            self.logger.error(f"Błąd odczytu pliku logu CSV: {e}")
        return total
        
    def load_config(self) -> Dict:
        config_path = self.get_app_path() / AppConfig.CONFIG_FILE
        default_config = {
            'daily_goal': 180, 'reminder_interval': 120, 'reminder_duration': 15000,
            'auto_save': True, 'sound_enabled': False, 'window_always_on_top': False, 'theme': 'default'
        }
        if not config_path.exists():
            self.save_config(default_config)
            return default_config
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return self.validate_config(config, default_config)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Błąd ładowania konfiguracji: {e}")
            return default_config

    def validate_config(self, config: Dict, default_config: Dict) -> Dict:
        validated = default_config.copy()
        for key, default_value in default_config.items():
            if key in config:
                value = config[key]
                if key in ['daily_goal', 'reminder_interval', 'reminder_duration']:
                    if isinstance(value, int) and value > 0: validated[key] = value
                elif key in ['auto_save', 'sound_enabled', 'window_always_on_top']:
                    validated[key] = bool(value)
                elif key == 'theme' and isinstance(value, str):
                    validated[key] = value
        return validated

    def save_config(self, config: Optional[Dict] = None) -> bool:
        if config is None: config = self.config
        config_path = self.get_app_path() / AppConfig.CONFIG_FILE
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("Konfiguracja zapisana.")
            return True
        except IOError as e:
            self.logger.error(f"Błąd zapisu konfiguracji: {e}")
            messagebox.showerror("Błąd", f"Nie można zapisać konfiguracji: {e}")
            return False

    def apply_config_changes(self) -> None:
        self.root.attributes("-topmost", self.config.get('window_always_on_top', False))
        self.daily_goal = self.config.get('daily_goal', 180)
        self.update_progress()

    # ==========================================================================
    #  Dodatkowe Okna i Funkcje (Extra Features & Windows)
    # ==========================================================================

    def show_statistics(self) -> None:
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Statystyki Czasu Pracy")
        stats_window.geometry("800x600")
        stats_window.transient(self.root)
        stats_window.grab_set()

        start_date = date(2000, 1, 1)
        end_date = datetime.now().date()
        data = self.load_history_data(start_date, end_date)

        if not data:
            label = ttk.Label(stats_window, text="📊 Brak danych do wyświetlenia statystyk.", font=("Helvetica", 12))
            label.pack(expand=True)
            return

        all_entries = []
        for date_obj, entries in data.items():
            for entry in entries:
                all_entries.append({'date': date_obj, 'mins': entry[1], 'task': entry[2]})

        total_minutes = sum(e['mins'] for e in all_entries)
        total_hours = total_minutes / 60
        total_entries = len(all_entries)
        avg_session = total_minutes / total_entries if total_entries else 0
        longest_session = max(e['mins'] for e in all_entries) if all_entries else 0

        tasks_summary = {}
        for entry in all_entries:
            task_name = entry['task']
            if task_name not in tasks_summary:
                tasks_summary[task_name] = {'mins': 0, 'count': 0}
            tasks_summary[task_name]['mins'] += entry['mins']
            tasks_summary[task_name]['count'] += 1
        sorted_tasks = sorted(tasks_summary.items(), key=lambda item: item[1]['mins'], reverse=True)

        weekday_summary = {i: 0 for i in range(7)}
        for entry in all_entries:
            weekday = entry['date'].weekday()
            weekday_summary[weekday] += entry['mins']
        
        daily_summary = {}
        for date_obj, entries in data.items():
            daily_summary[date_obj] = sum(e[1] for e in entries)
        most_productive_day = max(daily_summary.items(), key=lambda item: item[1]) if daily_summary else (None, 0)
        
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        summary_frame = ttk.Frame(notebook, padding="10")
        notebook.add(summary_frame, text="📈 Podsumowanie Ogólne")
        
        metrics_frame = ttk.LabelFrame(summary_frame, text="Główne Metryki", padding=10)
        metrics_frame.pack(fill=tk.X, pady=5)
        
        metrics_text = (
            f"🕒 Całkowity czas: {total_minutes} minut ({total_hours:.2f} godzin)\n"
            f"📑 Łączna liczba wpisów: {total_entries}\n"
            f"📊 Średnia długość sesji: {avg_session:.1f} minut\n"
            f"⭐ Najdłuższa sesja: {longest_session} minut\n"
            f"🏆 Najbardziej produktywny dzień: {most_productive_day[0]} ({most_productive_day[1]} min)" if most_productive_day[0] else ""
        )
        ttk.Label(metrics_frame, text=metrics_text, font=AppConfig.FONT_DEFAULT).pack(anchor=tk.W)

        weekday_frame = ttk.LabelFrame(summary_frame, text="Podsumowanie Tygodniowe", padding=10)
        weekday_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        weekday_tree = ttk.Treeview(weekday_frame, columns=('day', 'minutes'), show='headings')
        weekday_tree.heading('day', text='Dzień Tygodnia')
        weekday_tree.heading('minutes', text='Suma Minut')
        weekday_tree.column('minutes', anchor=tk.E)
        
        polish_days = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']
        for i, day_name in enumerate(polish_days):
            mins = weekday_summary.get(i, 0)
            if mins > 0:
                weekday_tree.insert('', tk.END, values=(day_name, f"{mins} min"))
        weekday_tree.pack(fill=tk.BOTH, expand=True)

        tasks_frame = ttk.Frame(notebook, padding="10")
        notebook.add(tasks_frame, text="📋 Analiza Zadań")

        task_tree = ttk.Treeview(tasks_frame, columns=('task', 'minutes', 'entries'), show='headings')
        task_tree.heading('task', text='Zadanie')
        task_tree.heading('minutes', text='Łączny Czas (min)')
        task_tree.heading('entries', text='Ilość Wpisów')
        task_tree.column('minutes', anchor=tk.E, width=150)
        task_tree.column('entries', anchor=tk.E, width=100)
        task_tree.column('task', width=400)

        for task, details in sorted_tasks:
            task_tree.insert('', tk.END, values=(task, details['mins'], details['count']))

        task_scrollbar = ttk.Scrollbar(tasks_frame, orient=tk.VERTICAL, command=task_tree.yview)
        task_tree.configure(yscrollcommand=task_scrollbar.set)
        
        task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        task_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def show_shortcuts(self) -> None:
        shortcuts = """Skróty klawiszowe:

Ctrl+S          - Start stopera
Ctrl+P          - Pauza
Ctrl+R          - Reset
Ctrl+Enter      - Zapisz do logu
Ctrl+H          - Pokaż historię
Ctrl+,          - Otwórz konfigurację
Ctrl+T          - Pokaż statystyki
Spacja          - Start/Pauza (przełącz)
Escape          - Reset
F1              - Pokaż tę pomoc"""
        messagebox.showinfo("Skróty klawiszowe", shortcuts)

    def show_about(self) -> None:
        about_text = f"""{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}

Zaawansowana aplikacja do śledzenia czasu
z funkcjami analizy i raportowania.
Autor: JarDobPL + AI
Data: 2025"""
        messagebox.showinfo(f"O aplikacji {AppConfig.APP_NAME}", about_text)

    def export_data(self) -> None:
        messagebox.showinfo("Eksport", "Funkcja eksportu będzie dostępna w następnej wersji.")

    def import_data(self) -> None:
        messagebox.showinfo("Import", "Funkcja importu będzie dostępna w następnej wersji.")
    
    # --- System przypomnień ---
    def reminder_check(self) -> None:
        if not self.is_running:
            now = datetime.now().timestamp()
            interval = self.config.get('reminder_interval', 120)
            is_reminder_visible = self.reminder_window and self.reminder_window.winfo_exists()
            if (self.last_reminder_time is None or now - self.last_reminder_time >= interval) and not is_reminder_visible:
                self.last_reminder_time = now
                self.show_reminder()
        self.root.after(30000, self.reminder_check)

    def show_reminder(self) -> None:
        self.hide_reminder()
        self.reminder_window = tk.Toplevel(self.root)
        rw = self.reminder_window
        rw.overrideredirect(True)
        rw.attributes("-topmost", True)
        rw.attributes("-alpha", 0.9)

        # ZMIANA: Geometria i pozycja paska przypomnienia
        width = self.root.winfo_screenwidth()  # Szerokość na cały ekran
        height = 35  # Niewielka wysokość paska
        x = 0  # Pozycja X od lewej krawędzi
        taskbar_height = 40  # Założona wysokość paska zadań Windows
        y = self.root.winfo_screenheight() - height - taskbar_height  # Pozycja Y nad paskiem

        rw.geometry(f"{width}x{height}+{x}+{y}")

        # ZMIANA: Tło ramki ustawione na kolor czerwony
        main_frame = tk.Frame(rw, bg=AppConfig.COLOR_RED_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ZMIANA: Tekst z emoji klepsydry i dopasowanie kolorów
        reminder_text = "🚀"
        reminder_text = reminder_text * 59
        label = tk.Label(main_frame, text=reminder_text, font=("Helvetica", 11, "bold"), 
                         bg=AppConfig.COLOR_RED_DARK, fg=AppConfig.COLOR_WHITE)
        label.pack(pady=5, expand=True)

        # ZMIANA: Możliwość zamknięcia okna poprzez kliknięcie na nim
        main_frame.bind("<Button-1>", lambda e: self.hide_reminder())
        label.bind("<Button-1>", lambda e: self.hide_reminder())

        self.root.after(self.config.get('reminder_duration', 15000), self.hide_reminder)

    def hide_reminder(self) -> None:
        if self.reminder_window and self.reminder_window.winfo_exists():
            self.reminder_window.destroy()
            self.reminder_window = None

    # --- Wskaźnik statusu ---
    def create_status_indicator(self) -> None:
        self.status_popup = tk.Toplevel(self.root)
        sp = self.status_popup
        sp.overrideredirect(True)
        sp.attributes("-topmost", True)
        sp.attributes("-alpha", 0.9)
        size, offset_x, offset_y = 21, 15, 40
        x = self.root.winfo_screenwidth() - size - offset_x
        y = self.root.winfo_screenheight() - size - offset_y
        sp.geometry(f"{size}x{size}+{x}+{y}")
        self.status_frame = tk.Frame(sp, relief=tk.RAISED, bd=1)
        self.status_frame.pack(fill=tk.BOTH, expand=True)
        self.status_time_label = tk.Label(self.status_frame, text="0", fg="white", font=AppConfig.FONT_STATUS_INDICATOR)
        self.status_time_label.pack(expand=True)

    def update_status_indicator(self) -> None:
        if self.status_popup and self.status_popup.winfo_exists():
            minutes = int(self.counter // 60)
            bg_color = AppConfig.COLOR_GREEN_DARK if self.is_running else AppConfig.COLOR_RED_DARK
            self.status_frame.config(bg=bg_color)
            self.status_time_label.config(bg=bg_color, text=str(minutes))

    # --- Okno konfiguracji ---
    def show_config(self) -> None:
        config_window = tk.Toplevel(self.root)
        config_window.title("Konfiguracja")
        config_window.geometry("500x320")
        config_window.transient(self.root)
        config_window.grab_set()

        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        vars_dict = self._create_config_vars()
        self._create_general_config(notebook, vars_dict)
        self._create_reminder_config(notebook, vars_dict)
        self._create_appearance_config(notebook, vars_dict)

        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        ttk.Button(button_frame, text="Anuluj", command=config_window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Zapisz", command=lambda: self._save_config_from_dialog(config_window, vars_dict)).pack(side=tk.RIGHT, padx=5)

    def _create_config_vars(self) -> Dict:
        return {
            'goal': tk.StringVar(value=str(self.config.get('daily_goal', 180))),
            'auto_save': tk.BooleanVar(value=self.config.get('auto_save', True)),
            'on_top': tk.BooleanVar(value=self.config.get('window_always_on_top', False)),
            'rem_interval': tk.StringVar(value=str(self.config.get('reminder_interval', 120))),
            'rem_duration': tk.StringVar(value=str(self.config.get('reminder_duration', 15000))),
            'sound': tk.BooleanVar(value=self.config.get('sound_enabled', False)),
            'theme': tk.StringVar(value=self.config.get('theme', 'default'))
        }

    def _create_general_config(self, parent: ttk.Notebook, vars_dict: Dict) -> None:
        frame = ttk.Frame(parent, padding=10)
        parent.add(frame, text="Ogólne")
        ttk.Label(frame, text="Cel dzienny (minuty):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(frame, from_=30, to=1440, textvariable=vars_dict['goal'], width=10).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(frame, text="Automatyczny reset po zapisie", variable=vars_dict['auto_save']).grid(row=1, columnspan=2, sticky=tk.W, pady=5)
        ttk.Checkbutton(frame, text="Okno zawsze na wierzchu", variable=vars_dict['on_top']).grid(row=2, columnspan=2, sticky=tk.W)

    def _create_reminder_config(self, parent: ttk.Notebook, vars_dict: Dict) -> None:
        frame = ttk.Frame(parent, padding=10)
        parent.add(frame, text="Przypomnienia")
        ttk.Label(frame, text="Interwał przypomnień (sekundy):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(frame, from_=30, to=3600, textvariable=vars_dict['rem_interval'], width=10).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(frame, text="Czas wyświetlania (ms):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Spinbox(frame, from_=5000, to=60000, textvariable=vars_dict['rem_duration'], width=10).grid(row=1, column=1, sticky=tk.W)
        ttk.Checkbutton(frame, text="Dźwięk przypomnień (niedostępne)", variable=vars_dict['sound'], state="disabled").grid(row=2, columnspan=2, sticky=tk.W, pady=5)

    def _create_appearance_config(self, parent: ttk.Notebook, vars_dict: Dict) -> None:
        frame = ttk.Frame(parent, padding=10)
        parent.add(frame, text="Wygląd")
        ttk.Label(frame, text="Motyw (niedostępne):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(frame, textvariable=vars_dict['theme'], values=['default', 'dark', 'light'], state='disabled', width=12).grid(row=0, column=1, sticky=tk.W)

    def _save_config_from_dialog(self, window: tk.Toplevel, vars_dict: Dict) -> None:
        try:
            new_goal = int(vars_dict['goal'].get())
            new_interval = int(vars_dict['rem_interval'].get())
            new_duration = int(vars_dict['rem_duration'].get())
            if new_goal <= 0 or new_interval <= 0 or new_duration <= 0:
                raise ValueError("Wartości liczbowe muszą być dodatnie.")

            self.config.update({
                'daily_goal': new_goal,
                'reminder_interval': new_interval,
                'reminder_duration': new_duration,
                'auto_save': vars_dict['auto_save'].get(),
                'sound_enabled': vars_dict['sound'].get(),
                'window_always_on_top': vars_dict['on_top'].get(),
                'theme': vars_dict['theme'].get()
            })
            self.apply_config_changes()
            if self.save_config():
                window.destroy()
                messagebox.showinfo("Sukces", "Konfiguracja została zapisana!")
        except ValueError as e:
            messagebox.showerror("Błąd", f"Nieprawidłowa wartość: {e}")

    # --- Okno historii ---
    def show_history(self) -> None:
        history_window = tk.Toplevel(self.root)
        history_window.title("Historia")
        history_window.geometry("800x480")
        history_window.transient(self.root)
        history_window.grab_set()

        control_frame = ttk.Frame(history_window)
        control_frame.pack(fill=tk.X, padx=5, pady=3)
        ttk.Label(control_frame, text="Od:").pack(side=tk.LEFT, padx=(10, 3))
        self.start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        start_date_entry = ttk.Entry(control_frame, textvariable=self.start_date_var, width=12)
        start_date_entry.pack(side=tk.LEFT, padx=3)
        ttk.Label(control_frame, text="Do:").pack(side=tk.LEFT, padx=3)
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_date_entry = ttk.Entry(control_frame, textvariable=self.end_date_var, width=12)
        end_date_entry.pack(side=tk.LEFT, padx=3)

        text_frame = ttk.Frame(history_window)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10), relief=tk.FLAT)
        
        ttk.Button(control_frame, text="Odśwież", command=lambda: self.refresh_history(text_widget)).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Eksportuj do CSV", command=self.export_history).pack(side=tk.LEFT, padx=3)

        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.refresh_history(text_widget)

    def refresh_history(self, text_widget: tk.Text) -> None:
        text_widget.config(state="normal")
        text_widget.delete(1.0, tk.END)

        text_widget.tag_config("header", foreground=AppConfig.COLOR_BG_DARK, font=("Helvetica", 12, "bold"))
        text_widget.tag_config("date_good", foreground=AppConfig.COLOR_GREEN_DARK, font=("Helvetica", 11, "bold"))
        text_widget.tag_config("date_bad", foreground=AppConfig.COLOR_RED_DARK, font=("Helvetica", 11, "bold"))
        text_widget.tag_config("time_entry", foreground=AppConfig.COLOR_BLUE_ACTION)
        text_widget.tag_config("task_desc", foreground=AppConfig.COLOR_PURPLE_DARK, font=("Helvetica", 9, "italic"))
        text_widget.tag_config("summary_header", foreground=AppConfig.COLOR_BG_DARK, font=("Helvetica", 10, "bold"))
        text_widget.tag_config("summary_text", foreground=AppConfig.COLOR_BG_DARK, font=AppConfig.FONT_DEFAULT)

        try:
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            text_widget.insert(tk.END, "Błąd: Nieprawidłowy format daty (oczekiwany: RRRR-MM-DD).")
            return
        data = self.load_history_data(start_date, end_date)
        if not data:
            text_widget.insert(tk.END, "Brak danych w wybranym okresie.")
            return

        text_widget.insert(tk.END, f"HISTORIA PRACY OD {start_date} DO {end_date}\n", "header")
        text_widget.insert(tk.END, f"Cel dzienny: {self.daily_goal} minut\n\n", "summary_text")
        
        total_minutes, goal_achieved_days = 0, 0
        for date_obj in sorted(data.keys(), reverse=True):
            day_entries = data[date_obj]
            day_total = sum(entry[1] for entry in day_entries)
            total_minutes += day_total
            is_goal_achieved = day_total >= self.daily_goal
            if is_goal_achieved: goal_achieved_days += 1
            status, tag = ("✅", "date_good") if is_goal_achieved else ("❌", "date_bad")
            day_name = self.get_polish_day_name(date_obj)
            text_widget.insert(tk.END, f"{day_name.capitalize()}, {date_obj.strftime('%Y-%m-%d')} {status}\n", tag)
            text_widget.insert(tk.END, f"  Suma: {day_total} min\n", "summary_text")
            for ts, mins, task in day_entries:
                time_part = ts.split(' ')[1] if ' ' in ts else ''
                text_widget.insert(tk.END, f"    {time_part} - ", "time_entry")
                text_widget.insert(tk.END, f"{mins} min - ", "summary_text")
                text_widget.insert(tk.END, f"{task}\n", "task_desc")
            text_widget.insert(tk.END, "\n")
        
        total_days = len(data)
        if total_days > 0:
            avg_daily = total_minutes / total_days
            success_rate = (goal_achieved_days / total_days) * 100
            text_widget.insert(tk.END, "="*80 + "\nPODSUMOWANIE OKRESU\n" + "="*80 + "\n", "summary_header")
            text_widget.insert(tk.END, f"Łączny czas: {total_minutes} minut ({total_minutes/60:.2f} godzin)\n", "summary_text")
            text_widget.insert(tk.END, f"Średnia dzienna: {avg_daily:.1f} minut\n", "summary_text")
            text_widget.insert(tk.END, f"Dni z osiągniętym celem: {goal_achieved_days}/{total_days} ({success_rate:.1f}%)\n", "summary_text")
        text_widget.config(state="disabled")

    def load_history_data(self, start_date: datetime.date, end_date: datetime.date) -> Dict:
        log_path = self.get_app_path() / AppConfig.LOG_FILE
        if not log_path.exists(): return {}
        data: Dict[datetime.date, list] = {}
        try:
            with open(log_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f, delimiter=';')
                next(reader, None) # Pomiń nagłówek

                for line_num, row in enumerate(reader, 2):
                    if not row: continue
                    if len(row) < 3:
                        self.logger.warning(f"Błędny format w linii {line_num}: {row}")
                        continue
                    try:
                        ts, mins_str, task = row[0], row[1], row[2]
                        mins = int(mins_str)
                        date_obj = datetime.strptime(ts.split(" ")[0], "%Y-%m-%d").date()
                        if start_date <= date_obj <= end_date:
                            if date_obj not in data: data[date_obj] = []
                            data[date_obj].append((ts, mins, task))
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Błąd parsowania linii {line_num}: {e}")
        except IOError as e:
            self.logger.error(f"Błąd odczytu historii z CSV: {e}")
        return data

    def export_history(self) -> None:
        try:
            start_date_str, end_date_str = self.start_date_var.get(), self.end_date_var.get()
            filename = filedialog.asksaveasfilename(
                initialfile=f"historia_{start_date_str}_do_{end_date_str}.csv",
                defaultextension=".csv", filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")],
                title="Eksportuj historię do CSV"
            )
            if not filename: return
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            data = self.load_history_data(start_date, end_date)
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Data", "Czas", "Minuty", "Zadanie"])
                for date_obj in sorted(data.keys()):
                    for ts, mins, task in data[date_obj]:
                        date_part, time_part = (ts.split(' ')[0], ts.split(' ')[1]) if ' ' in ts else (ts, '')
                        writer.writerow([date_part, time_part, mins, task])
            messagebox.showinfo("Sukces", f"Historia wyeksportowana do:\n{filename}")
        except Exception as e:
            self.logger.error(f"Błąd eksportu: {e}")
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas eksportu: {e}")

    # ==========================================================================
    #  Obsługa Zamykania (Closing Handler)
    # ==========================================================================

    def on_closing(self) -> None:
        if self.is_running and not messagebox.askyesno("Potwierdzenie", "Stoper jest uruchomiony.\nCzy na pewno chcesz zakończyć?"):
            return
        if self.counter > 60 and not self.config.get('auto_save', False):
            if messagebox.askyesno("Zapisz", f"Masz {int(self.counter//60)} minut na stoperze.\nCzy zapisać przed wyjściem?"):
                self.add_to_log()
        
        if self.status_popup and self.status_popup.winfo_exists(): self.status_popup.destroy()
        self.hide_reminder()
        
        self.logger.info("Aplikacja zamknięta.")
        self.root.destroy()

# ==============================================================================
#  Główny Punkt Wejścia (Main Entry Point)
# ==============================================================================

def main():
    try:
        root = tk.Tk()
        # root.iconbitmap('path/to/icon.ico')
        app = StopwatchApp(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Krytyczny błąd aplikacji: {e}", exc_info=True)
        messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd krytyczny:\n{e}\n\nAplikacja zostanie zamknięta.")

if __name__ == "__main__":
    main()
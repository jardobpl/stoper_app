import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import os
import json
import locale
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

POLISH_DAYS_MAPPING = {
    'Monday': 'poniedziałek',
    'Tuesday': 'wtorek',
    'Wednesday': 'środa', 
    'Thursday': 'czwartek',
    'Friday': 'piątek',
    'Saturday': 'sobota',
    'Sunday': 'niedziela'
}

class StopwatchApp:
    """Enhanced stopwatch application with improved architecture and features."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Stoper Pro")
        # Zmieniona wysokość okna (z 620 na około 496, czyli ~20% mniej)
        self.root.geometry("500x496")
        
        # Core state
        self.is_running = False
        self.counter = 0
        self.start_time: Optional[datetime] = None
        self.last_reminder_time: Optional[float] = None
        self.reminder_window: Optional[tk.Toplevel] = None
        self.current_task: str = ""
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration with validation
        self.config = self.load_config()
        self.daily_goal = self.config.get('daily_goal', 180)
        
        # Setup locale
        self.setup_locale()
        
        # Initialize UI and functionality
        self.setup_ui()
        self.setup_keybindings()
        self.setup_menu()
        
        # Start background tasks
        self.update_display()
        self.reminder_check()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.center_window()

    def center_window(self) -> None:
        """Center the main application window on the screen."""
        self.root.update_idletasks()  # Ensure window dimensions are updated
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        self.root.geometry(f'+{x}+{y}')

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        log_path = self.get_app_path() / "app.log"
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
        """Get application directory path."""
        return Path(__file__).parent

    def setup_locale(self) -> None:
        """Setup Polish locale with fallbacks and proper encoding."""
        import sys
        import platform
        
        # Ustaw kodowanie dla Windows
        if platform.system() == "Windows":
            try:
                # Dla Windows, ustaw kodowanie konsoli
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except:
                pass
        
        # Lista locale do wypróbowania w zależności od systemu
        if platform.system() == "Windows":
            locales_to_try = ['Polish_Poland.1250', 'Polish_Poland.utf8', 'pl_PL.UTF-8', 'pl_PL', 'pl']
        else:
            locales_to_try = ['pl_PL.UTF-8', 'pl_PL.utf8', 'pl_PL', 'pl', 'C.UTF-8']
        
        locale_set = False
        for loc in locales_to_try:
            try:
                locale.setlocale(locale.LC_ALL, loc)
                self.logger.info(f"Locale set to: {loc}")
                locale_set = True
                break
            except locale.Error:
                continue
        
        if not locale_set:
            self.logger.warning("Could not set Polish locale, using default")
            self.use_custom_day_names = True
        else:
            self.use_custom_day_names = False

    def get_polish_day_name(self, date_obj: datetime.date) -> str:
        """Get Polish day name with proper encoding."""
        polish_days = {
            0: 'poniedziałek',
            1: 'wtorek', 
            2: 'środa',
            3: 'czwartek',
            4: 'piątek',
            5: 'sobota',
            6: 'niedziela'
        }
        
        if hasattr(self, 'use_custom_day_names') and self.use_custom_day_names:
            return polish_days.get(date_obj.weekday(), 'nieznany')
        else:
            try:
                # Spróbuj użyć locale
                day_name = date_obj.strftime('%A')
                # Sprawdź czy nazwa zawiera dziwne znaki
                if 'Ĺ' in day_name or '‚' in day_name:
                    return polish_days.get(date_obj.weekday(), 'nieznany')
                return day_name
            except:
                return polish_days.get(date_obj.weekday(), 'nieznany')

    def update_time_color(self) -> None:
        """Dynamicznie zmienia kolor czasu w zależności od stanu."""
        if self.is_running:
            # Gdy stoper działa - ciemnozielony
            color = "#27AE60"
        elif self.counter > 0:
            # Gdy zatrzymany ale ma czas - pomarańczowy
            color = "#E67E22"
        else:
            # Gdy zresetowany - ciemnoniebieski
            color = "#2E86AB"
        
        self.time_label.config(fg=color)    

    def load_config(self) -> Dict:
        """Load configuration with comprehensive validation."""
        config_path = self.get_app_path() / "config.json"
        default_config = {
            'daily_goal': 180,
            'reminder_interval': 120,
            'reminder_duration': 15000,
            'auto_save': True,
            'sound_enabled': False,
            'window_always_on_top': False,
            'theme': 'default'
        }
        
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
                # Validate and merge with defaults
                validated_config = self.validate_config(config, default_config)
                return validated_config
            else:
                self.save_config(default_config)
                return default_config
                
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Configuration loading error: {e}")
            messagebox.showerror("Błąd", f"Błąd ładowania konfiguracji: {e}\nUżywam ustawień domyślnych.")
            return default_config

    def validate_config(self, config: Dict, default_config: Dict) -> Dict:
        """Validate configuration values."""
        validated = default_config.copy()
        
        for key, default_value in default_config.items():
            if key in config:
                value = config[key]
                if key in ['daily_goal', 'reminder_interval', 'reminder_duration']:
                    if isinstance(value, int) and value > 0:
                        validated[key] = value
                    else:
                        self.logger.warning(f"Invalid value for {key}: {value}, using default")
                elif key in ['auto_save', 'sound_enabled', 'window_always_on_top']:
                    validated[key] = bool(value)
                elif key == 'theme' and isinstance(value, str):
                    validated[key] = value
                else:
                    validated[key] = value
        
        return validated

    def save_config(self, config: Optional[Dict] = None) -> bool:
        """Save configuration with error handling."""
        if config is None:
            config = self.config
        
        config_path = self.get_app_path() / "config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("Configuration saved successfully")
            return True
        except IOError as e:
            self.logger.error(f"Failed to save configuration: {e}")
            messagebox.showerror("Błąd", f"Nie można zapisać konfiguracji: {e}")
            return False

    def setup_menu(self) -> None:
        """Setup application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plik", menu=file_menu)
        file_menu.add_command(label="Eksportuj dane...", command=self.export_data)
        file_menu.add_command(label="Importuj dane...", command=self.import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Wyjście", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Narzędzia", menu=tools_menu)
        tools_menu.add_command(label="Konfiguracja", command=self.show_config)
        tools_menu.add_command(label="Historia", command=self.show_history)
        tools_menu.add_command(label="Statystyki", command=self.show_statistics)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Pomoc", menu=help_menu)
        help_menu.add_command(label="Skróty klawiszowe", command=self.show_shortcuts)
        help_menu.add_command(label="O aplikacji", command=self.show_about)

    def setup_ui(self) -> None:
        """Create enhanced user interface."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="5") # Zmniejszone padding 
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Time display with better styling
        self.time_label = tk.Label(
            main_frame, 
            text="00:00:00", 
            font=("Helvetica", 38, "bold"), # Zmniejszony rozmiar czcionki (z 48 na 38) 
            fg="#2E86AB",  # NOWY KOLOR - niebieski morski
            bg=self.root.cget('bg')
        )
        self.time_label.grid(row=0, column=0, pady=10, sticky=tk.EW) # Zmniejszone pady (z 20 na 10) 

        task_frame = ttk.LabelFrame(main_frame, text="Zadanie", padding="5") # Zmniejszone padding 
        task_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5) # Zmniejszone pady (z 10 na 5) 
        task_frame.columnconfigure(0, weight=1)
        
        self.task_var = tk.StringVar(value=self.current_task)
        self.task_entry = ttk.Entry(task_frame, textvariable=self.task_var, font=("Helvetica", 9)) # Zmniejszony rozmiar czcionki (z 11 na 9) 
        self.task_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        self.task_entry.bind('<Return>', lambda e: self.start())

        # Control buttons frame
        controls_frame = ttk.LabelFrame(main_frame, text="Kontrola", padding="5") # Zmniejszone padding 
        controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5) # Zmniejszone pady (z 10 na 5) 
        controls_frame.columnconfigure((0, 1, 2, 3), weight=1)

        # Main control buttons with colors
        self.start_button = tk.Button(controls_frame, text="Start", command=self.start, bg="#27AE60", fg="white", font=("Helvetica", 9, "bold"), activebackground="#2ECC71", pady=4) # Zmniejszony rozmiar czcionki (z 10 na 9), pady (z 8 na 4) 
        self.start_button.grid(row=0, column=0, padx=5, sticky=tk.EW)

        self.pause_button = tk.Button(controls_frame, text="Pauza", command=self.stop, bg="#F39C12", fg="white", font=("Helvetica", 9, "bold"), activebackground="#E67E22", pady=4) # Zmniejszony rozmiar czcionki (z 10 na 9), pady (z 8 na 4) 
        self.pause_button.grid(row=0, column=1, padx=5, sticky=tk.EW)

        self.reset_button = tk.Button(controls_frame, text="Reset", command=self.reset, bg="#F44336", fg="white", font=("Helvetica", 9, "bold"), pady=4) # Zmniejszony rozmiar czcionki (z 10 na 9), pady (z 8 na 4) 
        self.reset_button.grid(row=0, column=2, padx=5, sticky=tk.EW)

        self.add_button = tk.Button(controls_frame, text="Zapisz", command=self.add_to_log, bg="#2196F3", fg="white", font=("Helvetica", 9, "bold"), pady=4) # Zmniejszony rozmiar czcionki (z 10 na 9), pady (z 8 na 4) 
        self.add_button.grid(row=0, column=3, padx=5, sticky=tk.EW)

        # Time adjustment frame
        adjust_frame = ttk.LabelFrame(main_frame, text="Korekta czasu", padding="5") # Zmniejszone padding 
        adjust_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5) # Zmniejszone pady (z 10 na 5) 
        adjust_frame.columnconfigure((0, 1, 2, 3), weight=1)

        # Time adjustment buttons
        ttk.Button(adjust_frame, text="+5 min", command=lambda: self.adjust_time(30000)).grid(row=0, column=0, padx=2, sticky=tk.EW)
        ttk.Button(adjust_frame, text="+1 min", command=lambda: self.adjust_time(6000)).grid(row=0, column=1, padx=2, sticky=tk.EW)
        ttk.Button(adjust_frame, text="-1 min", command=lambda: self.adjust_time(-6000)).grid(row=0, column=2, padx=2, sticky=tk.EW)
        ttk.Button(adjust_frame, text="-5 min", command=lambda: self.adjust_time(-30000)).grid(row=0, column=3, padx=2, sticky=tk.EW)

        # Information frame
        info_frame = ttk.LabelFrame(main_frame, text="Informacje", padding="5") # Zmniejszone padding 
        info_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5) # Zmniejszone pady (z 10 na 5) 

        # Start time label
        self.start_time_label = ttk.Label(info_frame, text="Czas startu: --")
        self.start_time_label.grid(row=0, column=0, sticky=tk.W, pady=1) # Zmniejszone pady (z 2 na 1) 

        # Progress frame
        progress_frame = ttk.Frame(info_frame)
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2) # Zmniejszone pady (z 5 na 2) 
        progress_frame.columnconfigure(0, weight=1)

        # Progress label and bar
        self.progress_label = ttk.Label(progress_frame, text="Postęp dnia")
        self.progress_label.grid(row=0, column=0, sticky=tk.W)

        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient="horizontal", 
            mode="determinate"
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=1) # Zmniejszone pady (z 2 na 1) 

        self.sum_label = ttk.Label(info_frame, text="Suma: 0 min (0.00%)", font=("Helvetica", 10, "bold")) # Zmniejszony rozmiar czcionki (z 12 na 10) 
        self.sum_label.grid(row=2, column=0, sticky=tk.W, pady=1) # Zmniejszone pady (z 2 na 1) 

        # Quick actions frame
        quick_frame = ttk.LabelFrame(main_frame, text="Szybkie akcje", padding="5") # Zmniejszone padding 
        quick_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5) # Zmniejszone pady (z 10 na 5) 
        quick_frame.columnconfigure((0, 1), weight=1)

        ttk.Button(quick_frame, text="Historia", command=self.show_history).grid(row=0, column=0, padx=5, sticky=tk.EW)
        ttk.Button(quick_frame, text="Statystyki", command=self.show_statistics).grid(row=0, column=1, padx=5, sticky=tk.EW)

        # Create status indicator
        self.create_status_indicator()

    def adjust_time(self, centiseconds: int) -> None:
        """Adjust time by specified centiseconds."""
        self.counter = max(0, self.counter + centiseconds)
        self.refresh_time_label()
        self.logger.info(f"Time adjusted by {centiseconds/6000:.1f} minutes")

    def setup_keybindings(self) -> None:
        """Setup comprehensive keyboard shortcuts."""
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

    def toggle_start_stop(self) -> None:
        """Toggle between start and stop."""
        if self.is_running:
            self.stop()
        else:
            self.start()

    def create_status_indicator(self) -> None:
        """Create modern status indicator."""
        self.status_popup = tk.Toplevel(self.root)
        self.status_popup.overrideredirect(True)
        self.status_popup.attributes("-topmost", True)
        self.status_popup.attributes("-alpha", 0.9)

        # Position in bottom-right corner with smaller size
        size = 21 # Zmniejszony rozmiar (z 21 na 17) 
        offset_x = 15 # Zmniejszony offset
        offset_y = 40 # Zmniejszony offset
        x = self.root.winfo_screenwidth() - size - offset_x
        y = self.root.winfo_screenheight() - size - offset_y
        self.status_popup.geometry(f"{size}x{size}+{x}+{y}")

        # Status frame
        self.status_frame = tk.Frame(self.status_popup, relief=tk.RAISED, bd=1)
        self.status_frame.pack(fill=tk.BOTH, expand=True)

        # Only minutes display (no symbol needed in such small space)
        self.status_time_label = tk.Label(
            self.status_frame,
            text="0",
            fg="white",
            font=("Helvetica", 8, "bold") 
        )
        self.status_time_label.pack(expand=True)

    def update_display(self) -> None:
        """Main display update loop with better performance."""
        if self.is_running:
            self.counter += 1
            
        # Update displays
        self.refresh_time_label()
        self.update_time_color()
        self.update_status_indicator()
        
        # Update progress less frequently
        if self.counter % 600 == 0:  # Every 6 seconds
            self.update_progress()
        
        # Schedule next update
        self.root.after(10, self.update_display)

    def update_status_indicator(self) -> None:
        """Update status indicator."""
        if hasattr(self, 'status_frame') and hasattr(self, 'status_time_label'):
            minutes = self.counter // 6000
            
            # Change background color based on running state
            if self.is_running:
                bg_color = "#4CAF50"  # Green when running
            else:
                bg_color = "#F44336"  # Red when stopped
            
            self.status_frame.config(bg=bg_color)
            self.status_time_label.config(bg=bg_color, text=str(minutes))

    def update_progress(self) -> None:
        """Update progress information."""
        total_minutes = self.read_and_sum_today()
        current_minutes = self.counter // 6000
        total_with_current = total_minutes + current_minutes
        
        percentage = (total_with_current / self.daily_goal) * 100
        
        # Update progress bar
        self.progress_bar["value"] = min(percentage, 100)
        
        # Update color based on progress
        # color = self.get_color_by_percentage(percentage / 100)
        current_bar_color = self.update_progress_color()
        
        # Update labels
        self.sum_label.config(
            text=f"Suma: {total_with_current} min ({percentage:.1f}% celu: {self.daily_goal} min)",
            foreground=current_bar_color
        )

    def get_color_by_percentage(self, pct: float) -> str:
        """Get color based on progress percentage with smooth transitions."""
        if pct < 0.25:
            return "#FF4444"  # Red
        elif pct < 0.5:
            return "#FF8800"  # Orange  
        elif pct < 0.75:
            return "#FFDD00"  # Yellow
        elif pct < 1.0:
            return "#88DD00"  # Light green
        else:
            return "#00AA00"  # Green

    def update_progress_color(self) -> str:
        """Aktualizuje kolor paska postępu."""
        total_minutes = self.read_and_sum_today()
        current_minutes = self.counter // 6000
        total_with_current = total_minutes + current_minutes
        percentage = (total_with_current / self.daily_goal) * 100
        
        # Konfiguruj styl paska postępu
        style = ttk.Style()
        
        if percentage < 25:
            color = "#E74C3C"  # Czerwony
        elif percentage < 50:
            color = "#F39C12"  # Pomarańczowy
        elif percentage < 75:
            #color = "#F1C40F"  # Żółty
            # color = "#008080"  # Ciemny turkus
            color = "#800080"  # Ciemny fiolet
        elif percentage < 100:
            color = "#2ECC71"  # Jasnozielony
        else:
            color = "#27AE60"  # Ciemnozielony
        
        style.configure("Custom.Horizontal.TProgressbar", 
            troughcolor='#ECF0F1', 
            background=color)
        
        self.progress_bar.configure(style="Custom.Horizontal.TProgressbar")
        
        return color

    def refresh_time_label(self) -> None:
        """Refresh time display with better formatting."""
        formatted_time = self.format_time(self.counter)
        self.time_label.config(text=formatted_time)
        
        # Update window title with current time
        minutes = self.counter // 6000
        status = "▶" if self.is_running else "⏸"
        self.root.title(f"Stoper Pro - {status} {minutes}m")
            
    def format_time(self, count: int) -> str:
        """Format time in HH:MM:SS format always."""
        total_seconds = count // 100
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        # Zawsze wyświetlaj w formacie HH:MM:SS
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def start(self) -> None:
        """Start the stopwatch with improved state management."""
        if not self.is_running:
            # Zapisz opis zadania
            self.current_task = self.task_var.get().strip()
            
            self.is_running = True
            if self.start_time is None:
                self.start_time = datetime.now()
                self.refresh_start_time_label()
            
            self.logger.info(f"Stopwatch started - Task: {self.current_task}")
            self.start_button.config(text="Uruchomiony", state="disabled")
            self.pause_button.config(state="normal")
            
            # Zablokuj pole zadania podczas działania stopera
            self.task_entry.config(state="disabled")
        
            # Hide reminder if visible
            self.hide_reminder()

    def stop(self) -> None:
        """Stop/pause the stopwatch."""
        if self.is_running:
            self.is_running = False
            self.logger.info("Stopwatch paused")
            self.start_button.config(text="Wznów", state="normal")
            self.pause_button.config(state="disabled")
            
            # Odblokuj pole zadania
            self.task_entry.config(state="normal")

    def reset(self) -> None:
        """Reset stopwatch with confirmation for long sessions."""
        if self.counter > 60000:  # More than 10 minutes
            if not messagebox.askyesno("Potwierdzenie", 
                f"Czy na pewno chcesz zresetować {self.counter//6000} minut?"):
                return
        
        self.is_running = False
        self.counter = 0
        self.start_time = None
        self.current_task = ""
        self.task_var.set("")
        
        self.refresh_time_label()
        self.refresh_start_time_label()
        self.update_progress()
        
        self.start_button.config(text="Start", state="normal")
        self.pause_button.config(state="normal")
        self.task_entry.config(state="normal")
        
        self.logger.info("Stopwatch reset")

    def refresh_start_time_label(self) -> None:
        """Refresh start time display."""
        if self.start_time is None:
            self.start_time_label.config(
                text="Czas startu: --",
                foreground="#7F8C8D"  # Szary dla braku danych
            )
        else:
            formatted = self.start_time.strftime("%H:%M:%S")
            duration = datetime.now() - self.start_time
            
            if hasattr(self, 'start_time_label'):
                self.start_time_label.config(
                    text=f"Start: {formatted} (przed {self.format_duration(duration)})",
                    foreground="#8E44AD"  # Fioletowy dla aktywnego czasu
                )

    def format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable format."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def show_statistics(self) -> None:
        """Show comprehensive statistics window."""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Statystyki")
        # Zmniejszona wysokość okna statystyk (z 500 na 400)
        stats_window.geometry("700x400")
        stats_window.transient(self.root)
        
        # Create notebook for different stats views
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Weekly stats
        weekly_frame = ttk.Frame(notebook)
        notebook.add(weekly_frame, text="Tydzień")
        self.create_weekly_stats(weekly_frame)
        
        # Monthly stats  
        monthly_frame = ttk.Frame(notebook)
        notebook.add(monthly_frame, text="Miesiąc")
        self.create_monthly_stats(monthly_frame)
        
        # Trends
        trends_frame = ttk.Frame(notebook)
        notebook.add(trends_frame, text="Trendy")
        self.create_trends_stats(trends_frame)

    def create_weekly_stats(self, parent: ttk.Frame) -> None:
        """Create weekly statistics view."""
        label = ttk.Label(parent, text="Statystyki tygodniowe będą dostępne w następnej wersji")
        label.pack(pady=20)

    def create_monthly_stats(self, parent: ttk.Frame) -> None:
        """Create monthly statistics view."""
        label = ttk.Label(parent, text="Statystyki miesięczne będą dostępne w następnej wersji")
        label.pack(pady=20)

    def create_trends_stats(self, parent: ttk.Frame) -> None:
        """Create trends statistics view."""
        label = ttk.Label(parent, text="Analiza trendów będzie dostępna w następnej wersji")
        label.pack(pady=20)

    def show_shortcuts(self) -> None:
        """Show keyboard shortcuts dialog."""
        shortcuts = """
Skróty klawiszowe:

Ctrl+S          - Start stopera
Ctrl+P          - Pauza
Ctrl+R          - Reset
Ctrl+Enter      - Zapisz do logu
Ctrl+H          - Historia
Ctrl+,          - Konfiguracja
Ctrl+T          - Statystyki
F1              - Ta pomoc
Spacja          - Start/Pauza
Escape          - Reset
        """
        messagebox.showinfo("Skróty klawiszowe", shortcuts)

    def show_about(self) -> None:
        """Show about dialog."""
        about_text = """
Stoper Pro v2.0

Zaawansowana aplikacja do śledzenia czasu
z funkcjami analizy i raportowania.
Autor: Ulepszona wersja
Data: 2025
        """
        messagebox.showinfo("O aplikacji", about_text)

    def export_data(self) -> None:
        """Export data to different formats."""
        messagebox.showinfo("Eksport", "Funkcja eksportu będzie dostępna w następnej wersji")

    def import_data(self) -> None:
        """Import data from file."""
        messagebox.showinfo("Import", "Funkcja importu będzie dostępna w następnej wersji")

    def add_to_log(self) -> None:
        """Enhanced log addition with validation and auto-save."""
        minutes = self.counter // 6000
        
        # Don't save if less than 1 minute
        if minutes < 1:
            messagebox.showwarning("Uwaga", "Czas musi wynosić co najmniej 1 minutę aby zapisać.")
            return
            
        self.stop()
        
        # Save to log
        if self.save_to_log(minutes):
            messagebox.showinfo("Sukces", f"Zapisano {minutes} minut do logu.")
            
            # Always reset after save
            self.reset()
            self.update_progress()
        else:
            messagebox.showerror("Błąd", "Nie udało się zapisać do logu.")

    def save_to_log(self, minutes: int) -> bool:
        """Save time entry to log file with improved error handling."""
        log_path = self.get_app_path() / "wynik.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        task_desc = self.current_task if self.current_task.strip() else "Bez opisu"  # POPRAWKA: użyj self.current_task
        
        try:
            # Create backup if file exists
            if log_path.exists() and log_path.stat().st_size > 1024:  # If file > 1KB
                backup_path = log_path.with_suffix('.bak')
                import shutil
                shutil.copy2(log_path, backup_path)
            
            # Append new entry
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{timestamp}\t{minutes}\t{task_desc}\n")
            
            self.logger.info(f"Saved {minutes} minutes to log - Task: {task_desc}")
            return True
            
        except IOError as e:
            self.logger.error(f"Failed to save to log: {e}")
            return False

    def read_and_sum_today(self) -> int:		
        """Read and sum today's minutes with better error handling."""
        log_path = self.get_app_path() / "wynik.txt"
        
        if not log_path.exists():
            return 0
        
        total = 0
        today = datetime.now().date()
        
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split("\t")
                    if len(parts) < 2:  # ZMIENIONE z != 2 na < 2
                        self.logger.warning(f"Invalid format in line {line_num}: {line}")
                        continue
                    
                    try:
                        date_str = parts[0].split(" ")[0]
                        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        
                        if entry_date == today:
                            total += int(parts[1])
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Error parsing line {line_num}: {e}")
                        continue
        except IOError as e:
            self.logger.error(f"Error reading log file: {e}")
        return total

    def reminder_check(self) -> None:
        """Enhanced reminder system with smart timing."""
        if not self.is_running:
            now = datetime.now().timestamp()
            interval = self.config.get('reminder_interval', 120)
            # Only show reminder if enough time has passed and we're not already showing one
            if (self.last_reminder_time is None or now - self.last_reminder_time >= interval) and \
            (self.reminder_window is None or not self.reminder_window.winfo_exists()):
                self.last_reminder_time = now
                self.show_reminder()
        # Check every 30 seconds instead of every second
        self.root.after(30000, self.reminder_check)

    def show_reminder(self) -> None:
        """Show modern reminder notification."""
        self.hide_reminder() # Hide any existing reminder
        self.reminder_window = tk.Toplevel(self.root)
        self.reminder_window.overrideredirect(True)
        self.reminder_window.attributes("-topmost", True)
        self.reminder_window.attributes("-alpha", 0.95)

        # Position at top-right corner with reduced size
        width, height = 240, 64 # Zmniejszone rozmiary (z 300x80 na 240x64) 
        x = self.root.winfo_screenwidth() - width - 15 # Zmniejszony offset
        y = self.root.winfo_screenheight() - height - 30 # Zmniejszony offset
        self.reminder_window.geometry(f"{width}x{height}+{x}+{y}")

        # Create modern looking notification
        main_frame = tk.Frame(self.reminder_window, bg='#2C3E50', relief=tk.RAISED, bd=2)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(
            main_frame, 
            text="⏱ Przypomnienie", 
            font=("Helvetica", 10, "bold"), # Zmniejszony rozmiar czcionki (z 12 na 10) 
            bg='#2C3E50', 
            fg='white'
        )
        title_label.pack(pady=3) # Zmniejszone pady 

        # Message
        msg_label = tk.Label(
            main_frame, 
            text="Uruchom stoper aby kontynuować pracę!", 
            font=("Helvetica", 8), # Zmniejszony rozmiar czcionki (z 10 na 8) 
            bg='#2C3E50', 
            fg='#ECF0F1'
        )
        msg_label.pack()

        # Close button
        close_btn = tk.Button(
            main_frame, 
            text="×", 
            command=self.hide_reminder, 
            bg='#E74C3C', 
            fg='white', 
            font=("Helvetica", 10, "bold"), # Zmniejszony rozmiar czcionki (z 12 na 10) 
            relief=tk.FLAT, 
            width=2 # Zmniejszona szerokość
        )
        close_btn.place(x=width-25, y=3) # Dostosowana pozycja przycisku

        # Auto-hide after duration
        duration = self.config.get('reminder_duration', 15000)
        self.root.after(duration, self.hide_reminder)

    def hide_reminder(self) -> None:
        """Hide reminder window."""
        if self.reminder_window and self.reminder_window.winfo_exists():
            self.reminder_window.destroy()
            self.reminder_window = None

    def show_config(self) -> None:
        """Show enhanced configuration dialog."""
        config_window = tk.Toplevel(self.root)
        config_window.title("Konfiguracja")
        config_window.geometry("500x320") # Zmniejszona wysokość okna konfiguracji (z 400 na 320) 
        config_window.transient(self.root)
        config_window.grab_set()

        # Create notebook for different config sections
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Zmniejszone pady 

        # General settings
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="Ogólne")
        self.create_general_config(general_frame)

        # Reminder settings
        reminder_frame = ttk.Frame(notebook)
        notebook.add(reminder_frame, text="Przypomnienia")
        self.create_reminder_config(reminder_frame)

        # Appearance settings
        appearance_frame = ttk.Frame(notebook)
        notebook.add(appearance_frame, text="Wygląd")
        self.create_appearance_config(appearance_frame)

        # Buttons frame
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=5, pady=5) # Zmniejszone pady 
        ttk.Button(
            button_frame, 
            text="Zapisz", 
            command=lambda: self.save_config_dialog(config_window)
        ).pack(side=tk.RIGHT, padx=3) # Zmniejszone padx 
        ttk.Button(
            button_frame, 
            text="Anuluj", 
            command=config_window.destroy
        ).pack(side=tk.RIGHT)

    def create_general_config(self, parent: ttk.Frame) -> None:
        """Create general configuration section."""
        # Daily goal
        ttk.Label(parent, text="Cel dzienny (minuty):").grid(row=0, column=0, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 
        self.goal_var = tk.StringVar(value=str(self.daily_goal))
        goal_spinbox = ttk.Spinbox(parent, from_=30, to=1440, textvariable=self.goal_var, width=8) # Zmniejszona szerokość 
        goal_spinbox.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

        # Auto-save option
        self.auto_save_var = tk.BooleanVar(value=self.config.get('auto_save', True))
        ttk.Checkbutton(
            parent, 
            text="Automatyczny reset po zapisie", 
            variable=self.auto_save_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

        # Always on top option
        self.always_on_top_var = tk.BooleanVar(value=self.config.get('window_always_on_top', False))
        ttk.Checkbutton(
            parent, 
            text="Okno zawsze na wierzchu", 
            variable=self.always_on_top_var
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

    def create_reminder_config(self, parent: ttk.Frame) -> None:
        """Create reminder configuration section."""
        # Reminder interval
        ttk.Label(parent, text="Interwał przypomnień (sekundy):").grid(row=0, column=0, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 
        self.reminder_interval_var = tk.StringVar(value=str(self.config.get('reminder_interval', 120)))
        interval_spinbox = ttk.Spinbox(parent, 
                                        from_=30, 
                                        to=3600, 
                                        textvariable=self.reminder_interval_var, 
                                        width=8) # Zmniejszona szerokość 
        interval_spinbox.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

        # Reminder duration
        ttk.Label(parent, text="Czas wyświetlania (ms):").grid(row=1, column=0, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 
        self.reminder_duration_var = tk.StringVar(value=str(self.config.get('reminder_duration', 15000)))
        duration_spinbox = ttk.Spinbox(parent, from_=5000, to=60000, textvariable=self.reminder_duration_var, width=8) # Zmniejszona szerokość 
        duration_spinbox.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

        # Sound enabled
        self.sound_enabled_var = tk.BooleanVar(value=self.config.get('sound_enabled', False))
        ttk.Checkbutton(
            parent, 
            text="Dźwięk przypomnień", 
            variable=self.sound_enabled_var
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

    def create_appearance_config(self, parent: ttk.Frame) -> None:
        """Create appearance configuration section."""
        # Theme selection
        ttk.Label(parent, text="Motyw:").grid(row=0, column=0, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 
        self.theme_var = tk.StringVar(value=self.config.get('theme', 'default'))
        theme_combo = ttk.Combobox(parent, textvariable=self.theme_var, values=['default', 'dark', 'light'], state='readonly', width=8) # Zmniejszona szerokość 
        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5) # Zmniejszone pady 

    def save_config_dialog(self, window: tk.Toplevel) -> None:
        """Save configuration from dialog."""
        try:
            new_goal = int(self.goal_var.get())
            new_interval = int(self.reminder_interval_var.get())
            new_duration = int(self.reminder_duration_var.get())
            if new_goal <= 0 or new_interval <= 0 or new_duration <= 0:
                raise ValueError("Wszystkie wartości muszą być większe od zera")

            # Update configuration
            self.daily_goal = new_goal
            self.config.update({
                'daily_goal': new_goal,
                'reminder_interval': new_interval,
                'reminder_duration': new_duration,
                'auto_save': self.auto_save_var.get(),
                'sound_enabled': self.sound_enabled_var.get(),
                'window_always_on_top': self.always_on_top_var.get(),
                'theme': self.theme_var.get()
            })

            # Apply settings
            self.apply_config_changes()
            if self.save_config():
                window.destroy()
                messagebox.showinfo("Sukces", "Konfiguracja została zapisana!")
        except ValueError as e:
            messagebox.showerror("Błąd", f"Nieprawidłowa wartość: {e}")

    def apply_config_changes(self) -> None:
        """Apply configuration changes to the application."""
        # Apply always on top setting
        self.root.attributes("-topmost", self.config.get('window_always_on_top', False))
        # Update progress display
        self.update_progress()

    def show_history(self) -> None:
        """Show enhanced history window with filtering and export options."""
        history_window = tk.Toplevel(self.root)
        history_window.title("Historia")
        history_window.geometry("800x480") # Zmniejszona wysokość okna historii (z 600 na 480) 
        history_window.transient(self.root)

        # Control frame
        control_frame = ttk.Frame(history_window)
        control_frame.pack(fill=tk.X, padx=5, pady=3) # Zmniejszone pady 

        # Days filter
        ttk.Label(control_frame, text="Liczba dni:").pack(side=tk.LEFT, padx=3) # Zmniejszone padx 
        self.days_var = tk.StringVar(value="7")
        days_spinbox = ttk.Spinbox(control_frame, from_=1, to=365, textvariable=self.days_var, width=6) # Zmniejszona szerokość 
        days_spinbox.pack(side=tk.LEFT, padx=3) # Zmniejszone padx 

        # Date range filter
        ttk.Label(control_frame, text="Od:").pack(side=tk.LEFT, padx=(10, 3)) # Zmniejszone padx 
        self.start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        start_date_entry = ttk.Entry(control_frame, textvariable=self.start_date_var, width=10) # Zmniejszona szerokość 
        start_date_entry.pack(side=tk.LEFT, padx=3) # Zmniejszone padx 
        ttk.Label(control_frame, text="Do:").pack(side=tk.LEFT, padx=3) # Zmniejszone padx 
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_date_entry = ttk.Entry(control_frame, textvariable=self.end_date_var, width=10) # Zmniejszona szerokość 
        end_date_entry.pack(side=tk.LEFT, padx=3) # Zmniejszone padx 

        # Buttons
        ttk.Button(
            control_frame, 
            text="Odśwież", 
            command=lambda: self.refresh_history(text_widget)
        ).pack(side=tk.LEFT, padx=5) # Zmniejszone padx 
        ttk.Button(
            control_frame, 
            text="Eksportuj", 
            command=self.export_history
        ).pack(side=tk.LEFT, padx=3) # Zmniejszone padx 

        # Text display with scrollbar
        text_frame = ttk.Frame(history_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Zmniejszone pady 
		
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Initial display
        self.refresh_history(text_widget)

    def refresh_history(self, text_widget: tk.Text) -> None:
        """Refresh history display with enhanced formatting and proper Polish characters."""
        text_widget.delete(1.0, tk.END)
        
        # Konfiguracja tagów kolorów
        text_widget.tag_config("header", foreground="#2C3E50", font=("Helvetica", 12, "bold"))
        text_widget.tag_config("date_good", foreground="#27AE60", font=("Helvetica", 11, "bold"))
        text_widget.tag_config("date_bad", foreground="#E74C3C", font=("Helvetica", 11, "bold"))
        text_widget.tag_config("time_entry", foreground="#3498DB")
        text_widget.tag_config("task_desc", foreground="#8E44AD", font=("Helvetica", 9, "italic"))
        text_widget.tag_config("summary", foreground="#D35400", font=("Helvetica", 10, "bold"))
        
        try:
            days = int(self.days_var.get())
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            text_widget.insert(tk.END, "Błąd: Nieprawidłowy format daty lub liczby dni.")
            return

        # Load and process data
        data = self.load_history_data(start_date, end_date)
        
        if not data:
            text_widget.insert(tk.END, "Brak danych w wybranym okresie.")
            return

        # Display header
        text_widget.insert(tk.END, f"HISTORIA PRACY - {start_date} do {end_date}\n")
        text_widget.insert(tk.END, f"Cel dzienny: {self.daily_goal} minut\n")
        text_widget.insert(tk.END, "=" * 80 + "\n\n")

        # Display daily summaries
        total_minutes = 0
        total_days = 0
        goal_achieved_days = 0

        for date_obj in sorted(data.keys(), reverse=True):
            day_entries = data[date_obj]
            day_total = sum(entry[1] for entry in day_entries)
            total_minutes += day_total
            total_days += 1
            
            percentage = (day_total / self.daily_goal) * 100
            status = "✅" if day_total >= self.daily_goal else "❌"
            
            if day_total >= self.daily_goal:
                goal_achieved_days += 1

            # UŻYWA poprawionej metody
            day_name = self.get_polish_day_name(date_obj)
            formatted_date = f"{day_name}, {date_obj.strftime('%d.%m.%Y')}"

            text_widget.insert(tk.END, f"{formatted_date} {status}\n")
            text_widget.insert(tk.END, f"  📊 Suma: {day_total:3d} min ({percentage:5.1f}% celu)\n")
            
            # Show individual entries with task description
            for entry in day_entries:
                timestamp = entry[0]
                minutes = entry[1]
                task_desc = entry[2] if len(entry) > 2 else "Bez opisu"
                
                time_part = timestamp.split(' ')[1] if ' ' in timestamp else timestamp
                text_widget.insert(tk.END, f"    🕐 {time_part} - {minutes:3d} min - {task_desc}\n")

        # Display summary statistics
        if total_days > 0:
            avg_daily = total_minutes / total_days
            success_rate = (goal_achieved_days / total_days) * 100
            
            text_widget.insert(tk.END, "=" * 80 + "\n")
            text_widget.insert(tk.END, "📈 PODSUMOWANIE STATYSTYCZNE\n")
            text_widget.insert(tk.END, "=" * 80 + "\n")
            text_widget.insert(tk.END, f"📅 Okres: {total_days} dni\n")
            text_widget.insert(tk.END, f"⏱️  Łączny czas: {total_minutes} minut ({total_minutes/60:.1f} godzin)\n")
            text_widget.insert(tk.END, f"📊 Średnia dzienna: {avg_daily:.1f} minut\n")
            text_widget.insert(tk.END, f"🎯 Dni z osiągniętym celem: {goal_achieved_days}/{total_days} ({success_rate:.1f}%)\n")
            
            # Najlepszy dzień
            best_date = max(data.keys(), key=lambda d: sum(e[1] for e in data[d]))
            best_day_name = self.get_polish_day_name(best_date)
            text_widget.insert(tk.END, f"📈 Najlepszy dzień: {best_day_name}, {best_date.strftime('%d.%m.%Y')} ")
            text_widget.insert(tk.END, f"({max(sum(e[1] for e in entries) for entries in data.values())} min)\n")

    # Dodatkowa metoda dla debugowania kodowania
    def debug_encoding(self) -> None:
        """Debug encoding issues."""
        import sys
        import locale
        
        self.logger.info(f"System encoding: {sys.getdefaultencoding()}")
        self.logger.info(f"File system encoding: {sys.getfilesystemencoding()}")
        self.logger.info(f"Locale: {locale.getlocale()}")
        self.logger.info(f"Preferred encoding: {locale.getpreferredencoding()}")

    # Alternatywne rozwiązanie - bezpośrednie mapowanie
    POLISH_DAYS_MAPPING = {
        'Monday': 'poniedziałek',
        'Tuesday': 'wtorek',
        'Wednesday': 'środa', 
        'Thursday': 'czwartek',
        'Friday': 'piątek',
        'Saturday': 'sobota',
        'Sunday': 'niedziela'
    }

    def get_polish_day_safe(self, date_obj: datetime.date) -> str:
        """Safe method to get Polish day name."""
        try:
            # Najpierw spróbuj z locale
            english_day = date_obj.strftime('%A')
            if english_day in self.POLISH_DAYS_MAPPING:  # DODANE self.
                return self.POLISH_DAYS_MAPPING[english_day]
            
            # Fallback na indeks dnia
            polish_days = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']
            return polish_days[date_obj.weekday()]
        except:
            return f"dzień-{date_obj.weekday() + 1}"

    def load_history_data(self, start_date: datetime.date, end_date: datetime.date) -> Dict:
        """Load history data for specified date range."""
        log_path = self.get_app_path() / "wynik.txt"
        
        if not log_path.exists():
            return {}

        data = {}
        
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split("\t")
                    if len(parts) < 2:
                        self.logger.warning(f"Invalid format in line {line_num}: {line}")
                        continue
                    
                    try:
                        timestamp = parts[0]
                        minutes = int(parts[1])
                        task_desc = parts[2] if len(parts) > 2 else "Bez opisu"
                        date_obj = datetime.strptime(timestamp.split(" ")[0], "%Y-%m-%d").date()
                        
                        if start_date <= date_obj <= end_date:
                            if date_obj not in data:
                                data[date_obj] = []
                            data[date_obj].append((timestamp, minutes, task_desc))
                            
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Error parsing line {line_num}: {e}")
                        continue
                        
        except IOError as e:
            self.logger.error(f"Error reading history: {e}")
            
        return data

    def export_history(self) -> None:
        """Export history to CSV format."""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Eksportuj historię"
            )
            
            if not filename:
                return
            
            # Get date range
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d").date()
            
            data = self.load_history_data(start_date, end_date)
            
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                f.write("Data,Czas,Minuty,Zadanie\n")
                   
                for date_obj in sorted(data.keys()):
                    for entry in data[date_obj]:
                        timestamp = entry[0]
                        minutes = entry[1]
                        task_desc = entry[2] if len(entry) > 2 else "Bez opisu"
                        
                        date_part = timestamp.split(' ')[0]
                        time_part = timestamp.split(' ')[1] if ' ' in timestamp else ''
                        
                        task_desc_escaped = task_desc.replace('"', '""')
                        f.write(f'{date_part},{time_part},{minutes},"{task_desc_escaped}"\n')
            
            messagebox.showinfo("Sukces", f"Historia została wyeksportowana do:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Błąd", f"Błąd eksportu: {e}")

    def on_closing(self) -> None:
        """Handle application closing with confirmation for running timer."""
        if self.is_running:
            if not messagebox.askyesno("Potwierdzenie", 
                                      "Stoper jest uruchomiony. Czy na pewno chcesz zakończyć aplikację?"):
                return
        
        # Save current state if needed
        if self.counter > 0:
            if messagebox.askyesno("Zapisać", 
                                  f"Masz {self.counter//6000} minut na stoperze. Czy chcesz zapisać przed wyjściem?"):
                self.add_to_log()
        
        # Clean up
        if hasattr(self, 'status_popup') and self.status_popup.winfo_exists():
            self.status_popup.destroy()
        
        if hasattr(self, 'reminder_window') and self.reminder_window and self.reminder_window.winfo_exists():
            self.reminder_window.destroy()
        
        self.logger.info("Application closing")
        self.root.destroy()


def main():
    """Main application entry point."""
    try:
        root = tk.Tk()
        
        # Set application icon if available
        try:
            # Uncomment if you have an icon file
            # root.iconbitmap('icon.ico')
            pass
        except:
            pass
        
        app = StopwatchApp(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
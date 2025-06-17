Stoper App or Stoper Pro is an advanced desktop stopwatch application designed to help users track their work time, set daily goals, and stay focused with customizable reminders. Built with Python's Tkinter, this application offers a clean user interface, detailed logging, and comprehensive statistics to help you manage your productivity effectively. 

Features

    Accurate Stopwatch: Start, pause, and reset your timer with precision. 

Time Adjustment: Easily add or subtract minutes from the current counter.
Daily Goal Tracking: Set a daily time goal and monitor your progress with a visual progress bar and percentage display.
Persistent Logging: Automatically saves your sessions to a daily log file (wynik.txt), allowing you to review your historical work data.
Configurable Reminders: Get discrete notifications when the stopwatch is inactive for a set period, encouraging you to resume work.
Modern UI with Status Indicator: A clean, intuitive interface with a compact, always-on-top status indicator showing elapsed minutes.
Comprehensive Keyboard Shortcuts: Control the application efficiently using a variety of shortcuts for common actions.
Dynamic Configuration: Customize daily goals, reminder intervals, reminder duration, auto-save, sound, window behavior, and themes via an in-app configuration dialog.
History and Statistics: View a detailed history of your recorded sessions and track your overall progress (future enhancements planned for weekly, monthly, and trend statistics).
Locale Support: Configured to support Polish locale with fallbacks for day names.
Error Handling and Logging: Robust error handling for configuration and log file operations, with detailed logging to app.log.

Technologies Used

    Python 3
    Tkinter: For the graphical user interface. 

datetime: For time and date operations.
json: For managing configuration data.
os, pathlib: For file system operations.
locale: For locale-specific settings (e.g., Polish day names).
threading: (Potentially for future background tasks, though not explicitly used for UI updates which are handled by after).
logging: For application logging.

Installation

To get started with Stoper Pro, follow these steps:

    Clone the repository:
    Bash

    git clone https://github.com/yourusername/stoper-app.git
    cd stoper-pro

    Install dependencies:
    (Currently, only standard Python libraries are used, so no pip install is strictly necessary beyond a Python installation.)

Usage

To run the application, execute the stoper_app.py file:
Bash

python stoper_app.py

Basic Controls:

    Start: Begins the stopwatch. 

Pause: Stops the stopwatch.
Reset: Clears the current session.
Save: Adds the current stopwatch time to your daily log.
Time Adjustment Buttons: Use +5 min, +1 min, -1 min, -5 min to quickly modify the timer.

Configuration

The application loads its settings from config.json. If the file doesn't exist or is invalid, default settings will be used and a new config.json will be created. 

You can configure the following options via the "Konfiguracja" (Configuration) menu: 

    Daily Goal (minutes): Set your target work time per day. 

Reminder Interval (seconds): How often the reminder notification appears when the stopwatch is paused.
Reminder Display Time (ms): How long the reminder notification stays on screen.
Auto Reset after Save: Automatically resets the timer after saving a session to the log.
Sound Enabled: Enable or disable reminder sounds.
Window Always on Top: Keep the main application window always visible.
Theme: Choose between 'default', 'dark', or 'light' themes.

Data Storage

Session data is saved to wynik.txt in the application's directory. Each entry includes a timestamp and the recorded minutes.  The application also creates a backup of wynik.txt if it exceeds a certain size before writing new data. 

Keyboard Shortcuts

For efficient use, Stoper Pro supports the following keyboard shortcuts: 

Shortcut	Action
Ctrl+S	Start stopwatch
Ctrl+P	Pause stopwatch
Ctrl+R	Reset stopwatch
Ctrl+Enter	Save to log
Ctrl+H	Show History
Ctrl+,	Show Configuration
Ctrl+T	Show Statistics
F1	Show Shortcuts Help
Space	Toggle Start/Pause
Escape	Reset
Future Enhancements

The current version (v2.0) has placeholders for upcoming features: 

    Weekly Statistics 

Monthly Statistics
Trend Analysis
Data Export functionality (e.g., to CSV, Excel)
Data Import functionality

License

This project is open-source and available under the MIT License.

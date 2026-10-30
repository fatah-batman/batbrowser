import os
import sys
from pathlib import Path
from urllib.parse import quote
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar,
                             QLineEdit, QTabWidget)
from PyQt6.QtWebEngineWidgets import QWebEngineView

HOME_FILE = Path(__file__).parent / "homepage.html"
HOME_URL = QUrl.fromLocalFile(str(HOME_FILE.resolve()))
SEARCH_URL = "https://duckduckgo.com/?q="

STYLE = """
* { font-family: "Avenir Next", "Helvetica Neue", sans-serif; }
QMainWindow, QWidget { background: #0e0e0e; color: #e9e6df; }

QToolBar {
    background: #0e0e0e; border: none; border-bottom: 1px solid #1f1e1b;
    padding: 8px 10px; spacing: 4px;
}
QToolButton {
    background: transparent; color: #7d7a74; border: none;
    border-radius: 6px; padding: 5px 11px; font-size: 16px;
}
QToolButton:hover { background: #1a1917; color: #e9e6df; }
QToolButton:pressed { background: #232220; }

QLineEdit {
    background: #161614; color: #e9e6df; border: 1px solid #161614;
    border-radius: 14px; padding: 7px 16px; font-size: 13px; margin-left: 6px;
    selection-background-color: #b9a27a; selection-color: #0e0e0e;
}
QLineEdit:focus { border: 1px solid #3a3730; background: #181816; }

QTabWidget::pane { border: none; }
QTabBar { background: #0e0e0e; }
QTabBar::tab {
    background: transparent; color: #6a6761; padding: 9px 18px;
    border: none; border-bottom: 1px solid transparent; min-width: 100px;
    font-size: 12px; letter-spacing: 1px;
}
QTabBar::tab:selected { color: #e9e6df; border-bottom: 1px solid #b9a27a; }
QTabBar::tab:hover:!selected { color: #a8a59e; }

QToolTip { background: #161614; color: #e9e6df; border: 1px solid #2a2924; padding: 4px 8px; }

QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #2a2924; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3a3730; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""


def to_url(text: str) -> QUrl:
    """Turn address-bar input into a URL or a search query."""
    text = text.strip()
    if "://" in text:
        return QUrl(text)
    if " " not in text and "." in text:
        return QUrl("https://" + text)
    return QUrl(SEARCH_URL + quote(text))


class BrowserView(QWebEngineView):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def createWindow(self, window_type):
        # Handles target="_blank" and window.open() by opening a new tab
        return self.main_window.add_tab()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BatBrowser")

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_url_bar)
        self.setCentralWidget(self.tabs)

        self.build_toolbar()
        self.add_tab(HOME_URL)
        self.showMaximized()

    # ---------- UI ----------
    def build_toolbar(self):
        navbar = QToolBar()
        navbar.setMovable(False)
        self.addToolBar(navbar)

        def action(text, tip, slot, shortcut=None):
            act = QAction(text, self)
            act.setToolTip(tip)
            act.triggered.connect(slot)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            navbar.addAction(act)
            return act

        action("\u2190", "Back", lambda: self.current().back())
        action("\u2192", "Forward", lambda: self.current().forward())
        action("\u21BB", "Reload (Ctrl+R)", lambda: self.current().reload(), "Ctrl+R")
        action("\u2302", "Home", lambda: self.current().setUrl(HOME_URL))
        action("+", "New tab (Ctrl+T)", lambda: self.add_tab(HOME_URL), "Ctrl+T")

        close = QAction(self)
        close.setShortcut(QKeySequence("Ctrl+W"))
        close.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close)

        focus = QAction(self)
        focus.setShortcut(QKeySequence("Ctrl+L"))
        focus.triggered.connect(lambda: (self.url_bar.setFocus(), self.url_bar.selectAll()))
        self.addAction(focus)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter address")
        self.url_bar.returnPressed.connect(
            lambda: self.current().setUrl(to_url(self.url_bar.text())))
        navbar.addWidget(self.url_bar)

    # ---------- Tabs ----------
    def current(self) -> QWebEngineView:
        return self.tabs.currentWidget()

    def add_tab(self, url=None):
        view = BrowserView(self)
        index = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(index)

        view.loadFinished.connect(
            lambda ok, v=view: print("[BatBrowser] loaded:", v.url().toString(), "ok =", ok))
        view.titleChanged.connect(
            lambda title, v=view: self.tabs.setTabText(
                self.tabs.indexOf(v), title[:20] or "New Tab"))
        view.urlChanged.connect(
            lambda qurl, v=view: self.on_url_changed(qurl, v))
        if url is not None:
            view.setUrl(QUrl(url))
        return view

    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()
        else:
            self.close()

    # ---------- URL bar sync ----------
    @staticmethod
    def display_text(qurl: QUrl) -> str:
        # Hide the ugly file:// path for the homepage
        if qurl.isLocalFile() and Path(qurl.toLocalFile()) == HOME_FILE.resolve():
            return ""
        return qurl.toString()

    def on_url_changed(self, qurl, view):
        if view is self.current():
            self.url_bar.setText(self.display_text(qurl))
            self.url_bar.setCursorPosition(0)

    def sync_url_bar(self, index):
        view = self.tabs.widget(index)
        if view:
            self.url_bar.setText(self.display_text(view.url()))


print("[BatBrowser] homepage:", HOME_FILE.resolve(), "exists =", HOME_FILE.exists())
app = QApplication(sys.argv)
QApplication.setApplicationName("BatBrowser")
app.setStyleSheet(STYLE)
window = Window()
sys.exit(app.exec())
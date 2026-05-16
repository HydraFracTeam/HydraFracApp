import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from session import SessionWidget
from config import settings

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HydraFracApp")

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Toolbar
        toolbar = QHBoxLayout()

        self.new_tab_btn = QPushButton("+")

        toolbar.addWidget(self.new_tab_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)

        layout.addWidget(self.tabs)

        self._session_counter = 0

        # signals
        self.new_tab_btn.clicked.connect(self.add_session_tab)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        # first tab
        self.add_session_tab()

    def add_session_tab(self):

        if self.tabs.count() >= settings.MAX_SESSIONS:
            return

        self._session_counter += 1
        session = SessionWidget()

        index = self.tabs.addTab(
            session,
            f"Сессия {self._session_counter}"
        )

        self.tabs.setCurrentIndex(index)

    def close_tab(self, index):

        if self.tabs.count() == 1:
            return

        widget = self.tabs.widget(index)

        self.tabs.removeTab(index)

        widget.deleteLater()


# Entry point
if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())

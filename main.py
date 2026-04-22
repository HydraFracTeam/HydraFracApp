import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout
)

from session import SessionWidget


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HydraFracApp")

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()

        self.new_tab_btn = QPushButton("+")
        self.split_btn = QPushButton("Split")

        toolbar.addWidget(self.new_tab_btn)
        toolbar.addWidget(self.split_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)

        layout.addWidget(self.tabs)

        self.new_tab_btn.clicked.connect(
            self.add_session_tab
        )

        self.split_btn.clicked.connect(
            self.split_current_tab
        )

        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )

        self.add_session_tab()


    def add_session_tab(self):

        session = SessionWidget()

        i = self.tabs.addTab(
            session,
            f"Сессия {self.tabs.count()+1}"
        )

        self.tabs.setCurrentIndex(i)

    def split_current_tab(self):
        from PySide6.QtWidgets import QSplitter
        from PySide6.QtCore import Qt

        index = self.tabs.currentIndex()

        current = self.tabs.widget(index)

        if isinstance(current, QSplitter):
            return

        # удалить старую вкладку
        self.tabs.removeTab(index)
        current.deleteLater()

        # создать splitter
        splitter = QSplitter(Qt.Horizontal)

        left_session = SessionWidget()
        right_session = SessionWidget()

        # вторую можно облегчить
        right_session.ui.left_panel.hide()

        splitter.addWidget(left_session)
        splitter.addWidget(right_session)

        splitter.setStretchFactor(0,1)
        splitter.setStretchFactor(1,1)

        self.tabs.insertTab(index, splitter, "Compare")
        self.tabs.setCurrentIndex(index)

    def close_tab(self,index):

        if self.tabs.count()==1:
            return

        w=self.tabs.widget(index)

        self.tabs.removeTab(index)

        w.deleteLater()


if __name__=="__main__":

    app=QApplication(sys.argv)

    window=MainWindow()
    window.showMaximized()

    sys.exit(app.exec())

import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,    
)
from PySide6.QtCore import Qt
from ui.solution_view import SolutionView
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

        toolbar.addWidget(self.new_tab_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)

        layout.addWidget(self.tabs)

        self.new_tab_btn.clicked.connect(
            self.add_session_tab
        )


        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )

        self.add_session_tab()


    def add_session_tab(self):

        session=SessionWidget()

        session.solutions_ready.connect(
            self.open_compare_tab
        )

        i=self.tabs.addTab(
            session,
            f"Сессия {self.tabs.count()+1}"
        )

        self.tabs.setCurrentIndex(i)

    import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,    
)
from PySide6.QtCore import Qt
from ui.solution_view import SolutionView
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

        toolbar.addWidget(self.new_tab_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)

        layout.addWidget(self.tabs)

        self.new_tab_btn.clicked.connect(
            self.add_session_tab
        )


        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )

        self.add_session_tab()


    def add_session_tab(self):

        session=SessionWidget()

        session.solutions_ready.connect(
            self.open_compare_tab
        )

        i=self.tabs.addTab(
            session,
            f"Сессия {self.tabs.count()+1}"
        )

        self.tabs.setCurrentIndex(i)

    def open_compare_tab(self, solutions):

        idx = self.tabs.currentIndex()

        session = self.tabs.widget(idx)

        compare_page = QWidget()
        root_layout = QHBoxLayout(compare_page)
        root_layout.setContentsMargins(0,0,0,0)

        splitter = QSplitter(Qt.Horizontal)


        # ---- ЛЕВАЯ ПАНЕЛЬ УПРАВЛЕНИЯ ----

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0,0,0,0)

        session.ui.left_panel.setParent(None)
        left_layout.addWidget(
            session.ui.left_panel
        )

        splitter.addWidget(left_container)


        # ---- ПРАВАЯ СТОРОНА С 5 РЕШЕНИЯМИ ----

        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0,0,0,0)

        for sol in solutions:

            view = SolutionView(
                sol,
                session.app_state
            )

            right_layout.addWidget(view)

        splitter.addWidget(right_container)


        splitter.setSizes(
            [450, 1400]
        )

        root_layout.addWidget(splitter)

        self.tabs.removeTab(idx)

        self.tabs.insertTab(
            idx,
            compare_page,
            f"Сессия {idx+1}"
        )

        self.tabs.setCurrentIndex(idx)

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

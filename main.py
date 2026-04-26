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

        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0,0,0,0)

        splitter = QSplitter(Qt.Horizontal)

        session = SessionWidget()

        session.solutions_ready.connect(
            lambda sols, s=splitter:
            self.populate_compare_panel(
                s,
                session,
                sols
            )
        )

        splitter.addWidget(session)

        # пустая правая часть
        placeholder = QWidget()
        placeholder.setMaximumWidth(10)

        splitter.addWidget(
            placeholder
        )
# 

        root.addWidget(splitter)

        i=self.tabs.addTab(
            page,
            f"Сессия {self.tabs.count()+1}"
        )

        self.tabs.setCurrentIndex(i)
    
    def populate_compare_panel(
        self,
        splitter,
        session,
        solutions
    ):
        old_right = splitter.widget(1)

        old_right.setParent(None)
        old_right.deleteLater()


        right_vertical = QSplitter(Qt.Vertical)

        top_row = QSplitter(Qt.Horizontal)
        bottom_row = QSplitter(Qt.Horizontal)


        for sol in solutions[:2]:
            top_row.addWidget(
                SolutionView(
                    sol,
                    session.app_state
                )
            )

        for sol in solutions[2:]:
            bottom_row.addWidget(
                SolutionView(
                    sol,
                    session.app_state
                )
            )

        right_vertical.addWidget(top_row)
        right_vertical.addWidget(bottom_row)

        right_vertical.setSizes([500,500])


        splitter.insertWidget(
            1,
            right_vertical
        )

        splitter.setSizes(
            [1100,1500]
        )
        
    def open_compare_tab(self, solutions):

        idx = self.tabs.currentIndex()
        session = self.tabs.widget(idx)

        compare_page = QWidget()
        root_layout = QHBoxLayout(compare_page)
        root_layout.setContentsMargins(0,0,0,0)


        # главный splitter

        main_splitter = QSplitter(Qt.Horizontal)

        # LEFT
        # вместо left_panel
        session.ui.main_panel.setParent(None)

        main_splitter.addWidget(session)
    
        # RIGHT SIDE

        right_vertical = QSplitter(
            Qt.Vertical
        )


        top_row = QSplitter(
            Qt.Horizontal
        )

        bottom_row = QSplitter(
            Qt.Horizontal
        )


        # первые 2 сверху
        for sol in solutions[:2]:

            top_row.addWidget(
                SolutionView(
                    sol,
                    session.app_state
                )
            )


        # остальные снизу
        for sol in solutions[2:]:
            
            bottom_row.addWidget(
                SolutionView(
                    sol,
                    session.app_state
                )
            )


        right_vertical.addWidget(
            top_row
        )

        right_vertical.addWidget(
            bottom_row
        )


        right_vertical.setSizes(
            [500,500]
        )


        main_splitter.addWidget(
            right_vertical
        )


        main_splitter.setSizes(
            [450,1500]
        )

        root_layout.addWidget(
            main_splitter
        )


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

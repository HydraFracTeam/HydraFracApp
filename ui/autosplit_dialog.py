"""
Диалог автосплиттера для выбора режима анализа КСД/КВД.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional, Callable
import numpy as np


class AutosplitDialog(QDialog):
    """
    Диалог выбора режима анализа при обнаружении склейки КСД и КВД.
    """
    
    # Режимы выбора
    MODE_KSD = "ksd"      # Только КСД
    MODE_KVD = "kvd"      # Только КВД
    MODE_BOTH = "both"    # Оба (с предупреждением)
    MODE_IGNORE = "ignore"  # Игнорировать
    
    def __init__(
        self, 
        parent=None,
        split_time: float = 0.0,
        split_pressure: float = 0.0,
        ksd_points: int = 0,
        kvd_points: int = 0,
        ksd_percent: float = 0.0,
        kvd_percent: float = 0.0
    ):
        super().__init__(parent)
        
        self.selected_mode = None
        self.split_time = split_time
        
        self.setWindowTitle("Обнаружена склейка КСД и КВД")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        self._setup_ui(
            split_time,
            split_pressure,
            ksd_points,
            kvd_points,
            ksd_percent,
            kvd_percent
        )
    
    def _setup_ui(
        self,
        split_time: float,
        split_pressure: float,
        ksd_points: int,
        kvd_points: int,
        ksd_percent: float,
        kvd_percent: float
    ):
        """Настройка UI диалога."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("⚠ Обнаружена склейка КСД и КВД")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Информация о точке разделения
        info_frame = QGroupBox("Информация о разделении")
        info_layout = QVBoxLayout(info_frame)
        
        info_text = (
            f"<b>Граница разделения:</b><br>"
            f"КСД: t ≤ 50000.00<br>"
            f"КВД: t > 50000.01<br><br>"
            f"<b>Точка перехода:</b><br>"
            f"Время T = {split_time:.2f}<br>"
            f"Давление P = {split_pressure:.2f}<br><br>"
            f"<b>КСД:</b> {ksd_points} точек ({ksd_percent:.1f}%)<br>"
            f"<b>КВД:</b> {kvd_points} точек ({kvd_percent:.1f}%)"
        )
        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.RichText)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_frame)
        
        # Предупреждение
        warning_frame = QFrame()
        warning_frame.setStyleSheet("background-color: #FFF3CD; border: 1px solid #FFEAA7; padding: 10px;")
        warning_layout = QVBoxLayout(warning_frame)
        warning_label = QLabel(
            "<b>⚠ Внимание:</b><br>"
            "Анализ обеих кривых одновременно может привести к некорректному подбору параметров. "
            "Рекомендуется анализировать кривые по отдельности."
        )
        warning_label.setTextFormat(Qt.RichText)
        warning_label.setWordWrap(True)
        warning_layout.addWidget(warning_label)
        layout.addWidget(warning_frame)
        
        # Кнопки выбора
        buttons_label = QLabel("Выберите режим анализа:")
        buttons_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(buttons_label)
        
        buttons_layout = QHBoxLayout()
        
        # Кнопка КСД
        self.ksd_btn = QPushButton("📉 Анализировать КСД")
        self.ksd_btn.setToolTip("Использовать только кривую стабилизации давления (первая часть)")
        self.ksd_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        self.ksd_btn.clicked.connect(lambda: self._select_mode(self.MODE_KSD))
        buttons_layout.addWidget(self.ksd_btn)
        
        # Кнопка КВД
        self.kvd_btn = QPushButton("📈 Анализировать КВД")
        self.kvd_btn.setToolTip("Использовать только кривую восстановления давления (вторая часть)")
        self.kvd_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219A52;
            }
        """)
        self.kvd_btn.clicked.connect(lambda: self._select_mode(self.MODE_KVD))
        buttons_layout.addWidget(self.kvd_btn)
        
        layout.addLayout(buttons_layout)
        
        # Дополнительные кнопки
        extra_layout = QHBoxLayout()
        
        # Кнопка "Показать оба"
        self.both_btn = QPushButton("⚠ Показать оба")
        self.both_btn.setToolTip("Анализировать обе кривые (не рекомендуется)")
        self.both_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        self.both_btn.clicked.connect(lambda: self._select_mode(self.MODE_BOTH))
        extra_layout.addWidget(self.both_btn)
        
        # Кнопка "Игнорировать"
        self.ignore_btn = QPushButton("Игнорировать")
        self.ignore_btn.setToolTip("Использовать все данные без разделения")
        self.ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)
        self.ignore_btn.clicked.connect(lambda: self._select_mode(self.MODE_IGNORE))
        extra_layout.addWidget(self.ignore_btn)
        
        layout.addLayout(extra_layout)
        
        # Описание режимов
        desc_label = QLabel(
            "<small>"
            "<b>КСД</b> - кривая стабилизации давления (давление падает)<br>"
            "<b>КВД</b> - кривая восстановления давления (давление растёт)"
            "</small>"
        )
        desc_label.setTextFormat(Qt.RichText)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
    
    def _select_mode(self, mode: str):
        """Выбор режима и закрытие диалога."""
        self.selected_mode = mode
        self.accept()
    
    def get_selected_mode(self) -> Optional[str]:
        """Получение выбранного режима."""
        return self.selected_mode
    
    @staticmethod
    def show_dialog(
        parent=None,
        split_info: dict = None
    ) -> Optional[str]:
        """
        Статический метод для показа диалога.
        
        Args:
            parent: Родительское окно
            split_info: Словарь с информацией о разделении
            
        Returns:
            Optional[str]: Выбранный режим или None
        """
        if split_info is None:
            return None
        
        dialog = AutosplitDialog(
            parent=parent,
            split_time=split_info.get('time', 0.0),
            split_pressure=split_info.get('pressure', 0.0),
            ksd_points=split_info.get('ksd_points', 0),
            kvd_points=split_info.get('kvd_points', 0),
            ksd_percent=split_info.get('ksd_percent', 0.0),
            kvd_percent=split_info.get('kvd_percent', 0.0)
        )
        
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            return dialog.get_selected_mode()
        return None

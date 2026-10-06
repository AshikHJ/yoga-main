"""
Yoga Pose Library Screen for KI.AI — AI-Powered Yoga & Posture Intelligence.
Allows searching, filtering by difficulty/category/goal, viewing full pose details,
and launching live AI posture practice sessions.
Features pose-specific SVG figures in the top-right corner of each pose card.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import settings
from database.database import Database
from ui.pose_details import PoseDetailsDialog
from vision.reference_helper import ReferenceHelper


class PoseCard(QFrame):
    """
    Premium Yoga Pose Card matching target reference design:
      - Top Image Area: Realistic yoga pose photo with corner pose figure
      - Top-Right Corner of Image: Dedicated white anatomical line-art silhouette figure
      - Content Row 1: Pose Name (Left) + Difficulty Badge (Right)
      - Content Row 2: Sanskrit / English Subtitle (Italic)
      - Content Row 3: Goal with Icon (e.g. 🧘 Balance, 💪 Strength)
      - Content Row 4: Short 2-line Description
      - Content Row 5: Large '▶ Practice Pose' + Bookmark Ribbon Button
    """

    view_details = Signal(dict)
    start_practice = Signal(dict)

    def __init__(self, pose: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.pose = pose
        self.setProperty("class", "card")
        self.setMinimumHeight(355)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(f"""
            QFrame.card {{
                background-color: #0F172A;
                border: 1.5px solid #1E293B;
                border-radius: 12px;
                padding: 0px;
            }}
            QFrame.card:hover {{
                border: 1.5px solid {settings.THEME['primary']};
                background-color: #131E32;
            }}
        """)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ==========================================
        # 1. TOP IMAGE AREA (Realistic Studio Photo)
        # ==========================================
        image_container = QFrame()
        image_container.setFixedHeight(140)
        image_container.setStyleSheet("""
            QFrame {
                background-color: #0B1120;
                border-radius: 8px;
                border: 1px solid #1E293B;
            }
        """)
        img_layout = QVBoxLayout(image_container)
        img_layout.setContentsMargins(6, 6, 6, 6)

        # Background Realistic Image
        self.lbl_bg_img = QLabel(image_container)
        self.lbl_bg_img.setGeometry(0, 0, 260, 140)
        self.lbl_bg_img.setScaledContents(True)
        self.lbl_bg_img.setStyleSheet("border-radius: 8px;")

        # Resolve image path
        img_path = self.pose.get("image_path", "")
        if not img_path or not Path(img_path).exists():
            clean_name = self.pose.get("name", "").lower().replace(" ", "_").replace("-", "_")
            fallback = Path("assets/images/yoga") / f"{clean_name}.png"
            img_path = str(fallback) if fallback.exists() else "assets/images/yoga/tadasana.png"

        pix = QPixmap(img_path)
        if not pix.isNull():
            self.lbl_bg_img.setPixmap(pix)

        # Overlay Row (Top-Right Reference Figure only, as in reference design)
        overlay_row = QHBoxLayout()
        overlay_row.setContentsMargins(0, 0, 0, 0)
        overlay_row.addStretch()

        # TOP-RIGHT: Dedicated Anatomical Reference Figure Badge
        self.figure_badge = QLabel()
        self.figure_badge.setFixedSize(42, 42)
        self.figure_badge.setAlignment(Qt.AlignCenter)
        self.figure_badge.setToolTip(f"Pose Figure Reference: {self.pose.get('name', 'Pose')}")
        self.figure_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1.5px solid #10B981;
                border-radius: 8px;
                padding: 2px;
            }
            QLabel:hover {
                border: 1.5px solid #34D399;
                background-color: rgba(6, 78, 59, 0.95);
            }
        """)

        fig_pix = ReferenceHelper.get_pose_figure_pixmap(self.pose, size=(34, 34))
        self.figure_badge.setPixmap(fig_pix)
        overlay_row.addWidget(self.figure_badge, alignment=Qt.AlignTop | Qt.AlignRight)

        img_layout.addLayout(overlay_row)
        img_layout.addStretch()

        layout.addWidget(image_container)

        # ==========================================
        # 2. CARD CONTENT
        # ==========================================
        # Row 1: Pose Name (Left) + Difficulty Badge (Right)
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 2, 0, 0)

        name_lbl = QLabel(self.pose.get("name", "Pose"))
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        name_row.addWidget(name_lbl)
        name_row.addStretch()

        diff = self.pose.get("difficulty", "Beginner")
        diff_color = '#10B981' if diff == 'Beginner' else ('#38BDF8' if diff == 'Intermediate' else '#A855F7')
        diff_bg = 'rgba(6, 78, 59, 0.5)' if diff == 'Beginner' else ('rgba(14, 116, 144, 0.5)' if diff == 'Intermediate' else 'rgba(88, 28, 135, 0.5)')
        
        diff_badge = QLabel(diff)
        diff_badge.setStyleSheet(f"""
            background-color: {diff_bg};
            color: {diff_color};
            border: 1px solid {diff_color};
            border-radius: 6px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: 700;
        """)
        name_row.addWidget(diff_badge)
        layout.addLayout(name_row)

        # Row 2: Sanskrit / English Subtitle
        sanskrit = self.pose.get("sanskrit_name", "")
        if sanskrit:
            s_lbl = QLabel(sanskrit)
            s_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-style: italic;")
            layout.addWidget(s_lbl)

        # Row 3: Goal with Icon
        goal = self.pose.get("goal", "Balance")
        goal_icon = "🧘" if "Balance" in goal or "Flexibility" in goal else ("💪" if "Strength" in goal else "🌿")
        goal_tag = QLabel(f"{goal_icon}  {goal}")
        goal_tag.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600;")
        layout.addWidget(goal_tag)

        # Row 4: Short Description (2 lines)
        desc = self.pose.get("description", "")
        if len(desc) > 85:
            desc = desc[:82] + "..."
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.25;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # ==========================================
        # 3. ACTION FOOTER (Practice Button + Bookmark)
        # ==========================================
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_start = QPushButton("▶ Practice Pose")
        btn_start.setProperty("class", "btn_primary")
        btn_start.setFixedHeight(34)
        btn_start.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        btn_start.clicked.connect(lambda: self.start_practice.emit(self.pose))
        btn_row.addWidget(btn_start, stretch=5)

        btn_bookmark = QPushButton("🔖")
        btn_bookmark.setFixedSize(34, 34)
        btn_bookmark.setToolTip("Bookmark Pose")
        btn_bookmark.setStyleSheet("""
            QPushButton {
                background-color: #0F172A;
                border: 1px solid #334155;
                color: #94A3B8;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                border: 1px solid #10B981;
                color: #10B981;
                background-color: #1E293B;
            }
        """)
        btn_bookmark.clicked.connect(lambda: btn_bookmark.setText("🏷️" if btn_bookmark.text() == "🔖" else "🔖"))
        btn_row.addWidget(btn_bookmark, stretch=1)

        layout.addLayout(btn_row)

    def mousePressEvent(self, event) -> None:
        """Clicking anywhere on the card opens full pose details dialog."""
        if event.button() == Qt.LeftButton:
            self.view_details.emit(self.pose)


class YogaLibrary(QWidget):
    """Searchable and filterable catalog of all yoga poses with dynamic pose figures."""

    pose_selected_for_practice = Signal(dict)

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.all_poses: List[Dict[str, Any]] = []
        self.view_mode = "grid"
        self._init_ui()
        self.load_poses()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Top Header (Page Title & Subtitle)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_lbl = QLabel("Yoga Library")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFFFFF;")
        title_box.addWidget(title_lbl)

        sub_lbl = QLabel("Browse poses with verified anatomical angle rules.")
        sub_lbl.setStyleSheet(f"color: {settings.THEME['text_secondary']}; font-size: 13px;")
        title_box.addWidget(sub_lbl)
        main_layout.addLayout(title_box)

        # Filter and Search Toolbar
        filter_card = QFrame()
        filter_card.setProperty("class", "card")
        filter_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 10px; padding: 6px;")
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(8, 6, 8, 6)
        f_layout.setSpacing(8)

        # Search Box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Search categories...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self.filter_poses)
        f_layout.addWidget(self.txt_search, stretch=3)

        # Difficulty Filter
        self.combo_difficulty = QComboBox()
        self.combo_difficulty.addItem("All Difficulty")
        self.combo_difficulty.addItems(settings.DIFFICULTY_LEVELS)
        self.combo_difficulty.setFixedHeight(34)
        self.combo_difficulty.currentIndexChanged.connect(self.filter_poses)
        f_layout.addWidget(self.combo_difficulty, stretch=2)

        # Goal Filter
        self.combo_goal = QComboBox()
        self.combo_goal.addItem("All Goals")
        self.combo_goal.addItems(settings.GOALS)
        self.combo_goal.setFixedHeight(34)
        self.combo_goal.currentIndexChanged.connect(self.filter_poses)
        f_layout.addWidget(self.combo_goal, stretch=2)

        # Sort Dropdown
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Sort: A - Z", "Sort: Difficulty", "Sort: Duration"])
        self.combo_sort.setFixedHeight(34)
        self.combo_sort.currentIndexChanged.connect(self.filter_poses)
        f_layout.addWidget(self.combo_sort, stretch=2)

        # Grid / List Toggle Buttons
        self.btn_grid_mode = QPushButton("▦")
        self.btn_grid_mode.setToolTip("Grid View")
        self.btn_grid_mode.setFixedSize(34, 34)
        self.btn_grid_mode.setStyleSheet("""
            QPushButton { background-color: #064E3B; color: #10B981; border: 1.5px solid #10B981; border-radius: 6px; font-size: 16px; font-weight: bold; }
        """)
        self.btn_grid_mode.clicked.connect(lambda: self._set_view_mode("grid"))
        f_layout.addWidget(self.btn_grid_mode)

        self.btn_list_mode = QPushButton("☷")
        self.btn_list_mode.setToolTip("List View")
        self.btn_list_mode.setFixedSize(34, 34)
        self.btn_list_mode.setStyleSheet("""
            QPushButton { background-color: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; font-size: 16px; }
        """)
        self.btn_list_mode.clicked.connect(lambda: self._set_view_mode("list"))
        f_layout.addWidget(self.btn_list_mode)

        main_layout.addWidget(filter_card)

        # Poses Grid Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 4, 0, 4)
        self.grid_layout.setSpacing(14)

        scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(scroll_area)

    def _set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        if mode == "grid":
            self.btn_grid_mode.setStyleSheet("background-color: #064E3B; color: #10B981; border: 1.5px solid #10B981; border-radius: 6px; font-size: 16px; font-weight: bold;")
            self.btn_list_mode.setStyleSheet("background-color: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; font-size: 16px;")
        else:
            self.btn_list_mode.setStyleSheet("background-color: #064E3B; color: #10B981; border: 1.5px solid #10B981; border-radius: 6px; font-size: 16px; font-weight: bold;")
            self.btn_grid_mode.setStyleSheet("background-color: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; font-size: 16px;")
        self.filter_poses()

    def load_poses(self) -> None:
        self.all_poses = self.db.get_all_poses()
        self.filter_poses()

    def filter_poses(self) -> None:
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search_text = self.txt_search.text().strip().lower()
        selected_diff = self.combo_difficulty.currentText()
        selected_goal = self.combo_goal.currentText()
        sort_mode = self.combo_sort.currentText()

        filtered = []
        for p in self.all_poses:
            if p.get("category") == "Surya Namaskar" and not search_text:
                continue

            if search_text:
                name_match = search_text in p.get("name", "").lower()
                sanskrit_match = search_text in p.get("sanskrit_name", "").lower()
                desc_match = search_text in p.get("description", "").lower()
                cat_match = search_text in p.get("category", "").lower()
                if not (name_match or sanskrit_match or desc_match or cat_match):
                    continue

            if selected_diff != "All Difficulty" and p.get("difficulty") != selected_diff:
                continue
            if selected_goal != "All Goals" and p.get("goal") != selected_goal:
                continue

            filtered.append(p)

        # Sorting
        if "A - Z" in sort_mode:
            filtered.sort(key=lambda x: x.get("name", "").lower())
        elif "Difficulty" in sort_mode:
            diff_order = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
            filtered.sort(key=lambda x: diff_order.get(x.get("difficulty", "Beginner"), 1))
        elif "Duration" in sort_mode:
            filtered.sort(key=lambda x: x.get("hold_duration", 20), reverse=True)

        columns = 1 if self.view_mode == "list" else 4
        for idx, pose in enumerate(filtered):
            card = PoseCard(pose)
            card.view_details.connect(self._on_view_details)
            card.start_practice.connect(self._on_start_practice)
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)

        if not filtered:
            lbl_empty = QLabel("No yoga poses match the selected filters.")
            lbl_empty.setStyleSheet("color: #64748B; font-size: 14px; padding: 40px;")
            lbl_empty.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(lbl_empty, 0, 0, 1, columns)

    def _on_view_details(self, pose: Dict[str, Any]) -> None:
        dialog = PoseDetailsDialog(pose, parent=self)
        dialog.start_practice_clicked.connect(self._on_start_practice)
        dialog.exec()

    def _on_start_practice(self, pose: Dict[str, Any]) -> None:
        self.pose_selected_for_practice.emit(pose)

import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QStackedWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from PySide6.QtCore import QDate

import admin_app


def populate_table(table: QTableWidget, columns, rows):
    """Fill a QTableWidget with the given column headers and row tuples."""
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([str(c) for c in columns])
    table.setRowCount(0)
    for row_data in rows:
        row_idx = table.rowCount()
        table.insertRow(row_idx)
        for col_idx, value in enumerate(row_data):
            table.setItem(row_idx, col_idx, QTableWidgetItem("" if value is None else str(value)))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

# ===================================================== #
#                    Query & Search Tab                 #
# ===================================================== #

class QuerySearchTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Search Players", "Search Games"])
        left_layout.addWidget(self.mode_combo)

        self.stack = QStackedWidget()

        # --- Players search page ---
        players_page = QWidget()
        players_form = QFormLayout(players_page)
        self.username_substr_edit = QLineEdit()
        self.is_banned_combo = QComboBox()
        self.is_banned_combo.addItems(["Any", "Banned", "Not Banned"])
        players_form.addRow("Username contains:", self.username_substr_edit)
        players_form.addRow("Banned status:", self.is_banned_combo)
        self.stack.addWidget(players_page)

        # --- Games search page ---
        games_page = QWidget()
        games_form = QFormLayout(games_page)

        self.date_from_check = QCheckBox("From:")
        self.date_from_edit = QDateEdit(QDate.currentDate().addYears(-1))
        self.date_from_edit.setCalendarPopup(True)
        date_from_row = QHBoxLayout()
        date_from_row.addWidget(self.date_from_check)
        date_from_row.addWidget(self.date_from_edit)
        games_form.addRow(date_from_row)

        self.date_to_check = QCheckBox("To:")
        self.date_to_edit = QDateEdit(QDate.currentDate())
        self.date_to_edit.setCalendarPopup(True)
        date_to_row = QHBoxLayout()
        date_to_row.addWidget(self.date_to_check)
        date_to_row.addWidget(self.date_to_edit)
        games_form.addRow(date_to_row)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Any", "pending", "active", "completed", "cancelled"])
        games_form.addRow("Status:", self.status_combo)

        self.winning_side_combo = QComboBox()
        self.winning_side_combo.addItems(["Any", "hunters", "hiders"])
        games_form.addRow("Winning Side:", self.winning_side_combo)

        self.min_players_spin = QSpinBox()
        self.min_players_spin.setRange(0, 999)
        self.min_players_spin.setSpecialValueText("Any")
        games_form.addRow("Min Players:", self.min_players_spin)

        self.max_players_spin = QSpinBox()
        self.max_players_spin.setRange(0, 999)
        self.max_players_spin.setSpecialValueText("Any")
        games_form.addRow("Max Players:", self.max_players_spin)

        self.stack.addWidget(games_page)

        left_layout.addWidget(self.stack)

        self.search_btn = QPushButton("Search")
        left_layout.addWidget(self.search_btn)
        left_layout.addStretch()

        self.results_table = QTableWidget(0, 0)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Results"))
        right_layout.addWidget(self.results_table)

        layout.addWidget(left_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.mode_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.search_btn.clicked.connect(self.on_search)

    def on_search(self):
        try:
            if self.mode_combo.currentIndex() == 0:
                username_substr = self.username_substr_edit.text().strip() or None
                is_banned = {0: None, 1: True, 2: False}[self.is_banned_combo.currentIndex()]
                columns, rows = admin_app.search_players(username_substr, is_banned)
            else:
                date_from = self.date_from_edit.date().toPython() if self.date_from_check.isChecked() else None
                date_to = self.date_to_edit.date().toPython() if self.date_to_check.isChecked() else None
                status = self.status_combo.currentText() if self.status_combo.currentIndex() != 0 else None
                winning_side = (
                    self.winning_side_combo.currentText()
                    if self.winning_side_combo.currentIndex() != 0
                    else None
                )
                min_players = self.min_players_spin.value() or None
                max_players = self.max_players_spin.value() or None
                columns, rows = admin_app.search_games(
                    date_from, date_to, status, winning_side, min_players, max_players
                )
            populate_table(self.results_table, columns, rows)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))


# ===================================================== #
#                      Manage Players Tab               #
# ===================================================== #

class ManagePlayersTab(QWidget):
    def __init__(self):
        super().__init__()
        self._selected_player_id = None
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        create_group = QGroupBox("Create Player")
        create_form = QFormLayout(create_group)
        self.new_username_edit = QLineEdit()
        self.new_email_edit = QLineEdit()
        self.new_display_name_edit = QLineEdit()
        self.new_avatar_url_edit = QLineEdit()
        self.create_btn = QPushButton("Create")
        create_form.addRow("Username:", self.new_username_edit)
        create_form.addRow("Email:", self.new_email_edit)
        create_form.addRow("Display Name:", self.new_display_name_edit)
        create_form.addRow("Avatar URL:", self.new_avatar_url_edit)
        create_form.addRow(self.create_btn)
        left_layout.addWidget(create_group)

        self.remove_btn = QPushButton("Remove Selected Player")
        left_layout.addWidget(self.remove_btn)

        self.ban_btn = QPushButton("Ban Selected")
        self.unban_btn = QPushButton("Unban Selected")
        self.refresh_btn = QPushButton("Refresh")
        left_layout.addWidget(self.ban_btn)
        left_layout.addWidget(self.unban_btn)
        left_layout.addWidget(self.refresh_btn)
        left_layout.addStretch()

        self.players_table = QTableWidget(0, 0)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Players"))
        right_layout.addWidget(self.players_table)

        layout.addWidget(left_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.create_btn.clicked.connect(self.on_create)
        self.remove_btn.clicked.connect(self.on_remove)
        self.ban_btn.clicked.connect(self.on_ban)
        self.unban_btn.clicked.connect(self.on_unban)
        self.refresh_btn.clicked.connect(self.refresh)
        self.players_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        selected = self.players_table.selectedItems()
        if not selected:
            self._selected_player_id = None
            return
        row = selected[0].row()
        self._selected_player_id = int(self.players_table.item(row, 0).text())

    def on_create(self):
        username = self.new_username_edit.text().strip()
        email = self.new_email_edit.text().strip()
        display_name = self.new_display_name_edit.text().strip()
        avatar_url = self.new_avatar_url_edit.text().strip()
        if not username or not email:
            QMessageBox.warning(self, "Missing Info", "Username and Email are required.")
            return
        try:
            admin_app.create_player(username, email, display_name or None, avatar_url or None)
            self.new_username_edit.clear()
            self.new_email_edit.clear()
            self.new_display_name_edit.clear()
            self.new_avatar_url_edit.clear()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def on_remove(self):
        if self._selected_player_id is None:
            QMessageBox.information(self, "No Selection", "Select a player first.")
            return
        confirm = QMessageBox.question(
            self, "Confirm Remove", "Are you sure you want to permanently remove this player?"
        )
        if confirm == QMessageBox.Yes:
            try:
                admin_app.delete_player(self._selected_player_id)
                self._selected_player_id = None
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", str(e))

    def on_ban(self):
        if self._selected_player_id is None:
            QMessageBox.information(self, "No Selection", "Select a player first.")
            return
        confirm = QMessageBox.question(self, "Confirm Ban", "Ban this player?")
        if confirm == QMessageBox.Yes:
            try:
                admin_app.ban_player(self._selected_player_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", str(e))

    def on_unban(self):
        if self._selected_player_id is None:
            QMessageBox.information(self, "No Selection", "Select a player first.")
            return
        try:
            admin_app.unban_player(self._selected_player_id)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def refresh(self):
        columns, rows = admin_app.list_all_players()
        populate_table(self.players_table, columns, rows)


# ===================================================== #
#                Leaderboard / Reports Tab              #
# ===================================================== #

class LeaderboardTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.report_combo = QComboBox()
        for key, (label, _) in admin_app.REPORTS.items():
            self.report_combo.addItem(label, userData=key)
        self.run_btn = QPushButton("Run Report")
        left_layout.addWidget(self.report_combo)
        left_layout.addWidget(self.run_btn)
        left_layout.addStretch()

        self.report_table = QTableWidget(0, 0)
        self.report_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.report_table.setEditTriggers(QTableWidget.NoEditTriggers)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Report Results"))
        right_layout.addWidget(self.report_table)

        layout.addWidget(left_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.run_btn.clicked.connect(self.on_run)

    def on_run(self):
        key = self.report_combo.currentData()
        if key is None:
            return
        try:
            columns, rows = admin_app.run_report(key)
            populate_table(self.report_table, columns, rows)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

# ===================================================== #
#                      Main Window                      #
# ===================================================== #

class AdminMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manhunt: Admin")
        self.resize(1000, 600)

        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)

        tabs.addTab(QuerySearchTab(), "Query && Search")
        tabs.addTab(ManagePlayersTab(), "Manage Players")
        tabs.addTab(LeaderboardTab(), "Leaderboard")


def main():
    app = QApplication(sys.argv)
    window = AdminMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

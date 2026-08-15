import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QDialog,
    QTabWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialogButtonBox,
)

import db
import player_app
import styles

def populate_table(table: QTableWidget, columns, rows):
    """ Fill QTableWidget with given column headers and row tuples."""
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
#                      Login / Registration             #
# ===================================================== #

class RegisterDialog(QDialog):
    def __init__(self, parent=None, prefill_username=""):
        super().__init__(parent)
        self.setWindowTitle("Register")
        self.new_player_row = None

        self.username_edit = QLineEdit(prefill_username)
        self.email_edit = QLineEdit()
        self.display_name_edit = QLineEdit()
        self.avatar_url_edit = QLineEdit()

        form = QFormLayout()
        form.addRow("Username:", self.username_edit)
        form.addRow("Email:", self.email_edit)
        form.addRow("Display Name:", self.display_name_edit)
        form.addRow("Avatar URL:", self.avatar_url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self):
        username = self.username_edit.text().strip()
        email = self.email_edit.text().strip()
        if not username or not email:
            QMessageBox.warning(self, "Missing Info", "Username and Email are required.")
            return
        try:
            new_id = player_app.create_account(
                username,
                email,
                self.display_name_edit.text().strip() or None,
                self.avatar_url_edit.text().strip() or None,
            )
            self.new_player_row = player_app.get_account(new_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Registration Failed", str(e))


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manhunt: Log In")
        self.player_row = None

        self.username_edit = QLineEdit()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")

        form = QFormLayout()
        form.addRow("Username:", self.username_edit)

        self.login_btn = QPushButton("Log In")
        self.register_btn = QPushButton("Register...")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addLayout(btn_layout)

        self.login_btn.clicked.connect(self._on_login_clicked)
        self.register_btn.clicked.connect(self._on_register_clicked)

    def _on_login_clicked(self):
        username = self.username_edit.text().strip()
        if not username:
            self.status_label.setText("Enter a username first.")
            return
        try:
            row = player_app.login(username)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
            return

        if row is None:
            answer = QMessageBox.question(
                self, "No Such User", f"No player named '{username}'. Register a new account?"
            )
            if answer == QMessageBox.Yes:
                self._open_register_dialog(prefill_username=username)
            return

        if row[6]:  # is_banned
            QMessageBox.warning(self, "Account Banned", "This account has been banned.")
            return

        self.player_row = row
        self.accept()

    def _on_register_clicked(self):
        self._open_register_dialog()

    def _open_register_dialog(self, prefill_username=""):
        dialog = RegisterDialog(self, prefill_username=prefill_username)
        if dialog.exec() == QDialog.Accepted and dialog.new_player_row is not None:
            self.player_row = dialog.new_player_row
            self.accept()

    def get_player_row(self):
        return self.player_row

# ===================================================== #
#                      Account Tab                      #
# ===================================================== #

class AccountTab(QWidget):
    def __init__(self, player_id):
        super().__init__()
        self.player_id = player_id
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        self.username_label = QLineEdit()
        self.username_label.setReadOnly(True)
        self.email_label = QLineEdit()
        self.email_label.setReadOnly(True)
        self.display_name_edit = QLineEdit()
        self.avatar_url_edit = QLineEdit()

        form_layout.addRow("Username:", self.username_label)
        form_layout.addRow("Email:", self.email_label)
        form_layout.addRow("Display Name:", self.display_name_edit)
        form_layout.addRow("Avatar URL:", self.avatar_url_edit)

        btn_layout = QHBoxLayout()
        self.update_btn = QPushButton("Update")
        self.refresh_btn = QPushButton("Refresh")
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.refresh_btn)
        form_layout.addRow(btn_layout)

        self.players_table = QTableWidget(0, 0)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("All Players"))
        right_layout.addWidget(self.players_table)

        layout.addWidget(form_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.update_btn.clicked.connect(self.on_update)
        self.refresh_btn.clicked.connect(self.refresh)

    def load_account(self):
        row = player_app.get_account(self.player_id)
        if row is None:
            return
        self.username_label.setText(row[1])
        self.email_label.setText(row[2])
        self.display_name_edit.setText(row[3] or "")
        self.avatar_url_edit.setText(row[4] or "")

    def refresh(self):
        self.load_account()
        columns, rows = player_app.list_all_players_brief()
        populate_table(self.players_table, columns, rows)
        for row_idx in range(self.players_table.rowCount()):
            if self.players_table.item(row_idx, 0).text() == str(self.player_id):
                self.players_table.selectRow(row_idx)
                break

    def on_update(self):
        try:
            player_app.update_account(
                self.player_id,
                self.display_name_edit.text().strip() or None,
                self.avatar_url_edit.text().strip() or None,
            )
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

# ===================================================== #
#                      Friends Tab                      #
# ===================================================== #

class FriendsTab(QWidget):
    def __init__(self, player_id):
        super().__init__()
        self.player_id = player_id
        self._selected_friend_id = None
        self._selected_pending_pair = None
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        send_group = QGroupBox("Send Friend Request")
        send_form = QFormLayout(send_group)
        self.target_username_edit = QLineEdit()
        self.send_btn = QPushButton("Send Request")
        send_form.addRow("Username:", self.target_username_edit)
        send_form.addRow(self.send_btn)
        left_layout.addWidget(send_group)

        action_group = QGroupBox("Manage Selection")
        action_layout = QVBoxLayout(action_group)
        self.accept_btn = QPushButton("Accept Selected Request")
        self.reject_btn = QPushButton("Reject Selected Request")
        self.remove_btn = QPushButton("Remove Selected Friend")
        action_layout.addWidget(self.accept_btn)
        action_layout.addWidget(self.reject_btn)
        action_layout.addWidget(self.remove_btn)
        left_layout.addWidget(action_group)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Friends"))
        self.friends_table = QTableWidget(0, 0)
        self.friends_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.friends_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.friends_table)

        right_layout.addWidget(QLabel("Pending Requests"))
        self.pending_table = QTableWidget(0, 0)
        self.pending_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pending_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.pending_table)

        layout.addWidget(left_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.send_btn.clicked.connect(self.on_send)
        self.accept_btn.clicked.connect(lambda: self.on_respond(True))
        self.reject_btn.clicked.connect(lambda: self.on_respond(False))
        self.remove_btn.clicked.connect(self.on_remove)
        self.friends_table.itemSelectionChanged.connect(self._on_friend_selected)
        self.pending_table.itemSelectionChanged.connect(self._on_pending_selected)

    def _on_friend_selected(self):
        selected = self.friends_table.selectedItems()
        if not selected:
            self._selected_friend_id = None
            return
        row = selected[0].row()
        self._selected_friend_id = int(self.friends_table.item(row, 0).text())

    def _on_pending_selected(self):
        selected = self.pending_table.selectedItems()
        if not selected:
            self._selected_pending_pair = None
            return
        row = selected[0].row()
        p1 = int(self.pending_table.item(row, 0).text())
        p2 = int(self.pending_table.item(row, 1).text())
        self._selected_pending_pair = (p1, p2)

    def on_send(self):
        username = self.target_username_edit.text().strip()
        if not username:
            return
        try:
            player_app.send_friend_request(self.player_id, username)
            self.target_username_edit.clear()
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Friend Request Failed", str(e))

    def on_respond(self, accept):
        if self._selected_pending_pair is None:
            QMessageBox.information(self, "No Selection", "Select a pending request first.")
            return
        try:
            player_app.respond_friend_request(*self._selected_pending_pair, accept)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def on_remove(self):
        if self._selected_friend_id is None:
            QMessageBox.information(self, "No Selection", "Select a friend to remove first.")
            return
        confirm = QMessageBox.question(self, "Confirm Remove", "Remove this friend?")
        if confirm == QMessageBox.Yes:
            try:
                player_app.remove_friend(self.player_id, self._selected_friend_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", str(e))

    def refresh(self):
        columns, rows = player_app.list_friends(self.player_id)
        populate_table(self.friends_table, columns, rows)
        columns, rows = player_app.list_pending_friend_requests(self.player_id)
        populate_table(self.pending_table, columns, rows)

# ===================================================== #
#                      Transfer Tab                     #
# ===================================================== #

class TransferTab(QWidget):
    def __init__(self, player_id):
        super().__init__()
        self.player_id = player_id
        self._active_games = {}
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        host_group = QGroupBox("Host a Game")
        host_form = QFormLayout(host_group)
        self.build_combo = QComboBox()
        self.host_lat_spin = QDoubleSpinBox()
        self.host_lat_spin.setRange(-90, 90)
        self.host_lat_spin.setDecimals(6)
        self.host_lng_spin = QDoubleSpinBox()
        self.host_lng_spin.setRange(-180, 180)
        self.host_lng_spin.setDecimals(6)
        self.host_role_combo = QComboBox()
        self.host_role_combo.addItems(["hunter", "hider"])
        self.host_btn = QPushButton("Host Game")
        host_form.addRow("Game Build:", self.build_combo)
        host_form.addRow("Center Latitude:", self.host_lat_spin)
        host_form.addRow("Center Longitude:", self.host_lng_spin)
        host_form.addRow("Your Role:", self.host_role_combo)
        host_form.addRow(self.host_btn)
        left_layout.addWidget(host_group)

        join_group = QGroupBox("Join a Game")
        join_form = QFormLayout(join_group)
        self.invite_code_edit = QLineEdit()
        self.invite_code_edit.setMaxLength(8)
        self.join_role_combo = QComboBox()
        self.join_role_combo.addItems(["hunter", "hider"])
        self.join_btn = QPushButton("Join Game")
        join_form.addRow("Invite Code:", self.invite_code_edit)
        join_form.addRow("Your Role:", self.join_role_combo)
        join_form.addRow(self.join_btn)
        left_layout.addWidget(join_group)

        live_group = QGroupBox("Live Game Activity")
        live_layout = QVBoxLayout(live_group)
        live_layout.addWidget(QLabel("Active Game:"))
        self.active_game_combo = QComboBox()
        live_layout.addWidget(self.active_game_combo)

        self.ping_btn = QPushButton("Send Location Ping")
        live_layout.addWidget(self.ping_btn)

        target_row = QHBoxLayout()
        self.target_combo = QComboBox()
        self.tag_btn = QPushButton("Tag Selected Player")
        target_row.addWidget(self.target_combo)
        target_row.addWidget(self.tag_btn)
        live_layout.addLayout(target_row)

        power_up_row = QHBoxLayout()
        self.power_up_combo = QComboBox()
        self.use_power_up_btn = QPushButton("Use Selected Power-Up")
        power_up_row.addWidget(self.power_up_combo)
        power_up_row.addWidget(self.use_power_up_btn)
        live_layout.addLayout(power_up_row)

        left_layout.addWidget(live_group)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Open Games"))
        self.games_table = QTableWidget(0, 0)
        self.games_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.games_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.games_table)
        self.refresh_btn = QPushButton("Refresh")
        right_layout.addWidget(self.refresh_btn)

        right_layout.addWidget(QLabel("Recent Game Events"))
        self.events_table = QTableWidget(0, 0)
        self.events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.events_table)

        layout.addWidget(left_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.host_btn.clicked.connect(self.on_host)
        self.join_btn.clicked.connect(self.on_join)
        self.refresh_btn.clicked.connect(self.refresh)
        self.active_game_combo.currentIndexChanged.connect(self._on_active_game_changed)
        self.ping_btn.clicked.connect(self.on_ping)
        self.tag_btn.clicked.connect(self.on_tag)
        self.use_power_up_btn.clicked.connect(self.on_use_power_up)

    def _reload_builds(self):
        self.build_combo.clear()
        _, rows = db.list_game_builds()
        for row in rows:
            build_id, name = row[0], row[1]
            self.build_combo.addItem(name, userData=build_id)

    def _reload_active_games(self):
        previous_game_id = self.active_game_combo.currentData()

        self.active_game_combo.blockSignals(True)
        self.active_game_combo.clear()
        self._active_games = {}
        _, rows = player_app.list_my_active_games(self.player_id)
        for row in rows:
            game_id, invite_code, status, role, center_lat, center_lng, initial_radius, build_name = row
            self._active_games[game_id] = row
            self.active_game_combo.addItem(f"{invite_code} ({status}) — {build_name}", userData=game_id)

        index = self.active_game_combo.findData(previous_game_id)
        if index == -1 and self.active_game_combo.count():
            index = 0
        self.active_game_combo.setCurrentIndex(index)
        self.active_game_combo.blockSignals(False)

        self._on_active_game_changed()

    def _on_active_game_changed(self):
        game_id = self.active_game_combo.currentData()

        self.target_combo.clear()
        self.power_up_combo.clear()

        if game_id is None:
            populate_table(self.events_table, [], [])
            return

        _, participant_rows = player_app.list_other_participants(game_id, self.player_id)
        for pid, username in participant_rows:
            self.target_combo.addItem(username, userData=pid)

        role = self._active_games[game_id][3]
        _, power_up_rows = player_app.list_power_ups_for_role(role)
        for power_up_id, name, effect_type, duration, cooldown_sec in power_up_rows:
            self.power_up_combo.addItem(name, userData=power_up_id)

        self._load_events(game_id)

    def _load_events(self, game_id):
        columns, rows = player_app.list_recent_game_events(game_id)
        populate_table(self.events_table, columns, rows)

    def on_host(self):
        build_id = self.build_combo.currentData()
        if build_id is None:
            QMessageBox.information(self, "No Builds", "No game builds are available to host with.")
            return
        try:
            game_id, code = player_app.host_game(
                self.player_id,
                build_id,
                self.host_lat_spin.value(),
                self.host_lng_spin.value(),
                self.host_role_combo.currentText(),
            )
            QMessageBox.information(self, "Game Created", f"Invite code: {code}")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def on_join(self):
        code = self.invite_code_edit.text().strip().upper()
        if not code:
            return
        try:
            player_app.join_game(self.player_id, code, self.join_role_combo.currentText())
            QMessageBox.information(self, "Joined", "You joined the game.")
            self.invite_code_edit.clear()
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Join Failed", str(e))

    def on_ping(self):
        game_id = self.active_game_combo.currentData()
        if game_id is None:
            QMessageBox.information(self, "No Active Game", "You have no pending/active games to interact with.")
            return
        _, _, _, _, center_lat, center_lng, initial_radius, _ = self._active_games[game_id]
        try:
            player_app.log_location_ping(game_id, self.player_id, center_lat, center_lng, initial_radius)
            self._load_events(game_id)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def on_tag(self):
        game_id = self.active_game_combo.currentData()
        target_id = self.target_combo.currentData()
        if game_id is None:
            QMessageBox.information(self, "No Active Game", "You have no pending/active games to interact with.")
            return
        if target_id is None:
            QMessageBox.information(self, "No Target", "There is no one else in this game to tag.")
            return
        _, _, _, _, center_lat, center_lng, initial_radius, _ = self._active_games[game_id]
        try:
            player_app.log_tag(game_id, self.player_id, target_id, center_lat, center_lng, initial_radius)
            self._load_events(game_id)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def on_use_power_up(self):
        game_id = self.active_game_combo.currentData()
        power_up_id = self.power_up_combo.currentData()
        if game_id is None:
            QMessageBox.information(self, "No Active Game", "You have no pending/active games to interact with.")
            return
        if power_up_id is None:
            QMessageBox.information(self, "No Power-Up", "No power-ups are available for your role.")
            return
        try:
            player_app.log_power_up_use(game_id, self.player_id, power_up_id)
            self._load_events(game_id)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def refresh(self):
        self._reload_builds()
        columns, rows = player_app.list_open_games()
        populate_table(self.games_table, columns, rows)
        self._reload_active_games()

# ===================================================== #
#                      History Tab                      #
# ===================================================== #

class HistoryTab(QWidget):
    def __init__(self, player_id):
        super().__init__()
        self.player_id = player_id
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        stats_form = QFormLayout()
        self.total_games_label = QLabel("0")
        self.wins_label = QLabel("0")
        self.tags_label = QLabel("0")
        stats_form.addRow("Total Games:", self.total_games_label)
        stats_form.addRow("Wins:", self.wins_label)
        stats_form.addRow("Tags Landed:", self.tags_label)
        left_layout.addLayout(stats_form)
        self.refresh_btn = QPushButton("Refresh")
        left_layout.addWidget(self.refresh_btn)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Match History"))
        self.history_table = QTableWidget(0, 0)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.history_table)

        layout.addWidget(left_widget, 1)
        layout.addLayout(right_layout, 2)

    def _connect_signals(self):
        self.refresh_btn.clicked.connect(self.refresh)

    def refresh(self):
        stats = player_app.get_player_stats(self.player_id)
        self.total_games_label.setText(str(stats["total_games"]))
        self.wins_label.setText(str(stats["wins"]))
        self.tags_label.setText(str(stats["total_tags_landed"]))

        columns, rows = player_app.get_player_history(self.player_id)
        populate_table(self.history_table, columns, rows)

# ===================================================== #
#                      Main Window                      #
# ===================================================== #

class PlayerMainWindow(QMainWindow):
    def __init__(self, player_row):
        super().__init__()
        self.player_id = player_row[0]
        self.player_row = player_row
        self.setWindowTitle(f"Manhunt: {player_row[1]}")
        self.resize(1000, 600)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.account_tab = AccountTab(self.player_id)
        self.friends_tab = FriendsTab(self.player_id)
        self.transfer_tab = TransferTab(self.player_id)
        self.history_tab = HistoryTab(self.player_id)

        self.tabs.addTab(self.account_tab, "Account")
        self.tabs.addTab(self.friends_tab, "Friends")
        self.tabs.addTab(self.transfer_tab, "Transfer")
        self.tabs.addTab(self.history_tab, "History")

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()


def main():
    app = QApplication(sys.argv)
    styles.apply_theme(app)

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    window = PlayerMainWindow(login.get_player_row())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

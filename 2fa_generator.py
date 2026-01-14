"""
2FA Code Generator
A simple tool to generate and auto-refresh TOTP 2FA codes
Shows all account information: Email, Password, Secondary Email, 2FA Code
"""
import sys
import time
import pyotp
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QProgressBar, QLineEdit, QGroupBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class ToastNotification(QLabel):
    """Small popup notification that disappears after a timeout"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QLabel {
                background-color: #323232;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def show_message(self, message, parent_widget, duration=2000):
        """Show toast message near the center of parent widget"""
        self.setText(message)
        self.adjustSize()

        # Position in center of parent window
        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)

        self.show()
        QTimer.singleShot(duration, self.hide)


class TwoFAGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.accounts = []  # List of {'email': ..., 'password': ..., 'backup': ..., 'secret': ...}
        self.existing_emails = set()  # Track emails to detect duplicates
        self.toast = ToastNotification()  # Small popup notification
        self.init_ui()

        # Auto-refresh timer (every 1 second to update countdown)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

    def init_ui(self):
        self.setWindowTitle("2FA Code Generator - Full Account View")
        self.resize(1000, 600)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # Title
        title = QLabel("2FA Code Generator")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Format hint
        format_hint = QLabel("Format: email----password----secondary_email----2fa_key (auto-detected)")
        format_hint.setStyleSheet("color: gray; font-style: italic;")
        format_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(format_hint)

        # Import section
        import_group = QGroupBox("Import Accounts")
        import_layout = QVBoxLayout()

        # Text input area for direct paste
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Paste account here: email----password----secondary_email----2fa_key")
        self.text_input.setFixedHeight(35)
        self.text_input.returnPressed.connect(self.add_from_text_input)
        import_layout.addWidget(self.text_input)

        # Buttons row
        btn_layout = QHBoxLayout()

        self.btn_add_line = QPushButton("Add This Account")
        self.btn_add_line.clicked.connect(self.add_from_text_input)
        self.btn_add_line.setFixedHeight(35)
        self.btn_add_line.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_add_line)

        self.btn_import = QPushButton("Import from File")
        self.btn_import.clicked.connect(self.import_from_file)
        self.btn_import.setFixedHeight(35)
        self.btn_import.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_import)

        self.btn_paste = QPushButton("Paste from Clipboard")
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        self.btn_paste.setFixedHeight(35)
        self.btn_paste.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_paste)

        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self.clear_accounts)
        self.btn_clear.setFixedHeight(35)
        self.btn_clear.setStyleSheet("background-color: #f44336; color: white;")
        btn_layout.addWidget(self.btn_clear)

        self.btn_remove_duplicates = QPushButton("Remove Duplicates")
        self.btn_remove_duplicates.clicked.connect(self.remove_all_duplicates)
        self.btn_remove_duplicates.setFixedHeight(35)
        self.btn_remove_duplicates.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.btn_remove_duplicates.setToolTip("Remove all duplicate accounts, keep only the first occurrence")
        btn_layout.addWidget(self.btn_remove_duplicates)

        import_layout.addLayout(btn_layout)
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        # Countdown bar
        countdown_layout = QHBoxLayout()
        countdown_layout.addWidget(QLabel("Code expires in:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(30)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v seconds")
        countdown_layout.addWidget(self.progress_bar)

        self.btn_refresh = QPushButton("Refresh Codes")
        self.btn_refresh.clicked.connect(self.refresh_codes)
        self.btn_refresh.setStyleSheet("background-color: #4CAF50; color: white;")
        countdown_layout.addWidget(self.btn_refresh)

        layout.addLayout(countdown_layout)

        # Table - now with all account info
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Email", "Password", "Secondary Email", "2FA Key", "2FA Code", "Delete"
        ])

        # Set column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Email
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Password
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Secondary
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # 2FA Key
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Code
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Delete

        # Set default column widths
        self.table.setColumnWidth(1, 120)  # Password
        self.table.setColumnWidth(3, 150)  # 2FA Key

        # Make table read-only (not editable)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Click to copy - connect cell click signal
        self.table.cellClicked.connect(self.on_cell_clicked)

        layout.addWidget(self.table)

        # Account count and status
        status_layout = QHBoxLayout()
        self.count_label = QLabel("Accounts: 0")
        self.count_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        status_layout.addWidget(self.count_label)

        status_layout.addStretch()

        self.status_label = QLabel("Ready. Import a file or paste account data.")
        self.status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self.status_label)

        layout.addLayout(status_layout)

        # Initial display
        self.update_display()

    def get_remaining_seconds(self):
        """Get seconds remaining until next TOTP code change"""
        return 30 - (int(time.time()) % 30)

    def update_display(self):
        """Update countdown bar and refresh codes if needed"""
        remaining = self.get_remaining_seconds()
        self.progress_bar.setValue(remaining)

        # Change color based on time remaining
        if remaining <= 5:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
        elif remaining <= 10:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
        else:
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")

        # Refresh codes when timer resets (remaining == 30)
        if remaining == 30:
            self.refresh_codes()

    def refresh_codes(self):
        """Refresh all 2FA codes in the table"""
        for row in range(self.table.rowCount()):
            secret_item = self.table.item(row, 3)  # 2FA Key is column 3
            if secret_item:
                secret = secret_item.data(Qt.ItemDataRole.UserRole)  # Get full secret from stored data
                if secret:
                    try:
                        code = self.generate_code(secret)
                        code_item = QTableWidgetItem(code)
                        code_item.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                        code_item.setForeground(QColor("#2196F3"))
                        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table.setItem(row, 4, code_item)
                    except:
                        pass

    def generate_code(self, secret):
        """Generate TOTP code from secret"""
        clean_secret = secret.strip().replace(" ", "").replace("-", "").upper()
        totp = pyotp.TOTP(clean_secret)
        return totp.now()

    def detect_separator(self, lines):
        """Auto-detect the separator used in the file"""
        # Check first line for separator declaration
        first_line = lines[0].strip() if lines else ""

        if first_line.startswith("分隔符="):
            sep = first_line.split("=")[1].strip().strip('"').strip("'")
            return sep, lines[1:]  # Return separator and remaining lines

        # Auto-detect from content
        separators = ["----", "---", "||", "|", "\t", ","]

        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            for sep in separators:
                parts = line.split(sep)
                if len(parts) >= 2:  # At least email and something else
                    return sep, lines

        return "----", lines  # Default

    def parse_account_line(self, line, separator):
        """Parse a single account line into components"""
        parts = line.split(separator)

        account = {
            'email': parts[0].strip() if len(parts) > 0 else '',
            'password': parts[1].strip() if len(parts) > 1 else '',
            'backup': parts[2].strip() if len(parts) > 2 else '',
            'secret': parts[3].strip() if len(parts) > 3 else ''
        }

        return account

    def import_from_file(self):
        """Import accounts from a text file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Account File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.process_lines(lines)

        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to import file:\n{e}")

    def add_from_text_input(self):
        """Add account from the text input field"""
        text = self.text_input.text().strip()

        if not text:
            QMessageBox.warning(self, "Empty Input", "Please paste an account line in the text box first.")
            return

        # Process single line
        self.process_lines([text])

        # Clear input
        self.text_input.clear()
        self.text_input.setFocus()

    def paste_from_clipboard(self):
        """Import accounts from clipboard"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()

        print(f"[DEBUG] Clipboard text: '{text[:100]}...' (length: {len(text)})")  # Debug

        if not text.strip():
            QMessageBox.warning(self, "Empty Clipboard", "Clipboard is empty. Copy some account data first.")
            return

        lines = text.strip().split('\n')
        print(f"[DEBUG] Found {len(lines)} lines")  # Debug
        self.process_lines(lines)

    def process_lines(self, lines):
        """Process lines of account data"""
        # Detect separator
        separator, data_lines = self.detect_separator(lines)

        count = 0
        duplicate_count = 0
        for line in data_lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            account = self.parse_account_line(line, separator)

            # Add account even if no 2FA key (will show empty code)
            is_dup = self.add_account_to_table(account)
            count += 1
            if is_dup:
                duplicate_count += 1

        self.count_label.setText(f"Accounts: {self.table.rowCount()}")

        # Show summary with duplicate info
        if duplicate_count > 0:
            self.status_label.setText(f"Imported {count} accounts. Found {duplicate_count} duplicates (yellow). Click 'Remove Duplicates' to clean.")
            self.status_label.setStyleSheet("color: orange;")
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {count} accounts.\n\nFound {duplicate_count} duplicate(s) (marked yellow).\n\nClick 'Remove Duplicates' to keep only unique accounts."
            )
        else:
            self.status_label.setText(f"Imported {count} accounts. No duplicates found.")
        self.status_label.setStyleSheet("color: green;")

    def add_account_to_table(self, account):
        """Add an account row to the table with all information. Returns True if duplicate."""
        email = account.get('email', '').lower().strip()

        # Check for duplicate (don't ask, just mark)
        is_duplicate = email in self.existing_emails

        # Add to tracking set
        self.existing_emails.add(email)

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Column 0: Email (mark duplicate with color)
        email_item = QTableWidgetItem(account.get('email', ''))
        if is_duplicate:
            email_item.setBackground(QColor("#FFEB3B"))  # Yellow background for duplicate
            email_item.setToolTip("DUPLICATE - This email already exists!")
        self.table.setItem(row, 0, email_item)

        # Column 1: Password
        password = account.get('password', '')
        password_item = QTableWidgetItem(password)
        if is_duplicate:
            password_item.setBackground(QColor("#FFEB3B"))
        self.table.setItem(row, 1, password_item)

        # Column 2: Secondary Email
        backup_item = QTableWidgetItem(account.get('backup', ''))
        if is_duplicate:
            backup_item.setBackground(QColor("#FFEB3B"))
        self.table.setItem(row, 2, backup_item)

        # Column 3: 2FA Key (show partial for security, store full)
        secret = account.get('secret', '')
        if secret:
            display_secret = secret[:6] + "..." + secret[-4:] if len(secret) > 10 else secret
        else:
            display_secret = "(none)"
        secret_item = QTableWidgetItem(display_secret)
        secret_item.setData(Qt.ItemDataRole.UserRole, secret)  # Store full secret
        secret_item.setToolTip(f"Full key: {secret}")  # Show on hover
        if is_duplicate:
            secret_item.setBackground(QColor("#FFEB3B"))
        self.table.setItem(row, 3, secret_item)

        # Column 4: 2FA Code
        if secret:
            try:
                code = self.generate_code(secret)
                code_item = QTableWidgetItem(code)
                code_item.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                code_item.setForeground(QColor("#2196F3"))
                code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception as e:
                code_item = QTableWidgetItem("ERROR")
                code_item.setForeground(QColor("red"))
                code_item.setToolTip(str(e))
        else:
            code_item = QTableWidgetItem("-")
            code_item.setForeground(QColor("gray"))
        if is_duplicate:
            code_item.setBackground(QColor("#FFEB3B"))
        self.table.setItem(row, 4, code_item)

        # Column 5: Delete button (small)
        btn_delete = QPushButton("X")
        btn_delete.setFixedSize(25, 25)
        btn_delete.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; font-size: 10px;")
        btn_delete.setToolTip("Delete this account")
        btn_delete.clicked.connect(lambda checked, r=row: self.delete_row(r))
        self.table.setCellWidget(row, 5, btn_delete)

        return is_duplicate  # Return True if this was a duplicate

    def on_cell_clicked(self, row, column):
        """Copy cell content to clipboard when clicked"""
        # Don't copy if clicking the Delete button column
        if column == 5:
            return

        item = self.table.item(row, column)
        if item:
            text = item.text()
            # For 2FA Key column, get the full key from stored data
            if column == 3:
                full_key = item.data(Qt.ItemDataRole.UserRole)
                if full_key:
                    text = full_key

            if text and text != "(none)" and text != "-":
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                # Show which column was copied
                column_names = ["Email", "Password", "Secondary Email", "2FA Key", "2FA Code"]
                col_name = column_names[column] if column < len(column_names) else "Text"

                # Show toast notification popup
                toast_text = f"Copied {col_name}!"
                self.toast.show_message(toast_text, self, 1000)

    def remove_all_duplicates(self):
        """Remove all duplicate accounts, keeping only the first occurrence of each email"""
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "No Accounts", "No accounts to process.")
            return

        seen_emails = set()
        rows_to_delete = []

        # Find all duplicate rows (keep first occurrence, mark later ones for deletion)
        for row in range(self.table.rowCount()):
            email_item = self.table.item(row, 0)
            if email_item:
                email = email_item.text().lower().strip()
                if email in seen_emails:
                    rows_to_delete.append(row)
                else:
                    seen_emails.add(email)

        if not rows_to_delete:
            QMessageBox.information(self, "No Duplicates", "No duplicate accounts found.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Remove Duplicates",
            f"Found {len(rows_to_delete)} duplicate account(s).\n\nRemove them and keep only unique accounts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete rows from bottom to top (so indices don't shift)
            for row in reversed(rows_to_delete):
                self.table.removeRow(row)

            # Rebuild tracking set
            self.existing_emails.clear()
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item:
                    self.existing_emails.add(item.text().lower().strip())

            # Reconnect buttons
            self.reconnect_buttons()

            # Update UI
            self.count_label.setText(f"Accounts: {self.table.rowCount()}")
            self.status_label.setText(f"Removed {len(rows_to_delete)} duplicates. {self.table.rowCount()} unique accounts remain.")
            self.status_label.setStyleSheet("color: green;")

            QMessageBox.information(
                self,
                "Duplicates Removed",
                f"Removed {len(rows_to_delete)} duplicate(s).\n\n{self.table.rowCount()} unique accounts remain."
            )

    def copy_code(self, row):
        """Copy 2FA code to clipboard"""
        # Find the actual row (in case rows were deleted)
        actual_row = self.find_row_by_original(row)
        if actual_row < 0:
            return

        code_item = self.table.item(actual_row, 4)
        if code_item:
            code = code_item.text()
            if code and code != "-" and code != "ERROR":
                clipboard = QApplication.clipboard()
                clipboard.setText(code)
                self.status_label.setText(f"Copied code: {code}")
                self.status_label.setStyleSheet("color: blue;")
            else:
                self.status_label.setText("No valid code to copy")
                self.status_label.setStyleSheet("color: red;")

    def find_row_by_original(self, original_row):
        """Find the current row index (rows may shift after deletions)"""
        # For simplicity, we'll just return the row if it exists
        if original_row < self.table.rowCount():
            return original_row
        return -1

    def delete_row(self, row):
        """Delete a single account row with confirmation"""
        # Get the email for confirmation message
        email_item = self.table.item(row, 0)
        email = email_item.text() if email_item else "this account"

        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete:\n\n{email}\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return  # User cancelled

        # Remove the row
        self.table.removeRow(row)

        # Rebuild existing_emails set from remaining rows
        self.existing_emails.clear()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                self.existing_emails.add(item.text().lower().strip())

        # Update count
        self.count_label.setText(f"Accounts: {self.table.rowCount()}")
        self.status_label.setText("Account deleted.")
        self.status_label.setStyleSheet("color: orange;")

        # Reconnect buttons for remaining rows (row indices changed)
        self.reconnect_buttons()

    def reconnect_buttons(self):
        """Reconnect all button callbacks after row deletion"""
        for row in range(self.table.rowCount()):
            # Reconnect Delete button at column 5 (small)
            btn_delete = QPushButton("X")
            btn_delete.setFixedSize(25, 25)
            btn_delete.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; font-size: 10px;")
            btn_delete.setToolTip("Delete this account")
            btn_delete.clicked.connect(lambda checked, r=row: self.delete_row(r))
            self.table.setCellWidget(row, 5, btn_delete)

    def clear_accounts(self):
        """Clear all accounts from table"""
        if self.table.rowCount() == 0:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Are you sure you want to clear all accounts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.table.setRowCount(0)
            self.existing_emails.clear()  # Clear tracking set
            self.count_label.setText("Accounts: 0")
            self.status_label.setText("All accounts cleared.")
            self.status_label.setStyleSheet("color: gray;")


def main():
    app = QApplication(sys.argv)

    # Set font
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    window = TwoFAGenerator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

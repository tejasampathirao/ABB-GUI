# open_gui_merged2.py
# Full merged main GUI with Product Code -> Inventory integration
# Preserves original ASRS callbacks and pipeline; adds inventory highlight/filter.

import sys
import os
import traceback
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QMessageBox, QFrame,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QSizePolicy, QDialog, QComboBox, QTextEdit, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QFont

# ---------- ASRS (game) code imports (SAFE) ----------
_game3_error = None
_game3_loaded = False
try:
    # We only need read APIs; do NOT merge code, just use callbacks.
    from game_3 import load_game_state, get_all_models, ASRSWindow
    _game3_loaded = True
except Exception as _e:
    _game3_error = traceback.format_exc()
    _game3_loaded = False

# Expected files (make sure these filenames exactly match files in the folder)
EXPECTED_MODULES = [
    "tray_config_window.py",
    "call_tray_details.py",
    "inventory_list.py",
    "tray_data.py",
    "tray_partition.py",
    "settings_window.py",
    "machine_status.py",
    "available_space.py",
    "material_tracking.py",
]

def check_required_files():
    missing = []
    cwd = os.path.dirname(os.path.abspath(__file__))
    for fname in EXPECTED_MODULES:
        if not os.path.exists(os.path.join(cwd, fname)):
            missing.append(fname)
    return missing

# Submodule holders and error dict
_submodule_errors = {}
TrayConfigWindow = None
CallTrayDetailsWindow = None
InventoryListWindow = None
TrayDataWindow = None
TrayPartitionWindow = None
SettingsWindow = None
MachineStatusWindow = None
AvailableSpaceWindow = None
MaterialTrackingWindow = None

# Attempt imports safely and store tracebacks for diagnostics
missing_files = check_required_files()
if missing_files:
    _submodule_errors["missing_files"] = "Missing module files:\n" + "\n".join(missing_files)
else:
    try:
        from tray_config_window import TrayConfigWindow
    except Exception:
        _submodule_errors["tray_config_window"] = traceback.format_exc()
    try:
        from call_tray_details import CallTrayDetailsWindow
    except Exception:
        _submodule_errors["call_tray_details"] = traceback.format_exc()
    try:
        from inventory_list import InventoryListWindow
    except Exception:
        _submodule_errors["inventory_list"] = traceback.format_exc()
    try:
        from tray_data import TrayDataWindow
    except Exception:
        _submodule_errors["tray_data"] = traceback.format_exc()
    try:
        from tray_partition import TrayPartitionWindow
    except Exception:
        _submodule_errors["tray_partition"] = traceback.format_exc()
    try:
        from settings_window import SettingsWindow
    except Exception:
        _submodule_errors["settings_window"] = traceback.format_exc()
    try:
        from machine_status import MachineStatusWindow
    except Exception:
        _submodule_errors["machine_status"] = traceback.format_exc()
    try:
        from available_space import AvailableSpaceWindow
    except Exception:
        _submodule_errors["available_space"] = traceback.format_exc()
    try:
        from material_tracking import MaterialTrackingWindow
    except Exception:
        _submodule_errors["material_tracking"] = traceback.format_exc()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABB Project - Home Page (Robust Loader)")
        self.setMinimumSize(1280, 780)
        self.setGeometry(200, 100, 1100, 850)  # ensures visible window

        # 🟫 Main window background color
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f3d9b1;
                color: black;
            }
        """)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ================================
        # 🟩 Top Bar Section
        # ================================
        top_bar_container = QWidget()
        top_bar_container.setStyleSheet("""
            background-color: #21cc93;
            border-radius: 10px;
        """)
        top_bar_layout = QHBoxLayout(top_bar_container)
        top_bar_layout.setContentsMargins(10, 6, 10, 6)
        top_bar_layout.setSpacing(10)

        # Timestamp label (left side)
        self.datetime_label = QLabel()
        self.datetime_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.datetime_label.setStyleSheet("color: white;")
        top_bar_layout.addWidget(self.datetime_label, alignment=Qt.AlignLeft)

        # Spacer between left & right items
        top_bar_layout.addStretch(1)

        # ================================
        # Icon Button Creator
        # ================================
        def mk_top_icon(sym, tip, cb=None):
            b = QPushButton(sym)
            b.setToolTip(tip)
            b.setFixedSize(48, 48)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #EDEFF2;
                    color: #333333;
                    font-size: 20px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                    color: white;
                }
            """)
            if cb:
                b.clicked.connect(cb)
            return b

        # ================================
        # Top Bar Icons (Right Side)
        # ================================
        btn_settings_top = mk_top_icon("⚙", "Settings", self.open_settings_window)
        btn_user_top = mk_top_icon("👤", "User", lambda: QMessageBox.information(self, "Users", "Users (placeholder)"))
        btn_home_top = mk_top_icon("🏠", "Home", lambda: self.stack.setCurrentWidget(self.home_page) if hasattr(self, "stack") and hasattr(self, "home_page") else None)
        btn_lock_top = mk_top_icon("🔒", "Lock", lambda: QMessageBox.information(self, "Lock", "Lock (placeholder)"))
        btn_power_top = mk_top_icon("⏻", "Power", self.close)

        # Add icons (settings first)
        top_bar_layout.addWidget(btn_settings_top, alignment=Qt.AlignRight)
        top_bar_layout.addWidget(btn_user_top, alignment=Qt.AlignRight)
        top_bar_layout.addWidget(btn_home_top, alignment=Qt.AlignRight)
        top_bar_layout.addWidget(btn_lock_top, alignment=Qt.AlignRight)
        top_bar_layout.addWidget(btn_power_top, alignment=Qt.AlignRight)

        # Add top bar to main layout
        root.addWidget(top_bar_container)

        # clock update
        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(1000)
        self._update_clock()

        # show a warning if some submodules failed to load
        if _submodule_errors:
            err_label = QLabel("⚠︎ Some submodules failed to load — open console or click 'Show Errors'")
            err_label.setStyleSheet("color: #d84315; font-weight:700;")
            root.addWidget(err_label)
            btn_show = QPushButton("Show Errors")
            btn_show.setFixedHeight(36)
            btn_show.clicked.connect(self.show_submodule_errors)
            root.addWidget(btn_show)

        # stacked pages (we keep home + settings stacked; machine status opens as its own window)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.home_page = self._build_home_page()
        self.settings_page = self._build_settings_page()

        for p in (self.home_page, self.settings_page):
            self.stack.addWidget(p)
        self.stack.setCurrentWidget(self.home_page)

        # store created subwindows
        self._tray_windows = {}

        # Pre-cache model list from ASRS (if available)
        self._model_list = []  # list[(id, name)]
        if _game3_loaded:
            try:
                self._model_list = get_all_models()
            except Exception:
                # keep empty; handlers will try again and show friendly msg
                pass

    def _update_clock(self):
        self.datetime_label.setText(QDateTime.currentDateTime().toString("dddd, MMMM d, yyyy  hh:mm:ss AP"))

    # =================== HOME PAGE ===================
    def _build_home_page(self):
        # Home page GUI that matches screenshot: two-card header + colorful tiles
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(16)

        # ---------- Upper content area (two large cards side-by-side) ----------
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Left card: Product Code / Serial Number + Fetch Product
        left_card = QFrame()
        left_card.setFrameShape(QFrame.StyledPanel)
        left_card.setStyleSheet("background: #f75e75; border-radius:10px;")
        left_layout = QHBoxLayout(left_card)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)

        left_form = QVBoxLayout()
        lbl_product = QLabel("Product Code")
        lbl_product.setStyleSheet("font-size:16px; color:black;")
        lbl_product.setMinimumHeight(28)
        left_form.addWidget(lbl_product)

        # single line edit to enter product code or serial (keeps UI compact)
        self.product_code_edit = QLineEdit()
        self.product_code_edit.setFixedWidth(220)
        self.product_code_edit.setPlaceholderText("Enter / choose product code or serial")
        self.product_code_edit.setStyleSheet("font-size:20px; padding:8px;")
        left_form.addWidget(self.product_code_edit)

        # alias for backward compatibility with older callbacks
        self.tray_number_edit = self.product_code_edit

        # Row with "Product Code" and "Serial Number" buttons
        row_buttons = QHBoxLayout()
        self.btn_product_code = QPushButton("Product Code")
        self.btn_product_code.setToolTip("Choose a product code from ASRS models")
        self.btn_product_code.setFixedHeight(40)
        self.btn_product_code.setStyleSheet(
            "background:#000000; color:white; font-weight:700; border-radius:8px;"
        )

        self.btn_serial_number = QPushButton("Serial Number")
        self.btn_serial_number.setToolTip("Choose or show serial number for a product/tray")
        self.btn_serial_number.setFixedHeight(40)
        self.btn_serial_number.setStyleSheet(
            "background:#00796b; color:white; font-weight:700; border-radius:8px;"
        )

        # Connect to the (new) handler names — implement these methods in your MainWindow
        # Product Code now opens Inventory List and highlights matching row
        self.btn_product_code.clicked.connect(lambda: self._open_inventory_list_with_product())
        self.btn_serial_number.clicked.connect(self._choose_serial_number)

        row_buttons.addWidget(self.btn_product_code)
        row_buttons.addWidget(self.btn_serial_number)
        left_form.addLayout(row_buttons)

        left_form.addStretch(1)
        left_layout.addLayout(left_form)

        # Fetch Product orange square button -> wired to ASRS callback (renamed)
        fetch_btn = QPushButton("⬇\nFetch Product")
        fetch_btn.setFixedSize(140, 120)
        fetch_btn.setStyleSheet("""
            QPushButton {
                background: #61aced;
                color: white;
                font-weight:700;
                font-size:16px;
                border-radius:10px;
            }
            QPushButton:pressed { background:#d84315; }
        """)
        fetch_btn.clicked.connect(self._fetch_product_from_asrs)
        left_layout.addWidget(fetch_btn, alignment=Qt.AlignRight)

        top_row.addWidget(left_card, 2)


        # Right card: Child Part, Model, Search + Master Data / Sample Format
        right_card = QFrame()
        right_card.setFrameShape(QFrame.StyledPanel)
        right_card.setStyleSheet("background: #f75e75; border-radius:10px;")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)

        lbl_child = QLabel("Child Part")
        lbl_child.setStyleSheet("font-size:15px; color:#000;")
        self.child_part_edit = QLineEdit()
        self.child_part_edit.setPlaceholderText("Child part")
        self.child_part_edit.setFixedHeight(36)

        lbl_model = QLabel("Model")
        lbl_model.setStyleSheet("font-size:15px; color:#333;")
        self.model_edit_home = QLineEdit()
        self.model_edit_home.setPlaceholderText("Model")
        self.model_edit_home.setFixedHeight(36)

        row2 = QHBoxLayout()
        left_inputs = QVBoxLayout()
        left_inputs.addWidget(lbl_child)
        left_inputs.addWidget(self.child_part_edit)
        left_inputs.addWidget(lbl_model)
        left_inputs.addWidget(self.model_edit_home)

        row2.addLayout(left_inputs, 1)

        right_buttons_col = QVBoxLayout()
        right_buttons_col.setSpacing(10)
        btn_search = QPushButton("Search")
        btn_search.setFixedSize(100, 80)
        btn_search.setStyleSheet("background:#63c7f2; color:white; font-weight:700; border-radius:8px;")
        btn_master = QPushButton("Master Data")
        btn_master.setFixedSize(120, 44)
        btn_master.setStyleSheet("background:#63c7f2; color:white; font-weight:700; border-radius:8px;")
        btn_sample = QPushButton("Sample Format")
        btn_sample.setFixedSize(120, 44)
        btn_sample.setStyleSheet("background:#63c7f2; color:white; font-weight:700; border-radius:8px;")

        # Placeholders (unchanged)
        btn_search.clicked.connect(lambda: QMessageBox.information(self, "Search", "Search (placeholder)"))
        btn_master.clicked.connect(lambda: QMessageBox.information(self, "Master Data", "Master Data (placeholder)"))
        btn_sample.clicked.connect(lambda: QMessageBox.information(self, "Sample Format", "Sample Format (placeholder)"))

        right_buttons_col.addWidget(btn_search, alignment=Qt.AlignTop)
        right_buttons_col.addSpacing(12)
        right_buttons_col.addWidget(btn_master)
        right_buttons_col.addWidget(btn_sample)
        row2.addLayout(right_buttons_col, 0)

        right_layout.addLayout(row2)
        top_row.addWidget(right_card, 3)

        page_layout.addLayout(top_row)

        # ---------- Middle: thin divider ----------
        divider = QFrame()
        divider.setFixedHeight(10)
        divider.setStyleSheet("background: transparent;")
        page_layout.addWidget(divider)

        # ---------- Bottom icon row (square action tiles) ----------
        tiles_frame = QFrame()
        tiles_frame.setStyleSheet("background: transparent;")
        tiles_layout = QHBoxLayout(tiles_frame)
        tiles_layout.setSpacing(14)
        tiles_layout.setContentsMargins(6, 6, 6, 6)

        def mk_tile(title, color, cb=None, w=120, h=120):
            b = QPushButton(title)
            b.setFixedSize(w, h)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    font-weight:700;
                    border-radius:10px;
                    font-size:13px;
                }}
                QPushButton:pressed {{ background: #222; }}
            """)
            if cb:
                b.clicked.connect(cb)
            return b

        tiles = [
            ("Tray Data", "#63c7f2", lambda: self._safe_open("tray_data", "Tray Data", TrayDataWindow)),
            ("Inventory List", "#6dedb6", lambda: self._safe_open("inventory_list", "Inventory List", InventoryListWindow)),
            ("Material\nTracking", "#f58356", lambda: self._safe_open("material_tracking", "Material Tracking", MaterialTrackingWindow)),
            ("Available\nSpace", "#f2d36d", lambda: self._safe_open("available_space", "Available Space", AvailableSpaceWindow)),
            ("Call Tray\nDetails", "#9ef056", lambda: self._safe_open("call_tray_details", "Call Tray Details", CallTrayDetailsWindow)),
            ("Machine\nStatus", "#4a9bf7", lambda: self.open_machine_status_window()),
            ("Tray\nConfiguration", "#66bb6a", lambda: self._safe_open("tray_config_window", "Tray Configuration", TrayConfigWindow)),
            ("Tray\nPartition", "#9b63eb", lambda: self._safe_open("tray_partition", "Tray Partition", TrayPartitionWindow)),
        ]

        for title, color, cb in tiles:
            tiles_layout.addWidget(mk_tile(title, color, cb))

        page_layout.addWidget(tiles_frame)

        page_layout.addStretch(1)
        return page

    # =================== SETTINGS PAGE ===================
    def _build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(QLabel("⚙️ SETTINGS PAGE (use top Settings icon to open full settings window)"))
        back = QPushButton("⬅ Back to Home")
        back.clicked.connect(lambda: self.stack.setCurrentWidget(self.home_page))
        layout.addWidget(back)
        return page

    # =================== ASRS CALLBACKS ===================
    def _ensure_game_loaded(self) -> bool:
        if not _game3_loaded:
            QMessageBox.critical(self, "ASRS unavailable",
                                 "game_3.py could not be loaded.\n\nDetails:\n" + (_game3_error or "Unknown import error"))
            return False
        return True

    def _reload_models(self):
        try:
            self._model_list = get_all_models()
        except Exception as e:
            self._model_list = []
            raise e

    def _choose_model_no(self):
        """Open a tiny dialog to pick a model number from ASRS, then fill the input."""
        if not self._ensure_game_loaded():
            return
        try:
            self._reload_models()
            if not self._model_list:
                QMessageBox.information(self, "No models", "No models found in ASRS.")
                return

            dlg = QDialog(self)
            dlg.setWindowTitle("Choose Model Number")
            v = QVBoxLayout(dlg)
            v.addWidget(QLabel("Select model:"))
            combo = QComboBox()
            for mid, mname in self._model_list:
                combo.addItem(mname, mid)
            v.addWidget(combo)
            row = QHBoxLayout()
            ok = QPushButton("OK"); cancel = QPushButton("Cancel")
            ok.clicked.connect(dlg.accept); cancel.clicked.connect(dlg.reject)
            row.addWidget(ok); row.addWidget(cancel)
            v.addLayout(row)
            if dlg.exec() == QDialog.Accepted:
                # fill into the product_code_edit alias for compatibility
                self.tray_number_edit.setText(combo.currentText())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load models:\n{e}")
            print(traceback.format_exc())

    def _show_model_tray_info(self):
        """
        Show how many trays (boxes) exist per model from the saved ASRS state.
        Uses game_3.load_game_state(); does NOT modify or merge code.
        """
        if not self._ensure_game_loaded():
            return
        try:
            # Load models and rack
            self._reload_models()
            rack = load_game_state()
            if rack is None:
                QMessageBox.information(self, "No ASRS state",
                                        "No saved ASRS state found yet.\nAdd/store boxes in the ASRS screen first.")
                return

            # Build counts
            id_to_name = {mid: mname for (mid, mname) in self._model_list}
            counts = {}
            for bid, box in rack.boxes.items():
                m_id = getattr(box, "model_id", None)
                if m_id is None:
                    continue
                counts[m_id] = counts.get(m_id, 0) + 1

            if not counts:
                QMessageBox.information(self, "No trays", "No trays/boxes stored in the current ASRS state.")
                return

            # Pretty list
            lines = []
            for mid, cnt in sorted(counts.items(), key=lambda x: id_to_name.get(x[0], str(x[0]))):
                lines.append(f"{id_to_name.get(mid, f'Model {mid}')}  ->  {cnt} tray(s)")

            msg = "\n".join(lines)
            QMessageBox.information(self, "Model Tray Summary", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read ASRS state:\n{e}")
            print(traceback.format_exc())

    def _fetch_model_from_asrs(self):
        """
        On 'Fetch model' button: read model name, find model id, and show:
          - how many trays for that model
          - where each tray is placed (rack grid row, col), using rack.box_positions
        """
        if not self._ensure_game_loaded():
            return
        try:
            model_name = (self.tray_number_edit.text() or "").strip()
            if not model_name:
                QMessageBox.warning(self, "Missing", "Enter or choose a model number first (Model No).")
                return

            # Ensure latest models and find the model_id by name
            self._reload_models()
            name_to_id = {mname: mid for (mid, mname) in self._model_list}
            if model_name not in name_to_id:
                # allow case-insensitive fallback
                lower_map = {mname.lower(): mid for (mid, mname) in self._model_list}
                if model_name.lower() in lower_map:
                    model_id = lower_map[model_name.lower()]
                    # fix user-visible name to exact casing
                    for n, mid in name_to_id.items():
                        if mid == model_id:
                            model_name = n
                            break
                else:
                    QMessageBox.warning(self, "Unknown model",
                                        f"Model '{model_name}' not found in ASRS models.\nUse 'Model No' to choose.")
                    return
            else:
                model_id = name_to_id[model_name]

            # Load ASRS state (Rack with positions)
            rack = load_game_state()
            if rack is None:
                QMessageBox.information(self, "No ASRS state",
                                        "No saved ASRS state found yet.\nStore boxes for this model in ASRS first.")
                return

            # Collect all box_ids for this model and their positions
            box_ids = [bid for bid, box in rack.boxes.items() if getattr(box, "model_id", None) == model_id]
            if not box_ids:
                QMessageBox.information(self, "No trays",
                                        f"No trays found for model '{model_name}'.")
                return

            # Positions
            lines = [f"Model: {model_name} (ID {model_id})",
                     f"Total trays: {len(box_ids)}",
                     "Placement locations (row, col):"]
            for bid in sorted(box_ids):
                pos = rack.box_positions.get(bid)
                if pos:
                    lines.append(f"  • Tray #{bid} -> ({pos[0]}, {pos[1]})")
                else:
                    lines.append(f"  • Tray #{bid} -> <position not recorded>")

            msg = "\n".join(lines)

            # Show in a readable dialog with copy-friendly text area
            dlg = QDialog(self)
            dlg.setWindowTitle("Fetch Model Result")
            v = QVBoxLayout(dlg)
            out = QTextEdit()
            out.setReadOnly(True)
            out.setMinimumSize(520, 320)
            out.setText(msg)
            v.addWidget(out)
            btns = QHBoxLayout()
            ok = QPushButton("OK")
            ok.clicked.connect(dlg.accept)
            btns.addStretch(1); btns.addWidget(ok)
            v.addLayout(btns)
            dlg.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch model info:\n{e}")
            print(traceback.format_exc())

    # =================== New Product / Inventory Handlers ===================
    def _choose_product_code(self):
        """
        Open dialog to select/enter product code then open inventory showing that code.
        (Kept for backward compatibility; main button now calls _open_inventory_list_with_product.)
        """
        code, ok = QInputDialog.getText(self, "Select Product Code", "Enter product code:")
        if ok and code:
            self.product_code_edit.setText(code)
            print(f"Product code selected: {code}")
            self._open_inventory_list_with_product(code)

    def _choose_serial_number(self):
        """Open dialog to enter or select serial number and open inventory list for it."""
        serial, ok = QInputDialog.getText(self, "Select Serial Number", "Enter serial number:")
        if ok and serial:
            self.product_code_edit.setText(serial)  # or use a separate field if desired
            print(f"Serial number selected: {serial}")
            self._open_inventory_list_with_product(serial)

    def _fetch_product_from_asrs(self):
        """
        Called by Fetch Product button. Kept to call original ASRS fetch flow if desired,
        then open Inventory list for the product code in the edit.
        """
        product_code = (self.product_code_edit.text() or "").strip()
        if not product_code:
            QMessageBox.warning(self, "Missing Input", "Please enter or select a product code first.")
            return
        print(f"Fetching product info for: {product_code}")
        # Optionally reuse earlier model-fetch flow (if logic expects model names):
        # We'll call _fetch_model_from_asrs() if appropriate (keeps old behavior).
        try:
            # _fetch_model_from_asrs expects to read from tray_number_edit alias - so keep compatibility
            self._fetch_model_from_asrs()
        except Exception:
            # don't break on ASRS errors here; show friendly message
            print("Warning: _fetch_model_from_asrs raised an exception:", traceback.format_exc())

        # After fetch (or regardless), open inventory and highlight
        self._open_inventory_list_with_product(product_code)

    def _open_inventory_list_with_product(self, product_code: str = None):
        """
        Open InventoryListWindow and highlight or filter to the given product_code.
        Uses multiple fallback methods to call into InventoryListWindow safely.
        """

        code = (product_code or "").strip()
        if not code:
            code = (self.product_code_edit.text() or "").strip()

        if not code:
            # If ASRS available, allow picking a model number then use it
            if _game3_loaded:
                self._choose_model_no()
                code = (self.product_code_edit.text() or "").strip()
            if not code:
                # Ask the user
                code, ok = QInputDialog.getText(self, "Product Code", "Enter product code to open in Inventory:")
                if not ok or not code:
                    return
                code = code.strip()

        # ✅ --- Launch ASRS window (separate process) ---
        try:
            import subprocess, sys, os
            game3_path = os.path.join(os.path.dirname(__file__), "game_3.py")

            # If user entered a product code, send it to ASRS
            if code:
                subprocess.Popen([sys.executable, game3_path, code])
                print(f"✅ ASRS launched with product code {code}")
            else:
                subprocess.Popen([sys.executable, game3_path])
                print("✅ ASRS window launched (no product code).")
        except Exception as e:
            print("❌ Error launching ASRS:", e)

        # ✅ --- Continue showing Inventory List as before ---
        if self._show_import_problem("inventory_list"):
            return
        if InventoryListWindow is None:
            QMessageBox.warning(self, "Inventory Unavailable", "InventoryList module/class not available.")
            return

        try:
            inv = InventoryListWindow(self)
            self._tray_windows["inventory"] = inv
            inv.show()

            # Try standard helper names if implemented in inventory_list.py
            if hasattr(inv, "filter_table_by_product_code"):
                try:
                    inv.filter_table_by_product_code(code)
                    return
                except Exception:
                    print("filter_table_by_product_code failed:", traceback.format_exc())

            if hasattr(inv, "select_row_for_product"):
                try:
                    inv.select_row_for_product(code)
                    return
                except Exception:
                    print("select_row_for_product failed:", traceback.format_exc())

            if hasattr(inv, "set_search_field"):
                try:
                    inv.set_search_field(code)
                    if hasattr(inv, "apply_search"):
                        inv.apply_search()
                    return
                except Exception:
                    print("set_search_field/apply_search failed:", traceback.format_exc())

            if hasattr(inv, "apply_filter"):
                try:
                    inv.apply_filter({"product_code": code})
                    return
                except Exception:
                    print("apply_filter failed:", traceback.format_exc())

            try:
                if hasattr(inv, "product_code_edit"):
                    inv.product_code_edit.setText(code)
                if hasattr(inv, "search_input"):
                    inv.search_input.setText(code)
            except Exception:
                pass

            if hasattr(inv, "table") and isinstance(inv.table, QTableWidget):
                self._highlight_product_row(inv.table, code)
                return

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Inventory window:\n{e}")
            print(traceback.format_exc())


    def _highlight_product_row(self, table: QTableWidget, product_code: str):
        """
        Generic fallback highlight: finds first row where the 'Product Code' column contains product_code (case-insensitive)
        and selects & scrolls to it.
        """
        pc_col_idx = None
        try:
            headers = []
            for i in range(table.columnCount()):
                hi = table.horizontalHeaderItem(i)
                if hi:
                    headers.append(hi.text())
                else:
                    headers.append("")
            for i, h in enumerate(headers):
                if "product" in h.lower() and "code" in h.lower():
                    pc_col_idx = i
                    break
        except Exception:
            pass

        if pc_col_idx is None:
            # fallback index guess (your screenshot suggests product code is around column 4)
            pc_col_idx = 4

        matched = None
        for r in range(table.rowCount()):
            try:
                item = table.item(r, pc_col_idx)
                if item and product_code.lower() in item.text().lower():
                    matched = r
                    break
            except Exception:
                continue

        if matched is not None:
            table.selectRow(matched)
            try:
                table.scrollToItem(table.item(matched, pc_col_idx), hint=QTableWidget.PositionAtCenter)
            except Exception:
                pass

    # =================== helper used by tiles to safely open modules ===================
    def _safe_open(self, key, friendly, cls_ref):
        """
        key: error key in _submodule_errors (string)
        friendly: friendly dialog title
        cls_ref: class reference (e.g. TrayDataWindow)
        """
        if self._show_import_problem(key):
            return
        if cls_ref is None:
            QMessageBox.warning(self, "Not available", f"{friendly} module/class not available.")
            return
        try:
            name = key
            self._tray_windows[name] = cls_ref(self)
            self._tray_windows[name].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open {friendly}:\n{e}")
            print(traceback.format_exc())

    # ---------- subwindow openers ----------
    def _show_import_problem(self, key):
        if key in _submodule_errors:
            detail = _submodule_errors[key]
            QMessageBox.critical(self, "Module error", f"Failed to load module: {key}\n\nSee console for details.")
            print(f"--- ERROR: {key} ---\n{detail}")
            return True
        return False

    def show_submodule_errors(self):
        if not _submodule_errors:
            QMessageBox.information(self, "OK", "No submodule errors detected.")
            return
        keys = "\n".join(_submodule_errors.keys())
        QMessageBox.warning(self, "Submodule load errors", f"The following failed:\n{keys}\n\nCheck console for stack traces.")
        for k, v in _submodule_errors.items():
            print(f"--- {k} ---\n{v}\n")

    def open_tray_config_window(self):
        if self._show_import_problem("tray_config_window") or TrayConfigWindow is None:
            return
        try:
            self._tray_windows["tray_config"] = TrayConfigWindow(self)
            self._tray_windows["tray_config"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open TrayConfigWindow:\n{e}")
            print(traceback.format_exc())

    def open_call_tray_window(self):
        if self._show_import_problem("call_tray_details") or CallTrayDetailsWindow is None:
            return
        try:
            self._tray_windows["call_tray"] = CallTrayDetailsWindow(self)
            self._tray_windows["call_tray"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open CallTrayDetailsWindow:\n{e}")
            print(traceback.format_exc())

    def open_inventory_list_window(self):
        if self._show_import_problem("inventory_list") or InventoryListWindow is None:
            return
        try:
            self._tray_windows["inventory"] = InventoryListWindow(self)
            self._tray_windows["inventory"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open InventoryListWindow:\n{e}")
            print(traceback.format_exc())

    def open_tray_data_window(self):
        if self._show_import_problem("tray_data") or TrayDataWindow is None:
            return
        try:
            self._tray_windows["tray_data"] = TrayDataWindow(self)
            self._tray_windows["tray_data"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open TrayDataWindow:\n{e}")
            print(traceback.format_exc())

    def open_tray_partition_window(self):
        if self._show_import_problem("tray_partition") or TrayPartitionWindow is None:
            return
        try:
            self._tray_windows["tray_partition"] = TrayPartitionWindow(self)
            self._tray_windows["tray_partition"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open TrayPartitionWindow:\n{e}")
            print(traceback.format_exc())

    def open_settings_window(self):
        if self._show_import_problem("settings_window") or SettingsWindow is None:
            return
        try:
            def _on_settings_saved(cfg):
                self.default_rows = cfg.get("default_rows", getattr(self, "default_rows", 4))
                self.default_cols = cfg.get("default_cols", getattr(self, "default_cols", 8))
                QMessageBox.information(self, "Settings Applied", f"Settings saved.\nRows: {self.default_rows}  Cols: {self.default_cols}")

            self._tray_windows["settings"] = SettingsWindow(self, settings_file="settings.json", on_settings_saved=_on_settings_saved)
            self._tray_windows["settings"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open SettingsWindow:\n{e}")
            print(traceback.format_exc())

    def open_machine_status_window(self):
        if self._show_import_problem("machine_status") or MachineStatusWindow is None:
            return
        try:
            self._tray_windows["machine_status"] = MachineStatusWindow(self)
            self._tray_windows["machine_status"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open MachineStatusWindow:\n{e}")
            print(traceback.format_exc())

    def open_available_space_window(self):
        if self._show_import_problem("available_space") or AvailableSpaceWindow is None:
            return
        try:
            self._tray_windows["available_space"] = AvailableSpaceWindow(self)
            self._tray_windows["available_space"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open AvailableSpaceWindow:\n{e}")
            print(traceback.format_exc())

    def open_material_tracking_window(self):
        if self._show_import_problem("material_tracking") or "MaterialTrackingWindow" not in globals():
            return
        try:
            self._tray_windows["material_tracking"] = MaterialTrackingWindow(self)
            self._tray_windows["material_tracking"].show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open MaterialTrackingWindow:\n{e}")
            print(traceback.format_exc())


if __name__ == "__main__":
    print("Running open_gui_merged2.py")
    print("Current folder:", os.path.abspath(os.path.dirname(__file__)))
    print("Python:", sys.version.splitlines()[0])

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    if _submodule_errors:
        print("\n--- Submodule import issues detected ---")
        for k, v in _submodule_errors.items():
            print(f"- {k}")

    sys.exit(app.exec())

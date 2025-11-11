# ============================================================================
# ASRS SYSTEM - PHASE 1 (Box Models + Dashboard + Database)
# With Model-Filtered LIFO/FIFO/BY ID Retrieval + FIXED RESET
# ============================================================================

import sys
import json
import os
import heapq
import math
import sqlite3
import logging
import traceback
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QTableWidget, QTableWidgetItem,
                               QPushButton, QLineEdit, QLabel, QMessageBox,
                               QComboBox, QGroupBox, QSizePolicy, QSpinBox, QDialog,
                               QScrollArea)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QScreen

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('asrs_debug.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)
logger.info("="*80)
logger.info("ASRS System Starting - Logging Enabled")
logger.info("="*80)

# ============================================================================
# SECTION 1: DATABASE FUNCTIONS
# (unchanged from your original file)
# ============================================================================

DATABASE = "asrs_system.db"

def init_database():
    """Initialize SQLite database with tables"""
    try:
        logger.info("Initializing database...")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        logger.debug("Creating box_models table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT UNIQUE NOT NULL,
                length INTEGER NOT NULL,
                width INTEGER NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        logger.debug("Creating boxes table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS boxes (
                box_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                placement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retrieval_date TIMESTAMP,
                status TEXT DEFAULT 'stored',
                FOREIGN KEY (model_id) REFERENCES box_models(id)
            )
        ''')

        logger.debug("Creating operations_log table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_id INTEGER,
                operation TEXT,
                operation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                distance_traveled REAL,
                FOREIGN KEY (box_id) REFERENCES boxes(box_id)
            )
        ''')

        logger.debug("Creating maintenance_info table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycles_today INTEGER DEFAULT 0,
                cycles_total INTEGER DEFAULT 0,
                cycles_till_check INTEGER DEFAULT 1000,
                last_check_date TIMESTAMP,
                next_check_date TIMESTAMP
            )
        ''')

        cursor.execute('''
            INSERT OR IGNORE INTO maintenance_info (id, cycles_till_check)
            VALUES (1, 1000)
        ''')

        # -------------------------------------------------------------
        # Default models (100 entries, named as plain numbers 1, 2, 3, ...)
        # -------------------------------------------------------------
        default_models = []
        for i in range(1, 101):
            # Assign varying dimensions to keep racks interesting
            # Pattern repeats every 5 models: (1x1), (2x2), (3x3), (4x4), (5x5)
            size = (i % 5) + 1
            default_models.append((str(i), size, size))


        logger.debug("Inserting default models...")
        for model_name, length, width in default_models:
            try:
                cursor.execute('''
                    INSERT INTO box_models (model_name, length, width)
                    VALUES (?, ?, ?)
                ''', (model_name, length, width))
                logger.debug(f"Added model: {model_name}")
            except sqlite3.IntegrityError:
                logger.debug(f"Model already exists: {model_name}")
                pass

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.error(traceback.format_exc())
        raise

def add_custom_model(model_name, length, width):
    """Add a custom box model"""
    try:
        logger.info(f"Adding custom model: {model_name} ({length}x{width})")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO box_models (model_name, length, width)
                VALUES (?, ?, ?)
            ''', (model_name, length, width))
            conn.commit()
            logger.info(f"Successfully added model: {model_name}")
            return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Model already exists: {model_name} - {e}")
            return False
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error adding custom model: {e}")
        logger.error(traceback.format_exc())
        return False

def get_all_models():
    """Get all available box models"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, model_name FROM box_models ORDER BY length, width')
    models = cursor.fetchall()
    conn.close()
    return models

def get_model_dimensions(model_id):
    """Get length and width of a model"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT length, width FROM box_models WHERE id = ?', (model_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def log_operation(box_id, operation, distance=0):
    """Log an operation to database"""
    try:
        logger.debug(f"Logging operation - Box: {box_id}, Operation: {operation}, Distance: {distance}")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO operations_log (box_id, operation, distance_traveled)
                VALUES (?, ?, ?)
            ''', (box_id, operation, distance))
            conn.commit()
            logger.debug(f"Operation logged successfully")
        except Exception as e:
            logger.error(f"Error logging operation: {e}")
            logger.error(traceback.format_exc())
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Critical error in log_operation: {e}")
        logger.error(traceback.format_exc())

def update_maintenance_cycles(distance_traveled):
    """Update maintenance cycles"""
    try:
        cycles = max(1, int(distance_traveled / 10))
        logger.debug(f"Updating maintenance cycles - Distance: {distance_traveled}, Cycles: {cycles}")

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE maintenance_info
                SET cycles_today = cycles_today + ?,
                    cycles_total = cycles_total + ?,
                    cycles_till_check = cycles_till_check - ?
                WHERE id = 1
            ''', (cycles, cycles, cycles))
            conn.commit()
            logger.debug(f"Maintenance cycles updated successfully")
        except Exception as e:
            logger.error(f"Error updating cycles: {e}")
            logger.error(traceback.format_exc())
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Critical error in update_maintenance_cycles: {e}")
        logger.error(traceback.format_exc())

def get_maintenance_info():
    """Get current maintenance information"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT cycles_today, cycles_total, cycles_till_check FROM maintenance_info WHERE id = 1')
    result = cursor.fetchone()
    conn.close()
    return result if result else (0, 0, 1000)

def add_box_to_db(model_id):
    """Add box to database"""
    try:
        logger.info(f"Adding box to database - Model ID: {model_id}")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO boxes (model_id, status)
                VALUES (?, 'stored')
            ''', (model_id,))
            conn.commit()
            box_id = cursor.lastrowid
            logger.info(f"Box added successfully - Box ID: {box_id}")
            return box_id
        except Exception as e:
            logger.error(f"Error adding box to database: {e}")
            logger.error(traceback.format_exc())
            return None
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Critical error in add_box_to_db: {e}")
        logger.error(traceback.format_exc())
        return None

def clear_all_database():
    """Clear all database tables completely"""
    try:
        logger.info("Clearing all database tables...")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM boxes')
            logger.debug("Deleted all boxes")
            cursor.execute('DELETE FROM operations_log')
            logger.debug("Deleted all operation logs")
            cursor.execute('''
                UPDATE maintenance_info
                SET cycles_today = 0,
                    cycles_total = 0,
                    cycles_till_check = 1000
                WHERE id = 1
            ''')
            logger.debug("Reset maintenance info")
            conn.commit()
            logger.info("Database cleared successfully")
        except Exception as e:
            logger.error(f"Database clear error: {e}")
            logger.error(traceback.format_exc())
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Critical error in clear_all_database: {e}")
        logger.error(traceback.format_exc())

# ============================================================================
# SECTION 2: CONFIGURATION CONSTANTS
# ============================================================================

SAVE_FILE = "asrs_state.json"
GRID_ROWS = 20
GRID_COLS = 20
ORIGIN_ROW = GRID_ROWS - 1
ORIGIN_COL = 0

# Colors
EMPTY_COLOR = QColor(240, 240, 240)
OCCUPIED_COLOR = QColor(34, 139, 34)
TROLLEY_COLOR = QColor(220, 20, 60)
PLACING_COLOR = QColor(255, 215, 0)
PATH_COLOR = QColor(173, 216, 230)
RETRIEVING_COLOR = QColor(255, 165, 0)

# ============================================================================
# SECTION 3: DATA STRUCTURES
# ============================================================================

class Box:
    """Represents a box to be stored"""
    def __init__(self, length, width, box_id=None, model_id=None):
        self.length = length
        self.width = width
        self.box_id = box_id
        self.model_id = model_id
    
    def to_dict(self):
        return {'length': self.length, 'width': self.width, 'box_id': self.box_id, 'model_id': self.model_id}
    
    @staticmethod
    def from_dict(data):
        return Box(data['length'], data['width'], data['box_id'], data.get('model_id'))

class Rack:
    """Represents the ASRS rack system"""
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]
        self.boxes = {}
        self.box_positions = {}
        self.next_box_id = 1
        self.box_order = []
    
    def can_place_box(self, box, start_row, start_col):
        end_row = start_row + box.width
        end_col = start_col + box.length
        
        if end_row > self.rows or end_col > self.cols:
            return False
        
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                if self.grid[r][c] is not None:
                    return False
        
        return True
    
    def place_box(self, box, start_row, start_col):
        if not self.can_place_box(box, start_row, start_col):
            return False
        
        box.box_id = self.next_box_id
        self.next_box_id += 1
        
        end_row = start_row + box.width
        end_col = start_col + box.length
        
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                self.grid[r][c] = box.box_id
        
        self.boxes[box.box_id] = box
        self.box_positions[box.box_id] = (start_row, start_col)
        self.box_order.append(box.box_id)
        
        return True
    
    def remove_box(self, box_id):
        if box_id not in self.boxes:
            return False
        
        start_row, start_col = self.box_positions[box_id]
        box = self.boxes[box_id]
        
        end_row = start_row + box.width
        end_col = start_col + box.length
        
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                self.grid[r][c] = None
        
        del self.boxes[box_id]
        del self.box_positions[box_id]
        self.box_order.remove(box_id)
        
        return True
    
    def get_lifo_box(self):
        if not self.box_order:
            return None
        return self.box_order[-1]
    
    def get_fifo_box(self):
        if not self.box_order:
            return None
        return self.box_order[0]
    
    def get_lifo_box_by_model(self, model_id):
        """Get LIFO box from specific model"""
        for box_id in reversed(self.box_order):
            if self.boxes[box_id].model_id == model_id:
                return box_id
        return None
    
    def get_fifo_box_by_model(self, model_id):
        """Get FIFO box from specific model"""
        for box_id in self.box_order:
            if self.boxes[box_id].model_id == model_id:
                return box_id
        return None
    
    def get_boxes_by_model(self, model_id):
        """Get all boxes of a specific model"""
        return [box_id for box_id in self.box_order if self.boxes[box_id].model_id == model_id]
    
    def find_closest_available_location(self, box, origin_row, origin_col):
        closest_location = None
        min_distance = float('inf')
        
        for row in range(self.rows - box.width + 1):
            for col in range(self.cols - box.length + 1):
                if self.can_place_box(box, row, col):
                    distance = math.sqrt((row - origin_row)**2 + (col - origin_col)**2)
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_location = (row, col)
        
        return closest_location
    
    def get_occupied_cells(self):
        return sum(1 for row in self.grid for cell in row if cell is not None)
    
    def to_dict(self):
        return {
            'rows': self.rows,
            'cols': self.cols,
            'grid': self.grid,
            'boxes': {box_id: box.to_dict() for box_id, box in self.boxes.items()},
            'box_positions': self.box_positions,
            'next_box_id': self.next_box_id,
            'box_order': self.box_order
        }
    
    @staticmethod
    def from_dict(data):
        rack = Rack(data['rows'], data['cols'])
        rack.grid = data['grid']
        rack.boxes = {int(box_id): Box.from_dict(box_data) 
                     for box_id, box_data in data['boxes'].items()}
        rack.box_positions = {int(k): tuple(v) for k, v in data['box_positions'].items()}
        rack.next_box_id = data['next_box_id']
        rack.box_order = data.get('box_order', [])
        return rack

# ============================================================================
# SECTION 4: PATHFINDING & SAVE/LOAD
# ============================================================================

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_pathfinding(grid, start, goal):
    rows = len(grid)
    cols = len(grid[0])
    
    open_list = []
    heapq.heappush(open_list, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    
    while open_list:
        current = heapq.heappop(open_list)[1]
        
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            # return everything except the starting cell
            return path[1:]
        
        neighbors = [
            (current[0]-1, current[1]),
            (current[0]+1, current[1]),
            (current[0], current[1]-1),
            (current[0], current[1]+1)
        ]
        
        for neighbor in neighbors:
            row, col = neighbor
            
            if not (0 <= row < rows and 0 <= col < cols):
                continue
            
            tentative_g = g_score[current] + 1
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_list, (f_score[neighbor], neighbor))
    
    return []

def save_game_state(rack):
    try:
        logger.debug("Saving game state...")
        with open(SAVE_FILE, 'w') as f:
            json.dump(rack.to_dict(), f, indent=2)
        logger.info("Game state saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving game state: {e}")
        logger.error(traceback.format_exc())
        return False

def load_game_state():
    try:
        if not os.path.exists(SAVE_FILE):
            logger.info("No save file found, starting fresh")
            return None

        logger.info("Loading game state from file...")
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
        rack = Rack.from_dict(data)
        logger.info(f"Game state loaded - {len(rack.boxes)} boxes in rack")
        return rack
    except Exception as e:
        logger.error(f"Error loading game state: {e}")
        logger.error(traceback.format_exc())
        return None

# ============================================================================
# SECTION 5: MAIN WINDOW CLASS (ASRSWindow)
# ============================================================================

class ASRSWindow(QMainWindow):
    def __init__(self):
        try:
            logger.info("Initializing ASRS Window...")
            super().__init__()
            self.setWindowTitle("ASRS - Automated Storage & Retrieval System")

            # Get screen size and calculate responsive dimensions
            screen = QApplication.primaryScreen().geometry()
            self.screen_width = screen.width()
            self.screen_height = screen.height()
            logger.info(f"Screen resolution: {self.screen_width}x{self.screen_height}")

            # Calculate cell size based on screen size (20-35 pixels)
            available_width = int(self.screen_width * 0.85)
            available_height = int(self.screen_height * 0.75)

            # Calculate cell size that fits the grid nicely
            cell_width = min(35, max(20, (available_width - 100) // GRID_COLS))
            cell_height = min(35, max(20, (available_height - 400) // GRID_ROWS))
            self.cell_size = min(cell_width, cell_height)

            logger.info(f"Calculated cell size: {self.cell_size}px")

            # Set responsive window size
            window_width = min(self.screen_width - 100, 1400)
            window_height = min(self.screen_height - 100, 1000)
            self.setGeometry(50, 50, window_width, window_height)

            # Maximize on large screens (TVs, large monitors)
            self.should_maximize = False
            if self.screen_width >= 1920 and self.screen_height >= 1080:
                logger.info("Large screen detected - will maximize window")
                self.should_maximize = True

            init_database()

            self.rack = load_game_state()
            if self.rack is None:
                logger.info("Creating new rack")
                self.rack = Rack(GRID_ROWS, GRID_COLS)

            self.trolley_row = ORIGIN_ROW
            self.trolley_col = ORIGIN_COL
            self.trolley_path = []
            self.is_animating = False
            self.operation_mode = 'idle'
            self.animation_cell_index = 0
            self.animation_cells = []
            self.pending_box = None
            self.pending_position = None
            self.path_visualization = []
            self.retrieving_box_id = None
            self.distance_traveled = 0
            self.pending_model_id = None

            logger.debug("Setting up UI...")
            self.setup_ui()
            self.update_grid_display()
            self.update_stats()
            self.update_dashboard()

            self.animation_timer = QTimer()
            self.animation_timer.timeout.connect(self.animate)

            logger.info("ASRS Window initialized successfully")
        except Exception as e:
            logger.error(f"Critical error initializing ASRS Window: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 8, 10, 8)

        # Calculate responsive font sizes based on screen resolution
        base_font_size = max(10, min(16, int(self.screen_width / 100)))
        title_font_size = base_font_size + 4
        label_font_size = base_font_size
        dashboard_font_size = min(28, max(18, int(self.screen_width / 60)))

        # Title
        title = QLabel("ASRS - Automated Storage & Retrieval System")
        title.setStyleSheet(f"font-size: {title_font_size}px; font-weight: bold; padding: 5px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # ===== STORAGE SECTION =====
        storage_group = QGroupBox("📦 Storage Operations")
        storage_layout = QVBoxLayout()
        
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Select Model:"))
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo)
        
        self.custom_model_btn = QPushButton("➕ Custom Model")
        self.custom_model_btn.clicked.connect(self.add_custom_model_dialog)
        model_layout.addWidget(self.custom_model_btn)
        
        model_layout.addStretch()
        storage_layout.addLayout(model_layout)
        
        add_btn_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Box")
        self.add_button.setMinimumWidth(150)
        self.add_button.clicked.connect(self.add_box_by_model)
        add_btn_layout.addWidget(self.add_button)
        add_btn_layout.addStretch()
        storage_layout.addLayout(add_btn_layout)
        
        storage_group.setLayout(storage_layout)
        main_layout.addWidget(storage_group)
        
        # ===== RETRIEVAL SECTION =====
        retrieval_group = QGroupBox("🔄 Retrieval Operations")
        retrieval_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.retrieval_mode = QComboBox()
        self.retrieval_mode.addItems(['LIFO', 'FIFO', 'BY ID'])
        self.retrieval_mode.setMaximumWidth(100)
        self.retrieval_mode.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.retrieval_mode)
        
        mode_layout.addWidget(QLabel("Model:"))
        self.filter_model_combo = QComboBox()
        self.filter_model_combo.addItem("All Models", None)
        self.filter_model_combo.setMaximumWidth(120)
        mode_layout.addWidget(self.filter_model_combo)
        
        mode_layout.addWidget(QLabel("Box ID:"))
        self.retrieve_id_input = QLineEdit()
        self.retrieve_id_input.setPlaceholderText("ID")
        self.retrieve_id_input.setMaximumWidth(50)
        self.retrieve_id_input.setEnabled(False)
        mode_layout.addWidget(self.retrieve_id_input)
        
        mode_layout.addStretch()
        retrieval_layout.addLayout(mode_layout)
        
        retrieve_btn_layout = QHBoxLayout()
        self.retrieve_button = QPushButton("Retrieve Box")
        self.retrieve_button.setMinimumWidth(150)
        self.retrieve_button.clicked.connect(self.retrieve_box)
        retrieve_btn_layout.addWidget(self.retrieve_button)
        retrieve_btn_layout.addStretch()
        retrieval_layout.addLayout(retrieve_btn_layout)
        
        retrieval_group.setLayout(retrieval_layout)
        main_layout.addWidget(retrieval_group)
        
        self.load_models_to_combo(self.model_combo)
        self.load_models_to_combo(self.filter_model_combo)
        
        # ===== DASHBOARD SECTION =====
        dashboard_group = QGroupBox("📊 Maintenance Dashboard")
        dashboard_layout = QHBoxLayout()
        
        self.cycles_today_label = QLabel("0")
        self.cycles_today_label.setAlignment(Qt.AlignCenter)
        self.cycles_today_label.setStyleSheet(f"font-size: {dashboard_font_size}px; font-weight: bold; padding: 10px; background-color: #e3f2fd; border-radius: 5px;")
        today_box = QVBoxLayout()
        today_label = QLabel("Cycles Today")
        today_label.setStyleSheet(f"font-size: {label_font_size}px;")
        today_label.setAlignment(Qt.AlignCenter)
        today_box.addWidget(today_label)
        today_box.addWidget(self.cycles_today_label)
        today_widget = QWidget()
        today_widget.setLayout(today_box)
        dashboard_layout.addWidget(today_widget)

        self.cycles_total_label = QLabel("0")
        self.cycles_total_label.setAlignment(Qt.AlignCenter)
        self.cycles_total_label.setStyleSheet(f"font-size: {dashboard_font_size}px; font-weight: bold; padding: 10px; background-color: #f3e5f5; border-radius: 5px;")
        total_box = QVBoxLayout()
        total_label = QLabel("Cycles Total")
        total_label.setStyleSheet(f"font-size: {label_font_size}px;")
        total_label.setAlignment(Qt.AlignCenter)
        total_box.addWidget(total_label)
        total_box.addWidget(self.cycles_total_label)
        total_widget = QWidget()
        total_widget.setLayout(total_box)
        dashboard_layout.addWidget(total_widget)

        self.cycles_check_label = QLabel("1000")
        self.cycles_check_label.setAlignment(Qt.AlignCenter)
        self.cycles_check_label.setStyleSheet(f"font-size: {dashboard_font_size}px; font-weight: bold; padding: 10px; background-color: #fff3e0; border-radius: 5px;")
        check_box = QVBoxLayout()
        check_label = QLabel("Cycles Till Check")
        check_label.setStyleSheet(f"font-size: {label_font_size}px;")
        check_label.setAlignment(Qt.AlignCenter)
        check_box.addWidget(check_label)
        check_box.addWidget(self.cycles_check_label)
        check_widget = QWidget()
        check_widget.setLayout(check_box)
        dashboard_layout.addWidget(check_widget)

        self.avg_cycles_label = QLabel("0")
        self.avg_cycles_label.setAlignment(Qt.AlignCenter)
        self.avg_cycles_label.setStyleSheet(f"font-size: {dashboard_font_size}px; font-weight: bold; padding: 10px; background-color: #e8f5e9; border-radius: 5px;")
        avg_box = QVBoxLayout()
        avg_label = QLabel("Avg Cycles/Day")
        avg_label.setStyleSheet(f"font-size: {label_font_size}px;")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_box.addWidget(avg_label)
        avg_box.addWidget(self.avg_cycles_label)
        avg_widget = QWidget()
        avg_widget.setLayout(avg_box)
        dashboard_layout.addWidget(avg_widget)
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumWidth(50)
        refresh_btn.clicked.connect(self.update_dashboard)
        dashboard_layout.addWidget(refresh_btn)
        
        dashboard_group.setLayout(dashboard_layout)
        main_layout.addWidget(dashboard_group)
        
        # ===== GRID SECTION =====
        self.table = QTableWidget(GRID_ROWS, GRID_COLS)

        # Set responsive cell sizes
        for i in range(GRID_ROWS):
            self.table.setRowHeight(i, self.cell_size)
        for i in range(GRID_COLS):
            self.table.setColumnWidth(i, self.cell_size)

        # Calculate table size based on cell size
        table_width = GRID_COLS * self.cell_size + 50
        table_height = GRID_ROWS * self.cell_size + 50
        self.table.setMinimumSize(table_width, table_height)
        self.table.setMaximumSize(table_width, table_height)

        # Make table size policy expanding but respect min/max
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.table.horizontalHeader().setVisible(True)
        self.table.verticalHeader().setVisible(True)
        
        for col in range(GRID_COLS):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(str(col)))
        for row in range(GRID_ROWS):
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(str(row)))

        # Responsive header font size based on cell size
        header_font_size = max(8, min(12, self.cell_size // 2))

        self.table.horizontalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: #4CAF50;
                color: white;
                padding: 2px;
                border: 1px solid #388E3C;
                font-weight: bold;
                font-size: {header_font_size}px;
            }}
        """)

        self.table.verticalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: #2196F3;
                color: white;
                padding: 2px;
                border: 1px solid #1976D2;
                font-weight: bold;
                font-size: {header_font_size}px;
            }}
        """)
        
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Wrap table in scroll area for smaller screens
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.table)
        scroll_area.setWidgetResizable(False)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setAlignment(Qt.AlignCenter)

        # Set scroll area size policy
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        table_container = QHBoxLayout()
        table_container.addWidget(scroll_area)
        main_layout.addLayout(table_container)
        
        # ===== STATUS & STATS =====
        self.status_label = QLabel("🚛 Trolley Ready")
        self.status_label.setStyleSheet(f"padding: 4px; background-color: #f0f0f0; font-size: {label_font_size}px; font-weight: bold;")
        main_layout.addWidget(self.status_label)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"padding: 5px; font-size: {label_font_size}px; background-color: #e3f2fd;")
        main_layout.addWidget(self.stats_label)
        
        # ===== SYSTEM BUTTONS =====
        system_layout = QHBoxLayout()
        
        self.save_button = QPushButton("💾 Save")
        self.save_button.clicked.connect(self.save_state)
        system_layout.addWidget(self.save_button)
        
        self.export_button = QPushButton("📥 Export Report")
        self.export_button.clicked.connect(self.export_report)
        system_layout.addWidget(self.export_button)
        
        self.reset_button = QPushButton("🔄 Reset")
        self.reset_button.clicked.connect(self.reset_rack)
        system_layout.addWidget(self.reset_button)
        
        system_layout.addStretch()
        main_layout.addLayout(system_layout)
    
    def on_mode_changed(self):
        """Handle mode change"""
        mode = self.retrieval_mode.currentText()
        self.retrieve_id_input.setEnabled(mode == "BY ID")
        if mode != "BY ID":
            self.retrieve_id_input.clear()
    
    def load_models_to_combo(self, combo):
        """Load models to dropdown"""
        combo.clear()
        models = get_all_models()
        
        if combo == self.filter_model_combo:
            combo.addItem("All Models", None)
        
        for model_id, model_name in models:
            combo.addItem(model_name, model_id)
    
    def add_custom_model_dialog(self):
        """Add custom model dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Model")
        dialog.setGeometry(200, 200, 300, 200)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Model Name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., Custom-6x3")
        layout.addWidget(name_input)
        
        layout.addWidget(QLabel("Length:"))
        length_input = QSpinBox()
        length_input.setMinimum(1)
        length_input.setMaximum(20)
        layout.addWidget(length_input)
        
        layout.addWidget(QLabel("Width:"))
        width_input = QSpinBox()
        width_input.setMinimum(1)
        width_input.setMaximum(20)
        layout.addWidget(width_input)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Add")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        def on_ok():
            model_name = name_input.text().strip()
            if not model_name:
                QMessageBox.warning(dialog, "Error", "Enter model name")
                return
            
            if add_custom_model(model_name, length_input.value(), width_input.value()):
                self.load_models_to_combo(self.model_combo)
                self.load_models_to_combo(self.filter_model_combo)
                QMessageBox.information(dialog, "Success", f"Model {model_name} added!")
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", "Model already exists!")
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def add_box_by_model(self):
        """Add box"""
        try:
            logger.info("=== ADD BOX OPERATION STARTED ===")

            if self.is_animating:
                logger.warning("Operation rejected: Animation already in progress")
                return

            model_index = self.model_combo.currentIndex()
            if model_index < 0:
                logger.warning("No model selected")
                QMessageBox.warning(self, "Error", "Select a model")
                return

            model_id = self.model_combo.currentData()
            logger.info(f"Selected model ID: {model_id}")

            dimensions = get_model_dimensions(model_id)

            if not dimensions:
                logger.error(f"Invalid model ID: {model_id}")
                QMessageBox.warning(self, "Error", "Invalid model")
                return

            length, width = dimensions
            logger.info(f"Box dimensions: {length}x{width}")

            box = Box(length, width, model_id=model_id)
            logger.debug(f"Finding closest location from origin ({ORIGIN_ROW}, {ORIGIN_COL})")

            target = self.rack.find_closest_available_location(box, ORIGIN_ROW, ORIGIN_COL)

            if target is None:
                logger.warning(f"No space available for {length}x{width} box")
                QMessageBox.warning(self, "No Space", f"No space for {length}x{width} box!")
                return

            logger.info(f"Target location found: {target}")
            logger.debug(f"Calculating path from ({self.trolley_row}, {self.trolley_col}) to {target}")

            path = a_star_pathfinding(self.rack.grid, (self.trolley_row, self.trolley_col), target)
            distance = len(path)

            logger.info(f"Path calculated - Distance: {distance} steps")

            self.pending_model_id = model_id
            self.start_storage_animation(box, target, path, distance)

        except Exception as e:
            logger.error(f"Error in add_box_by_model: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Failed to add box:\n{str(e)}")
    
    def update_dashboard(self):
        """Update dashboard"""
        cycles_today, cycles_total, cycles_till_check = get_maintenance_info()
        
        self.cycles_today_label.setText(str(cycles_today))
        self.cycles_total_label.setText(str(cycles_total))
        self.cycles_check_label.setText(str(max(0, cycles_till_check)))
        
        if cycles_total > 0:
            avg = cycles_total // max(1, 1)
            self.avg_cycles_label.setText(str(avg))
    
    def export_report(self):
        """Export report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"asrs_report_{timestamp}.csv"
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            report = "Box ID,Model,Placement Date,Status\n"
            
            cursor.execute('''
                SELECT b.box_id, m.model_name, b.placement_date, b.status
                FROM boxes b
                LEFT JOIN box_models m ON b.model_id = m.id
                ORDER BY b.box_id
            ''')
            
            rows = cursor.fetchall()
            
            if not rows:
                QMessageBox.information(self, "Info", "No boxes in database yet!")
                return
            
            for row in rows:
                report += f"{row[0]},{row[1] if row[1] else 'Unknown'},{row[2]},{row[3]}\n"
            
            with open(filename, 'w') as f:
                f.write(report)
            
            QMessageBox.information(self, "Exported", f"Report saved as:\n{filename}")
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error:\n{str(e)}")
    
    def start_storage_animation(self, box, position, path, distance):
        """Start storage animation"""
        try:
            logger.info(f"Starting storage animation - Position: {position}, Distance: {distance}")
            self.is_animating = True
            self.operation_mode = 'storing_moving'
            self.pending_box = box
            self.pending_position = position
            self.trolley_path = path
            self.path_visualization = set(path)
            self.animation_cell_index = 0
            self.distance_traveled = distance

            self.status_label.setText(f"📦 STORAGE: Moving to ({position[0]},{position[1]}) | Distance: {distance}")
            self.add_button.setEnabled(False)
            self.retrieve_button.setEnabled(False)
            self.update_grid_display()
            self.animation_timer.start(150)
            logger.debug("Storage animation started")
        except Exception as e:
            logger.error(f"Error starting storage animation: {e}")
            logger.error(traceback.format_exc())
    
    def update_grid_display(self):
        """Update grid - now shows pcode labels for empty cells"""
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignCenter)
                
                if self.trolley_row == row and self.trolley_col == col:
                    item.setBackground(TROLLEY_COLOR)
                    item.setText("🚛")
                    item.setForeground(Qt.white)
                elif (row, col) in self.path_visualization:
                    item.setBackground(PATH_COLOR)
                    item.setText("•")
                elif self.rack.grid[row][col] is None:
                    # Compute linear index and display number label for empty slots
                    linear_idx = row * GRID_COLS + col + 1
                    item.setBackground(EMPTY_COLOR)
                    item.setText(str(linear_idx))
                else:
                    box_id = self.rack.grid[row][col]
                    item.setBackground(OCCUPIED_COLOR)
                    item.setText(str(box_id))
                    item.setForeground(Qt.white)
                
                self.table.setItem(row, col, item)
    
    def update_stats(self):
        """Update stats"""
        total_cells = GRID_ROWS * GRID_COLS
        occupied = self.rack.get_occupied_cells()
        empty = total_cells - occupied
        num_boxes = len(self.rack.boxes)
        capacity = (occupied * 100) // total_cells if total_cells > 0 else 0
        
        stats_text = f"📦 Boxes: {num_boxes} | Occupied: {occupied} | Empty: {empty} | Capacity: {capacity}%"
        self.stats_label.setText(stats_text)
    
    def retrieve_box(self):
        """Retrieve box"""
        try:
            logger.info("=== RETRIEVE BOX OPERATION STARTED ===")

            if self.is_animating:
                logger.warning("Operation rejected: Animation already in progress")
                return

            if len(self.rack.boxes) == 0:
                logger.warning("No boxes in rack to retrieve")
                return

            mode = self.retrieval_mode.currentText()
            selected_model_id = self.filter_model_combo.currentData()
            logger.info(f"Retrieval mode: {mode}, Model filter: {selected_model_id}")

            box_id = None
            mode_name = ""

            if mode == 'LIFO':
                if selected_model_id is None:
                    box_id = self.rack.get_lifo_box()
                    mode_name = "LIFO (All Models)"
                    logger.debug(f"LIFO (All): Box ID = {box_id}")
                else:
                    box_id = self.rack.get_lifo_box_by_model(selected_model_id)
                    model_name = self.filter_model_combo.currentText()
                    mode_name = f"LIFO ({model_name})"
                    logger.debug(f"LIFO ({model_name}): Box ID = {box_id}")

            elif mode == 'FIFO':
                if selected_model_id is None:
                    box_id = self.rack.get_fifo_box()
                    mode_name = "FIFO (All Models)"
                    logger.debug(f"FIFO (All): Box ID = {box_id}")
                else:
                    box_id = self.rack.get_fifo_box_by_model(selected_model_id)
                    model_name = self.filter_model_combo.currentText()
                    mode_name = f"FIFO ({model_name})"
                    logger.debug(f"FIFO ({model_name}): Box ID = {box_id}")

            elif mode == 'BY ID':
                try:
                    box_id = int(self.retrieve_id_input.text())
                    logger.debug(f"BY ID: Box ID = {box_id}")
                except ValueError as e:
                    logger.warning(f"Invalid box ID input: {self.retrieve_id_input.text()}")
                    QMessageBox.warning(self, "Invalid ID", "Enter valid Box ID")
                    return

                if box_id not in self.rack.box_positions:
                    logger.warning(f"Box ID {box_id} not found in rack")
                    QMessageBox.warning(self, "Not Found", f"Box ID {box_id} not found!")
                    return

                mode_name = f"BY ID ({box_id})"

            if box_id is None:
                model_name = self.filter_model_combo.currentText() if selected_model_id else "All Models"
                logger.warning(f"No boxes available for {mode_name}")
                QMessageBox.warning(self, "No Box", f"No boxes in {mode_name}!")
                return

            target_row, target_col = self.rack.box_positions[box_id]
            logger.info(f"Box {box_id} location: ({target_row}, {target_col})")
            logger.debug(f"Calculating path from ({self.trolley_row}, {self.trolley_col}) to ({target_row}, {target_col})")

            path = a_star_pathfinding(self.rack.grid,
                                      (self.trolley_row, self.trolley_col),
                                      (target_row, target_col))

            logger.info(f"Path calculated - Distance: {len(path)} steps")
            self.start_retrieval_animation(box_id, (target_row, target_col), path, mode_name)

        except Exception as e:
            logger.error(f"Error in retrieve_box: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Failed to retrieve box:\n{str(e)}")
    
    def start_retrieval_animation(self, box_id, position, path, mode_name):
        """Start retrieval animation"""
        try:
            logger.info(f"Starting retrieval animation - Box ID: {box_id}, Position: {position}, Mode: {mode_name}")
            self.is_animating = True
            self.operation_mode = 'retrieving_moving'
            self.retrieving_box_id = box_id
            self.pending_position = position
            self.trolley_path = path
            self.path_visualization = set(path)
            self.animation_cell_index = 0
            self.distance_traveled = len(path)

            self.status_label.setText(f"🔄 RETRIEVAL ({mode_name}): Box #{box_id}")
            self.add_button.setEnabled(False)
            self.retrieve_button.setEnabled(False)
            self.update_grid_display()
            self.animation_timer.start(150)
            logger.debug("Retrieval animation started")
        except Exception as e:
            logger.error(f"Error starting retrieval animation: {e}")
            logger.error(traceback.format_exc())
    
    # --------- NEW: numbered rack helpers and movement ----------
    def pcode_to_cell(self, pcode_str):
        """
        Convert 'pcode-<n>' to (row, col). Supports plain numbers too.
        """
        try:
            if not isinstance(pcode_str, str):
                pcode_str = str(pcode_str)

            p = pcode_str.strip().lower()
            if not p.startswith("pcode-"):
                p = f"pcode-{p}"

            num = int(p.split("-", 1)[1])
            if num <= 0:
                return None

            idx = num - 1
            row = idx // GRID_COLS
            col = idx % GRID_COLS

            if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                return (row, col)
            return None
        except Exception as e:
            logger.error(f"Error in pcode_to_cell({pcode_str}): {e}")
            return None


    def move_trolley_to_cell(self, row, col):
        """
        Compute path to (row,col) and animate trolley movement.
        """
        try:
            if self.is_animating:
                QMessageBox.warning(self, "Busy", "ASRS is busy with another animation.")
                return False

            # 🚀 Fix 1: prevent zero-distance motion
            if (row, col) == (self.trolley_row, self.trolley_col):
                logger.warning(f"Trolley already at ({row}, {col}), nudging to nearby cell.")
                # move one step right (or left if at border)
                col = col + 1 if col + 1 < self.grid.cols else max(col - 1, 0)

            path = a_star_pathfinding(self.rack.grid, (self.trolley_row, self.trolley_col), (row, col))
            if not path:
                QMessageBox.information(self, "No Path", f"Cannot find path to ({row},{col}).")
                return False

            self.trolley_path = path
            self.path_visualization = set(path)
            self.animation_cell_index = 0
            self.distance_traveled = len(path)
            self.operation_mode = 'goto_pcode'
            self.is_animating = True
            self.status_label.setText(f"➡ Moving to {row},{col} (pcode)")
            self.add_button.setEnabled(False)
            self.retrieve_button.setEnabled(False)
            self.update_grid_display()
            self.animation_timer.start(150)
            logger.info(f"Started moving trolley to pcode cell ({row},{col}) - steps: {len(path)}")
            return True

        except Exception as e:
            logger.error(f"Error in move_trolley_to_cell: {e}")
            logger.error(traceback.format_exc())
            return False


    def find_and_move_to_product(self, code_str):
        """
        Public helper: move trolley to the numbered rack corresponding to the code.
        Accepts plain numbers like "7" instead of "pcode-7".
        """
        cell = self.pcode_to_cell(code_str)
        if cell is None:
            QMessageBox.warning(self, "Invalid code", f"Invalid rack/product number: {code_str}")
            return False
        row, col = cell
        return self.move_trolley_to_cell(row, col)

    # -------------------------------------------------------------

    def animate(self):
        """Animation loop (extended with 'goto_pcode' mode)"""
        try:
            if self.operation_mode == 'storing_moving':
                # existing storing_moving logic...
                if self.trolley_path:
                    next_row, next_col = self.trolley_path.pop(0)
                    self.trolley_row = next_row
                    self.trolley_col = next_col
                    self.update_grid_display()

                    if not self.trolley_path:
                        self.operation_mode = 'storing_placing'
                        self.animation_cell_index = 0
                        self.animation_cells = []
                        start_row, start_col = self.pending_position
                        for r in range(start_row, start_row + self.pending_box.width):
                            for c in range(start_col, start_col + self.pending_box.length):
                                self.animation_cells.append((r, c))
                        self.path_visualization.clear()
                        self.status_label.setText(f"📦 Placing...")
                        self.update_grid_display()

            elif self.operation_mode == 'storing_placing':
                if self.animation_cell_index < len(self.animation_cells):
                    row, col = self.animation_cells[self.animation_cell_index]
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(PLACING_COLOR)
                        item.setText("📦")
                    self.animation_cell_index += 1
                else:
                    self.rack.place_box(self.pending_box, self.pending_position[0], self.pending_position[1])
                    db_box_id = add_box_to_db(self.pending_model_id)
                    self.operation_mode = 'returning'
                    self.trolley_path = a_star_pathfinding(self.rack.grid,
                                                          (self.trolley_row, self.trolley_col),
                                                          (ORIGIN_ROW, ORIGIN_COL))
                    self.status_label.setText(f"🔄 Returning...")
                    self.update_grid_display()

            elif self.operation_mode == 'retrieving_moving':
                if self.trolley_path:
                    next_row, next_col = self.trolley_path.pop(0)
                    self.trolley_row = next_row
                    self.trolley_col = next_col
                    self.update_grid_display()

                    if not self.trolley_path:
                        self.operation_mode = 'retrieving_picking'
                        self.animation_cell_index = 0
                        box = self.rack.boxes[self.retrieving_box_id]
                        start_row, start_col = self.pending_position
                        self.animation_cells = []
                        for r in range(start_row, start_row + box.width):
                            for c in range(start_col, start_col + box.length):
                                self.animation_cells.append((r, c))
                        self.path_visualization.clear()
                        self.status_label.setText(f"🔄 Picking...")
                        self.update_grid_display()

            elif self.operation_mode == 'retrieving_picking':
                if self.animation_cell_index < len(self.animation_cells):
                    row, col = self.animation_cells[self.animation_cell_index]
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(RETRIEVING_COLOR)
                        item.setText("⬆️")
                    self.animation_cell_index += 1
                else:
                    self.rack.remove_box(self.retrieving_box_id)
                    self.operation_mode = 'returning'
                    self.trolley_path = a_star_pathfinding(self.rack.grid,
                                                          (self.trolley_row, self.trolley_col),
                                                          (ORIGIN_ROW, ORIGIN_COL))
                    self.status_label.setText(f"🔄 Returning...")
                    self.update_grid_display()

            elif self.operation_mode == 'returning':
                if self.trolley_path:
                    next_row, next_col = self.trolley_path.pop(0)
                    self.trolley_row = next_row
                    self.trolley_col = next_col
                    self.update_grid_display()

                    if not self.trolley_path:
                        self.animation_timer.stop()
                        self.is_animating = False

                        if hasattr(self, 'pending_box') and self.pending_box:
                            self.status_label.setText(f"✅ Box #{self.pending_box.box_id} stored!")
                            log_operation(self.pending_box.box_id, 'STORED', self.distance_traveled)
                            self.pending_box = None
                        else:
                            self.status_label.setText(f"✅ Box #{self.retrieving_box_id} retrieved!")
                            log_operation(self.retrieving_box_id, 'RETRIEVED', self.distance_traveled)
                            self.retrieving_box_id = None

                        update_maintenance_cycles(self.distance_traveled)
                        self.update_dashboard()
                        self.operation_mode = 'idle'
                        self.add_button.setEnabled(True)
                        self.retrieve_button.setEnabled(True)
                        self.update_grid_display()
                        self.update_stats()
                        save_game_state(self.rack)

            elif self.operation_mode == 'goto_pcode':
                # New mode: move the trolley along the path to the target pcode cell
                if self.trolley_path:
                    next_row, next_col = self.trolley_path.pop(0)
                    self.trolley_row = next_row
                    self.trolley_col = next_col
                    self.update_grid_display()
                    if not self.trolley_path:
                        # reached destination
                        self.animation_timer.stop()
                        self.is_animating = False
                        self.operation_mode = 'idle'
                        self.add_button.setEnabled(True)
                        self.retrieve_button.setEnabled(True)
                        self.status_label.setText(f"✅ Arrived at target ({self.trolley_row},{self.trolley_col})")
                        self.update_grid_display()
                        self.update_stats()
                        # do not modify rack state (we just moved trolley)
                # else: nothing to do if no path

        except Exception as e:
            logger.error(f"CRITICAL ERROR IN ANIMATE: {e}")
            logger.error(f"Operation mode: {self.operation_mode}")
            logger.error(f"Trolley position: ({self.trolley_row}, {self.trolley_col})")
            logger.error(f"Is animating: {self.is_animating}")
            logger.error(traceback.format_exc())
            if hasattr(self, 'animation_timer') and self.animation_timer.isActive():
                self.animation_timer.stop()
            self.is_animating = False
            self.operation_mode = 'idle'
            self.add_button.setEnabled(True)
            self.retrieve_button.setEnabled(True)
            QMessageBox.critical(self, "Animation Error", f"Critical error during animation:\n{str(e)}")
    
    def save_state(self):
        """Save state"""
        if save_game_state(self.rack):
            QMessageBox.information(self, "Saved", "State saved!")
    
    def reset_rack(self):
        """Reset rack - FIXED VERSION"""
        reply = QMessageBox.question(self, "Reset", "Reset entire rack?\n\nThis will clear:\n✓ All boxes\n✓ Dashboard data\n✓ Rack state",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Clear database
                clear_all_database()
                
                # Clear in-memory rack
                self.rack = Rack(GRID_ROWS, GRID_COLS)
                
                # Delete save file
                if os.path.exists(SAVE_FILE):
                    os.remove(SAVE_FILE)
                
                # Reset trolley
                self.trolley_row = ORIGIN_ROW
                self.trolley_col = ORIGIN_COL
                self.path_visualization.clear()
                self.trolley_path = []
                
                # Reset animation state
                self.is_animating = False
                self.operation_mode = 'idle'
                self.pending_box = None
                self.retrieving_box_id = None
                
                if self.animation_timer.isActive():
                    self.animation_timer.stop()
                
                # Update all UI
                self.update_grid_display()
                self.update_stats()
                self.update_dashboard()
                self.add_button.setEnabled(True)
                self.retrieve_button.setEnabled(True)
                
                self.status_label.setText("✅ Rack completely reset!")
                QMessageBox.information(self, "Reset Complete", "✅ All data cleared!\n\n✓ Boxes deleted\n✓ Dashboard reset\n✓ Cycles reset to 0")
                
            except Exception as e:
                QMessageBox.critical(self, "Reset Error", f"Error during reset:\n{str(e)}")

# ============================================================================
# SECTION 6: MAIN FUNCTION
# ============================================================================

def main():
    try:
        logger.info("Starting ASRS Application...")
        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        window = ASRSWindow()

        # Show maximized for large screens, normal for others
        if window.should_maximize:
            window.showMaximized()
            logger.info("Window shown maximized")
        else:
            window.show()
            logger.info("Window shown normal")

        logger.info("ASRS Application started successfully - GUI displayed")
        exit_code = app.exec()
        logger.info(f"ASRS Application exiting with code: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"FATAL ERROR: Application crashed - {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    # Only run standalone if launched directly
    app = QApplication(sys.argv)
    win = ASRSWindow()
    win.show()
    sys.exit(app.exec())
else:
    # When imported by open_gui_merged2.py, do nothing special
    pass

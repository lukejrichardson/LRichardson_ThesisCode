"""
This app is intended to connect to the Mechatronics Systems Group Thrust Stand design.
It utilises a PyQt5 GUI to display the data from the thrust stand in real-time, and allows the user to calibrate the sensors and set the throttle.
The data is also saved to a CSV file for later analysis.
The app is designed to be used with the corresponding Arduino code.
@author: Michael Thomson
@date: 2024-07-08
@version: 1.5.0
@status: Development
@requires: PyQt5, pyqtgraph, pyserial, crcmod, numpy
@license: MIT
"""

import sys
import os
from datetime import datetime
import subprocess
import json
from collections import deque
import struct
import time
from io import StringIO
import logging

#Constants for the application
BAUDRATES = ['9600', '19200', '38400', '57600', '115200', '230400', '250000', '460800', '500000', '921600']
DEFAULT_POLLING_RATE = 100
DEFAULT_PULSES_PER_REV = 1
MAX_POLLING_RATE = 1000
MAX_PULSES_PER_REV = 10
GRAPH_FPS = 30

import numpy as np
import serial
import crcmod
from serial.tools.list_ports import comports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QComboBox,
                             QLineEdit, QLabel, QFileDialog, QMessageBox, QTextEdit, QTabWidget, QAction, QCheckBox,
                             QListWidget, QListWidgetItem, QSplitter, QGroupBox, QSpinBox)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QSettings, Qt, QPointF
import pyqtgraph as pg
from PyQt5.QtGui import QColor


# Create a thread to read data from the serial port
class SerialThread(QThread):
    """
    A worker thread for handling serial communication with the Arduino.

    This thread continuously reads from the serial port, decodes incoming messages,
    and emits signals for data and status messages.

    Attributes:
        data_received (pyqtSignal): Signal emitted when sensor data is received.
        message_received (pyqtSignal): Signal emitted when a status message is received.

    Algorithm:
        1. Continuously read bytes from the serial port into a buffer.
        2. Look for the message start marker (0xFF).
        3. Parse the message type and length.
        4. Once a complete message is received, verify its CRC.
        5. If CRC is valid, process the message based on its type:
           - For sensor data (0x01), unpack and emit the data.
           - For status messages (0x03), decode and emit the message.
        6. Remove the processed message from the buffer and continue.
    """
    data_received = pyqtSignal(object)
    message_received = pyqtSignal(str)
    
    def __init__(self, serial_connection, crc_func):
        """
        Initialize the SerialThread.

        Args:
            serial_connection: An open pyserial connection to the Arduino.
            crc_func: A function to calculate CRC for message validation.
        """
        super().__init__()
        self.serial_connection = serial_connection
        self.running = True
        self.crc_func = crc_func
    
    def run(self):
        buffer = b""
        while self.running:
            try:
                if self.serial_connection and self.serial_connection.in_waiting:
                    buffer += self.serial_connection.read(self.serial_connection.in_waiting)
                    while len(buffer) >= 8:  # Minimum message size
                        if buffer[0] != 0xFF:  # Check for prefix
                            buffer = buffer[1:]
                            continue
                        
                        message_type = buffer[1]
                        message_length = struct.unpack('<I', buffer[2:6])[0]
                        
                        if len(buffer) < 8 + message_length + 2:  # Not enough data yet
                            break
                        
                        # Extract the message and CRC
                        message = buffer[6:6+message_length]
                        received_crc = struct.unpack('<H', buffer[6+message_length:8+message_length])[0]
                        calculated_crc = self.crc_func(message)

                        ##DEBUG##
                        # print(f"Received message type: {message_type:02X}")
                        # print(f"Message length: {message_length}")
                        # print(f"Message payload: {message.hex()}")
                        # print(f"Received CRC: {received_crc:04X}")
                        # print(f"Calculated CRC: {calculated_crc:04X}")
                        ##DEBUG##
                        
                        if calculated_crc == received_crc:
                            #print("CRC match - processing message")
                            if message_type == 0x01:  # Sensor data
                                # Unpack the sensor data
                                try:
                                    data = struct.unpack('<fffff', message)
                                    self.data_received.emit({
                                        'Thrust': data[0],
                                        'Torque': data[1],
                                        'RPM': data[2],
                                        'Voltage': data[3],
                                        'Current': data[4]
                                    })
                                    #print(f"Unpacked data: Thrust={data[0]:.2f}, Torque={data[1]:.2f}, RPM={data[2]:.2f}, Voltage={data[3]:.2f}, Current={data[4]:.2f}")
                                except struct.error as e:
                                    print(f"Error unpacking sensor data: {e}")
                            elif message_type == 0x03:  # Status message
                                decoded_message = message.decode('utf-8')
                                print(f"Received status message: {decoded_message}")
                                self.message_received.emit(decoded_message)
                        else:
                            print("CRC mismatch - discarding message")
                        
                        # Remove the processed message from the buffer
                        buffer = buffer[8+message_length:]
            except Exception as e:
                print(f"Error in SerialThread: {e}")
            self.msleep(1)

    def stop(self):
        self.running = False

# Create a thread to update the plot with new data from the serial port thread
class PlotThread(QThread):
    update_plot_signal = pyqtSignal(object)
    # Create a constructor to store the data source function and set the thread to running
    def __init__(self, data_source):
        super().__init__()
        self.data_source = data_source
        self.running = True

    # Create a run method to continuously update the plot with new data
    def run(self):
        while self.running:
            data = self.data_source()
            self.update_plot_signal.emit(data)
            self.msleep(int(1000/GRAPH_FPS))  # FPS (1000 ms / GRAPH_FPS = t ms)

    def stop(self):
        self.running = False

# Create a command class to represent the different types of commands that can be added to a test program
class Command:
    # Create a constructor to store the command type and value
    def __init__(self, command_type, value):
        self.command_type = command_type
        self.value = value

    # Create a string representation of the command
    def __str__(self):
        return f"{self.command_type}: {self.value}"

# Create subclasses for the different types of commands
class ThrottleCommand(Command):
    def __init__(self, value):
        super().__init__("throttle", value)

    def __str__(self):
        return f"Set Throttle: {self.value}%"

class WaitCommand(Command):
    def __init__(self, value):
        super().__init__("wait", value)

    def __str__(self):
        return f"Wait: {self.value} seconds"

class RampCommand(Command):
    def __init__(self, start_throttle, end_throttle, duration):
        # Unpack the tuple of (start_throttle, end_throttle, duration) and store the values
        super().__init__("ramp", (start_throttle, end_throttle, duration))
        self.start_throttle = start_throttle
        self.end_throttle = end_throttle
        self.duration = duration

    def __str__(self):
        return f"Ramp: {self.start_throttle}% to {self.end_throttle}% over {self.duration} seconds"

# Create a factory class to generate Command objects based on the command type and value
class CommandFactory:
    # Create a static method to generate Command objects based on the command type
    @staticmethod
    def create_command(command_type: str, value) -> Command:
        if command_type == "throttle":
            return ThrottleCommand(value)
        elif command_type == "wait":
            return WaitCommand(value)
        elif command_type == "ramp":
            return RampCommand(*value)  # Unpack the tuple of (start_throttle, end_throttle, duration)
        else:
            raise ValueError(f"Unknown command type: {command_type}")

# Create a custom text stream to redirect stdout to the terminal window in the UI
class StreamToTerminal(StringIO):
    def __init__(self, terminal_widget: QTextEdit) -> None:
        super().__init__()
        self.terminal_widget = terminal_widget

    def write(self, text: str) -> None:
        text = text.strip()  # Remove leading/trailing whitespace
        if text:  # Only append non-empty lines
            self.terminal_widget.append(text)
            # Scroll to the bottom
            self.terminal_widget.verticalScrollBar().setValue(
                self.terminal_widget.verticalScrollBar().maximum()
            )

# Create the main window for the data logger
class ArduinoDataLogger(QMainWindow):
    """
    Main application window for the UAV Thrust Stand Data Logger.

    This class manages the user interface, data processing, and communication
    with the Arduino. It handles user inputs, displays real-time data plots,
    and manages the overall application state.

    Attributes:
        serial_connection: The current serial connection to the Arduino.
        data: A numpy array storing all received sensor data.
        current_profile: A list of commands for the current test profile.

    Algorithm:
        1. Initialize the UI and plot widgets.
        2. Manage serial connection to the Arduino.
        3. Process incoming data and update plots in real-time.
        4. Handle user inputs for throttle control, calibration, and test profiles.
        5. Manage data export and settings persistence.
    """
    def __init__(self) -> None:
        """Initialize the main window and set up the user interface."""
        super().__init__()
        self.setWindowTitle("Thrust Stand Data Logger")
        # Set the window size and position on the screen (x, y, width, height)
        self.setGeometry(100, 100, 800, 800)
        # Initialize the serial connection and data storage
        self.serial_connection = None
        self.serial_thread = None
        # Create an empty numpy array to store sensor data
        self.data = np.array([], dtype=[('Timestamp', 'datetime64[ns]'),
                                    ('ElapsedTime', 'float64'),
                                    ('Thrust', 'float64'),
                                    ('Torque', 'float64'),
                                    ('RPM', 'float64'),
                                    ('Voltage', 'float64'),
                                    ('Current', 'float64'),
                                    ('Throttle', 'int32')])
        self.start_time = None
        self.calibration_in_progress = False
        self.message_queue = deque(maxlen=5)
        self.current_throttle = 0
        self.current_profile = []

        self.settings = QSettings("MechatronicsSystemsGroup", "ArduinoDataLogger")
        
        # Initialize CRC function
        self.crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        self.test_crc()
        # Initialize the UI
        self.setup_logging()
        self.init_ui()
        self.init_plot()  # Make sure this is called after init_ui

        # Redirect stdout to terminal windows
        sys.stdout = StreamToTerminal(self.main_terminal)

        # Create a thread to update the plot with new data
        self.plot_thread = PlotThread(self.get_plot_data)
        self.plot_thread.update_plot_signal.connect(self.update_plot)
        self.plot_thread.start()

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s', filename='arduino_data_logger.log')

    def init_ui(self) -> None:
        """Set up the user interface components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create menu bar
        self.create_menu_bar()

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self.tabChanged)

        # Main tab
        main_tab = QWidget()
        main_layout = QVBoxLayout()
        main_tab.setLayout(main_layout)

        # Define buttons and combo boxes (keep these definitions where they are)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)

        self.port_combo = QComboBox()
        self.port_combo.currentTextChanged.connect(self.update_connection_button_state)
        
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(BAUDRATES)
        self.baudrate_combo.setCurrentText('115200')

        # Add a refresh button next to the port combo box
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.refresh_ports_button.clicked.connect(lambda: self.update_port_list(True))
        # Add a refresh button next to the baudrate combo box
        self.throttle_value = QLineEdit()
        self.throttle_value.setPlaceholderText("Throttle% (0-100)")
        self.throttle_value.setMaximumWidth(150)
        # Add a button to set the throttle value
        self.set_throttle_button = QPushButton("Set Throttle")
        self.set_throttle_button.clicked.connect(self.set_throttle)
        # Add a button to stop the motor immediately
        self.emergency_stop_button = QPushButton("Emergency Stop")
        self.emergency_stop_button.clicked.connect(self.emergency_stop)
        self.emergency_stop_button.setStyleSheet("background-color: red; color: white; font-size: 16px; border-radius: 5px")

        # Group connection controls
        connection_group = QGroupBox("Connection")
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(self.connect_button)
        connection_layout.addWidget(self.refresh_ports_button)
        connection_layout.addWidget(self.port_combo)
        connection_layout.addWidget(self.baudrate_combo)
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # Group throttle controls
        throttle_group = QGroupBox("Throttle Control")
        throttle_layout = QHBoxLayout()
        throttle_layout.addWidget(self.throttle_value)
        throttle_layout.addWidget(self.set_throttle_button)
        throttle_layout.addWidget(self.emergency_stop_button)
        throttle_group.setLayout(throttle_layout)
        main_layout.addWidget(throttle_group)

        # Add plot widget
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        # Create a new group for graphing controls
        graph_control_group = QGroupBox("Graph Controls")
        graph_control_layout = QHBoxLayout()
        graph_control_group.setLayout(graph_control_layout)

        # Plot visibility checkboxes
        self.thrust_checkbox = QCheckBox("Thrust")
        self.thrust_checkbox.setChecked(True)
        self.thrust_checkbox.stateChanged.connect(self.update_plot)
        self.torque_checkbox = QCheckBox("Torque")
        self.torque_checkbox.setChecked(True)
        self.torque_checkbox.stateChanged.connect(self.update_plot)
        self.secondary_checkbox = QCheckBox("Secondary")
        self.secondary_checkbox.setChecked(True)
        self.secondary_checkbox.stateChanged.connect(self.update_plot)
        graph_control_layout.addWidget(self.thrust_checkbox)
        graph_control_layout.addWidget(self.torque_checkbox)
        graph_control_layout.addWidget(self.secondary_checkbox)

        # Secondary axis dropdown
        secondary_axis_label = QLabel("Secondary Axis:")
        graph_control_layout.addWidget(secondary_axis_label)
        self.secondary_axis_combo = QComboBox()
        self.secondary_axis_combo.setToolTip("Select the variable for the secondary (right) axis")
        self.secondary_axis_combo.currentTextChanged.connect(self.on_secondary_axis_changed)
        graph_control_layout.addWidget(self.secondary_axis_combo)

        # Add Live button
        self.live_button = QPushButton("Live")
        self.live_button.setCheckable(True)
        self.live_button.setChecked(True)
        self.live_button.clicked.connect(self.toggle_live_view)
        graph_control_layout.addWidget(self.live_button)

        # Add the graph control group to the main layout
        main_layout.addWidget(graph_control_group)

        # Group instantaneous values
        values_group = QGroupBox("Current Values")
        values_layout = QHBoxLayout()
        values_group.setLayout(values_layout)
        # Add labels for the instantaneous values
        self.throttle_label = QLabel("Throttle: 0%")
        self.thrust_label = QLabel("Thrust: 0 N")
        self.torque_label = QLabel("Torque: 0 Nm")
        self.rpm_label = QLabel("RPM: 0")
        self.voltage_label = QLabel("Voltage: 0 V")
        self.current_label = QLabel("Current: 0 A")
        # Add the labels to the layout
        values_layout.addWidget(self.throttle_label)
        values_layout.addWidget(self.thrust_label)
        values_layout.addWidget(self.torque_label)
        values_layout.addWidget(self.rpm_label)
        values_layout.addWidget(self.voltage_label)
        values_layout.addWidget(self.current_label)
        # Add the values group to the main layout
        main_layout.addWidget(values_group)

        # Add terminal-style window to main tab
        self.main_terminal = QTextEdit()
        self.main_terminal.setReadOnly(True)
        self.main_terminal.setMaximumHeight(100)
        main_layout.addWidget(self.main_terminal)
        # Add the main tab to the tab widget
        self.tab_widget.addTab(main_tab, "Main")

        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        settings_tab.setLayout(settings_layout)

        # Add polling rate setting
        polling_layout = QHBoxLayout()
        polling_layout.addWidget(QLabel("Polling Rate (Hz):"))
        self.polling_rate_spinbox = QSpinBox()
        self.polling_rate_spinbox.setRange(1, 1000)
        self.polling_rate_spinbox.setValue(self.settings.value("polling_rate", 100, type=int))
        polling_layout.addWidget(self.polling_rate_spinbox)
        self.update_polling_rate_button = QPushButton("Update Polling Rate")
        self.update_polling_rate_button.clicked.connect(self.send_polling_rate)
        polling_layout.addWidget(self.update_polling_rate_button)
        settings_layout.addLayout(polling_layout)

        # Add pulses per revolution setting
        ppr_layout = QHBoxLayout()
        ppr_layout.addWidget(QLabel("Pulses per Revolution:"))
        self.ppr_spinbox = QSpinBox()
        self.ppr_spinbox.setRange(1, 10)
        self.ppr_spinbox.setValue(self.settings.value("pulses_per_rev", 1, type=int))
        ppr_layout.addWidget(self.ppr_spinbox)
        self.update_ppr_button = QPushButton("Update Pulses per Rev")
        self.update_ppr_button.clicked.connect(self.send_pulses_per_rev)
        ppr_layout.addWidget(self.update_ppr_button)
        settings_layout.addLayout(ppr_layout)

        # Calibration controls
        thrust_calibration_group = QGroupBox("Thrust Sensor Calibration")
        thrust_calibration_layout = QHBoxLayout()
        self.tare_thrust_button = QPushButton("Tare Thrust")
        self.tare_thrust_button.clicked.connect(lambda: self.tare_sensor(0))
        self.calibrate_thrust_button = QPushButton("Calibrate Thrust Gain")
        self.calibrate_thrust_button.clicked.connect(lambda: self.calibrate_gain(0))
        self.thrust_calibration_value = QLineEdit()
        self.thrust_calibration_value.setPlaceholderText("Calibration Value (N)")
        thrust_calibration_layout.addWidget(self.tare_thrust_button)
        thrust_calibration_layout.addWidget(self.calibrate_thrust_button)
        thrust_calibration_layout.addWidget(self.thrust_calibration_value)
        thrust_calibration_group.setLayout(thrust_calibration_layout)
        settings_layout.addWidget(thrust_calibration_group)

        torque_calibration_group = QGroupBox("Torque Sensor Calibration")
        torque_calibration_layout = QHBoxLayout()
        self.tare_torque_button = QPushButton("Tare Torque")
        self.tare_torque_button.clicked.connect(lambda: self.tare_sensor(1))
        self.calibrate_torque_button = QPushButton("Calibrate Torque Gain")
        self.calibrate_torque_button.clicked.connect(lambda: self.calibrate_gain(1))
        self.torque_calibration_value = QLineEdit()
        self.torque_calibration_value.setPlaceholderText("Calibration Value (Nm)")
        torque_calibration_layout.addWidget(self.tare_torque_button)
        torque_calibration_layout.addWidget(self.calibrate_torque_button)
        torque_calibration_layout.addWidget(self.torque_calibration_value)
        torque_calibration_group.setLayout(torque_calibration_layout)
        settings_layout.addWidget(torque_calibration_group)

        # Add terminal-style window to settings tab
        self.settings_terminal = QTextEdit()
        self.settings_terminal.setReadOnly(True)
        self.settings_terminal.setMaximumHeight(100)
        settings_layout.addWidget(self.settings_terminal)
        # Add the settings tab to the tab widget
        self.tab_widget.addTab(settings_tab, "Settings")

        # Test Programs tab
        test_programs_tab = QWidget()
        test_programs_layout = QHBoxLayout()
        test_programs_tab.setLayout(test_programs_layout)

        # Left side: Available commands
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        # Add a label for the available commands
        left_layout.addWidget(QLabel("Available Commands"))

        # Create a widget to hold command buttons and entry fields
        commands_widget = QWidget()
        commands_layout = QVBoxLayout()
        commands_widget.setLayout(commands_layout)

        # Set Throttle command (keep existing definitions)
        throttle_layout = QHBoxLayout()
        throttle_button = QPushButton("Set Throttle")
        throttle_button.clicked.connect(lambda: self.add_command_to_profile("throttle"))
        throttle_layout.addWidget(throttle_button)
        self.throttle_entry = QLineEdit()
        self.throttle_entry.setPlaceholderText("Throttle %")
        throttle_layout.addWidget(self.throttle_entry)
        commands_layout.addLayout(throttle_layout)

        # Wait command (keep existing definitions)
        wait_layout = QHBoxLayout()
        wait_button = QPushButton("Wait")
        wait_button.clicked.connect(lambda: self.add_command_to_profile("wait"))
        wait_layout.addWidget(wait_button)
        self.wait_entry = QLineEdit()
        self.wait_entry.setPlaceholderText("Seconds")
        wait_layout.addWidget(self.wait_entry)
        commands_layout.addLayout(wait_layout)

        # Ramp command (keep existing definitions)
        ramp_layout = QHBoxLayout()
        ramp_button = QPushButton("Add Ramp")
        ramp_button.clicked.connect(lambda: self.add_command_to_profile("ramp"))
        ramp_layout.addWidget(ramp_button)
        self.ramp_start_entry = QLineEdit()
        self.ramp_start_entry.setPlaceholderText("Start %")
        ramp_layout.addWidget(self.ramp_start_entry)
        self.ramp_end_entry = QLineEdit()
        self.ramp_end_entry.setPlaceholderText("End %")
        ramp_layout.addWidget(self.ramp_end_entry)
        self.ramp_duration_entry = QLineEdit()
        self.ramp_duration_entry.setPlaceholderText("Duration (s)")
        ramp_layout.addWidget(self.ramp_duration_entry)
        commands_layout.addLayout(ramp_layout)
        # Add the commands widget to the left layout
        left_layout.addWidget(commands_widget)

        # Right side: Current profile
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        # Add a label for the current profile
        right_layout.addWidget(QLabel("Current Profile"))
        # Create a list widget to display the current profile
        self.current_profile_list = QListWidget()
        right_layout.addWidget(self.current_profile_list)
        # Add a button to remove a command from the profile
        remove_command_button = QPushButton("Remove Command")
        remove_command_button.clicked.connect(self.remove_command_from_profile)
        right_layout.addWidget(remove_command_button)
        # Add buttons to manage the profile
        load_profile_button = QPushButton("Load Profile")
        load_profile_button.clicked.connect(self.load_profile)
        right_layout.addWidget(load_profile_button)
        # Add a button to create a new profile
        save_profile_button = QPushButton("Save Profile")
        save_profile_button.clicked.connect(self.save_profile)
        right_layout.addWidget(save_profile_button)
        # Add a button to create a new profile
        execute_profile_button = QPushButton("Execute Profile")
        execute_profile_button.clicked.connect(self.execute_profile)
        right_layout.addWidget(execute_profile_button)

        # Add splitter to divide the left and right widgets
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        test_programs_layout.addWidget(splitter)
        # Add the test programs tab to the tab widget
        self.tab_widget.addTab(test_programs_tab, "Test Programs")

        # Load settings from QSettings (COM port and baudrate)
        self.load_settings()
        # Post-initialization setup
        self.update_connection_button_state()

        #Tooltips for buttons
        self.connect_button.setToolTip("Connect or disconnect from the Arduino")
        self.port_combo.setToolTip("Select the COM port for the Arduino")
        self.baudrate_combo.setToolTip("Select the baud rate for serial communication")
        self.throttle_value.setToolTip("Enter the desired throttle percentage (0-100)")
        self.set_throttle_button.setToolTip("Set the throttle to the specified value")
        self.emergency_stop_button.setToolTip("Immediately stop the motor")
        self.calibrate_thrust_button.setToolTip("Calibrate the thrust sensor")
        self.calibrate_torque_button.setToolTip("Calibrate the torque sensor")
        self.refresh_ports_button.setToolTip("Refresh the list of available COM ports")
        self.polling_rate_spinbox.setToolTip("Set the polling rate for sensor data")
        self.update_polling_rate_button.setToolTip("Update the polling rate on the Arduino")
        self.ppr_spinbox.setToolTip("Set the pulses per revolution for the RPM sensor (1 for motor body, else number of propellor blades)")
        self.update_ppr_button.setToolTip("Update the pulses per revolution on the Arduino")
        self.throttle_entry.setToolTip("Enter the throttle percentage for the command")
        self.wait_entry.setToolTip("Enter the wait time in seconds for the command")
        self.ramp_start_entry.setToolTip("Enter the starting throttle percentage for the ramp")
        self.ramp_end_entry.setToolTip("Enter the ending throttle percentage for the ramp")
        self.ramp_duration_entry.setToolTip("Enter the duration of the ramp in seconds")
        self.torque_checkbox.setToolTip("Toggle visibility of the torque data on the plot")
        self.secondary_checkbox.setToolTip("Toggle visibility of the secondary axis data on the plot")
        self.secondary_axis_combo.setToolTip("Select the variable to display on the secondary axis")
        self.main_terminal.setToolTip("Terminal window for status messages and data logging")
        self.settings_terminal.setToolTip("Terminal window for settings messages and calibration")


    def create_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu('File')
        # Export CSV action 
        export_action = QAction('Export CSV', self)
        export_action.triggered.connect(self.export_csv)
        file_menu.addAction(export_action)
        # Open data file action
        open_action = QAction('Open Data File', self)
        open_action.triggered.connect(self.open_data_file)
        file_menu.addAction(open_action)
        # Clear data action 
        clear_action = QAction('Clear Data', self)
        clear_action.triggered.connect(self.clear_data)
        file_menu.addAction(clear_action)

    def post_init(self) -> None:
        """Run any post-initialization setup tasks."""
        self.update_port_list(show_error=False)
        self.update_connection_button_state()
        self.update_secondary_axis_options()
        self.update_connection_button_state()

    def execute_profile(self) -> None:
        # Check if a profile is loaded and the Arduino is connected before executing the profile
        if not self.serial_connection:
            QMessageBox.warning(self, "Connection Error",
                                "Not connected to Arduino. Please connect first.",
                                QMessageBox.Ok)
            self.tab_widget.setCurrentIndex(0)  # Switch to Main tab to show connection controls
        else:
            self.tab_widget.setCurrentIndex(0)  # Switch to Main tab
            self.execute_test_program() # Execute the current test profile
        
    def execute_test_program(self) -> None:
        # Execute the current test program by sending commands to the Arduino
        # Check if a test program is loaded
        if not self.current_profile:
            print("No test program loaded. Please load or create a profile first.")
            return
        self.program_step = 0
        self.execute_next_command()

    def execute_next_command(self):
        # Execute the next command in the test program
        if self.program_step < len(self.current_profile):
            # Get the next command from the profile and execute it based on the command type
            command = self.current_profile[self.program_step]
            # Check the command type and execute the appropriate action
            if isinstance(command, ThrottleCommand):
                self.set_throttle_value(command.value)
                self.program_step += 1
                QTimer.singleShot(100, self.execute_next_command)  # Short delay before next command
            elif isinstance(command, WaitCommand):
                QTimer.singleShot(int(command.value * 1000), self.execute_next_command)
                self.program_step += 1
            elif isinstance(command, RampCommand):
                self.execute_ramp(command.start_throttle, command.end_throttle, command.duration)
                QTimer.singleShot(int(command.duration * 1000) + 100, self.execute_next_command)
                self.program_step += 1
            print(f"Executed command: {command}")
        else:
            print("Test program execution completed.")

    def execute_ramp(self, start_throttle: float, end_throttle: float, duration: float) -> None:
        # Execute a ramp command by gradually changing the throttle value over time
        steps = 100
        step_duration = duration / steps
        self.ramp_step = 0
        self.ramp_start = start_throttle
        self.ramp_end = end_throttle
        self.ramp_steps = steps
        # Create a QTimer to update the throttle value at each step
        self.ramp_timer = QTimer(self)
        # Connect the timer to the ramp_step_function
        self.ramp_timer.timeout.connect(self.ramp_step_function)
        # Start the timer with the step duration
        self.ramp_timer.start(int(step_duration * 1000))  # Convert to milliseconds

    def ramp_step_function(self):
        """
        Update the throttle value for a ramp command.
        """
        # Calculate the throttle value based on the current step
        if self.ramp_step <= self.ramp_steps:
            # Calculate the throttle value based on the current step and update the throttle
            throttle = self.ramp_start + (self.ramp_end - self.ramp_start) * (self.ramp_step / self.ramp_steps)
            self.set_throttle_value(int(throttle))
            self.ramp_step += 1
        else:
            self.ramp_timer.stop()

    def set_throttle_value(self, value: int) -> None:
        # Set the throttle value and update the UI
        self.throttle_value.setText(str(value))
        self.set_throttle()

    def add_command_to_profile(self, command_type: str) -> None:
        """
        Add a new command to the current test profile.

        This method is called when the user adds a command in the Test Programs tab.
        It creates a new Command object and adds it to the current profile.

        Args:
            command_type (str): The type of command to add ('throttle', 'wait', or 'ramp').

        The method:
        1. Retrieves the necessary parameters from the UI inputs.
        2. Validates the input values.
        3. Creates the appropriate Command object.
        4. Adds the command to the current profile and updates the UI list.

        Raises:
            ValueError: If invalid parameter values are provided.
        """
        try:
            # Create a new Command object based on the command type and input values
            if command_type == "throttle":
                value = float(self.throttle_entry.text())
                if 0 <= value <= 100:
                    command = ThrottleCommand(value)
                else:
                    raise ValueError("Throttle must be between 0 and 100")
            # Create a new WaitCommand object based on the input value
            elif command_type == "wait":
                value = float(self.wait_entry.text())
                if value > 0:
                    command = WaitCommand(value)
                else:
                    raise ValueError("Wait time must be positive")
            # Create a new RampCommand object based on the input values
            elif command_type == "ramp":
                start = float(self.ramp_start_entry.text())
                end = float(self.ramp_end_entry.text())
                duration = float(self.ramp_duration_entry.text())
                if 0 <= start <= 100 and 0 <= end <= 100 and duration > 0:
                    command = RampCommand(start, end, duration)
                else:
                    raise ValueError("Invalid ramp parameters")
            else:
                # Raise an error if the command type is unknown
                raise ValueError("Unknown command type")

            # Add the command to the current profile and update the UI list
            self.current_profile.append(command)
            self.current_profile_list.addItem(QListWidgetItem(str(command)))
            
            # Clear the entry fields after adding the command
            if command_type == "throttle":
                self.throttle_entry.clear()
            elif command_type == "wait":
                self.wait_entry.clear()
            elif command_type == "ramp":
                self.ramp_start_entry.clear()
                self.ramp_end_entry.clear()
                self.ramp_duration_entry.clear()
        
        # Catch any ValueError exceptions and display an error message
        except ValueError as e:
            print(f"Invalid input: {str(e)}")

    # Remove the selected command from the current profile
    def remove_command_from_profile(self) -> None:
        # Remove the selected command from the current profile and update the UI list
        selected_item = self.current_profile_list.currentItem()
        # Check if an item is selected before removing it
        if selected_item:
            # Get the row of the selected item and remove the command from the profile list
            row = self.current_profile_list.row(selected_item)
            self.current_profile_list.takeItem(row)
            del self.current_profile[row]

    def save_profile(self) -> None:
        """
        Save the current test profile to a JSON file.

        This method is called when the user clicks the 'Save Profile' button.
        It serializes the current profile to JSON format and saves it to a file.

        The method:
        1. Opens a file dialog for the user to choose the save location.
        2. Converts the Command objects to a JSON-serializable format.
        3. Writes the JSON data to the chosen file.

        Raises:
            IOError: If there's an error writing to the file.
        """
        # Open a file dialog to choose the save location
        filename, _ = QFileDialog.getSaveFileName(self, "Save Profile", "", "JSON Files (*.json)")
        if filename:
            profile_data = []
            # Convert each Command object to a JSON-serializable format and add it to the profile data list 
            for cmd in self.current_profile:
                if isinstance(cmd, RampCommand):
                    profile_data.append({"command_type": cmd.command_type, "value": (cmd.start_throttle, cmd.end_throttle, cmd.duration)})
                else:
                    profile_data.append({"command_type": cmd.command_type, "value": cmd.value})
            # Write the profile data to the chosen file
            with open(filename, 'w') as f:
                json.dump(profile_data, f)
            print(f"Profile saved to {filename}")

    def load_profile(self) -> None:
        """
        Load a test profile from a JSON file.

        This method is called when the user clicks the 'Load Profile' button.
        It reads a JSON file and populates the current profile with the loaded commands.

        The method:
        1. Opens a file dialog for the user to choose the profile file.
        2. Reads and parses the JSON data from the file.
        3. Creates Command objects from the parsed data.
        4. Populates the current profile and updates the UI list.

        Raises:
            IOError: If there's an error reading the file.
            json.JSONDecodeError: If the file contains invalid JSON data.
        """
        # Open a file dialog to choose the profile file
        try:
            # Load the profile data from the selected JSON file and populate the current profile
            filename, _ = QFileDialog.getOpenFileName(self, "Load Profile", "", "JSON Files (*.json)")
            if filename:
                # Read the profile data from the selected file and populate the current profile
                with open(filename, 'r') as f:
                    profile_data = json.load(f)
                self.current_profile.clear()
                self.current_profile_list.clear()
                # Create Command objects from the loaded data and add them to the current profile list
                for cmd_data in profile_data:
                    command = CommandFactory.create_command(cmd_data["command_type"], cmd_data["value"])
                    self.current_profile.append(command)
                    self.current_profile_list.addItem(QListWidgetItem(str(command)))
                logging.info(f"Profile loaded from {filename}")
                QMessageBox.information(self, "Profile Loaded", f"Profile successfully loaded from {filename}")
        # Catch any exceptions that occur during the loading process and display an error message
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            QMessageBox.critical(self, "Load Error", f"Invalid profile file format: {str(e)}")
        except IOError as e:
            logging.error(f"Error reading file: {e}")
            QMessageBox.critical(self, "Load Error", f"Failed to read file: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error loading profile: {e}")
            QMessageBox.critical(self, "Load Error", f"An unexpected error occurred: {str(e)}")

    def new_profile(self) -> None:
        # Clear the current profile and update the UI list
        self.current_profile.clear()
        self.current_profile_list.clear()
        self.tab_widget.setCurrentIndex(2)  # Switch to Test Programs tab

    # Initialise the plot widget with labels and colours for thrust, torque, and RPM data
    def init_plot(self) -> None:
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Thrust (N) / Torque (Nm)')
        self.plot_widget.setLabel('bottom', 'Elapsed Time (s)')
        self.plot_widget.addLegend()

        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange()

        # Enable grid
        self.plot_widget.showGrid(x=True, y=True)

        # Create plot items
        self.thrust_curve = self.plot_widget.plot(pen=pg.mkPen(color='r', width=2), name='Thrust')
        self.torque_curve = self.plot_widget.plot(pen=pg.mkPen(color='g', width=2), name='Torque')

        # Create a secondary y-axis
        self.secondary_axis = self.plot_widget.getAxis('right')
        self.secondary_axis_widget = pg.ViewBox()
        self.plot_widget.scene().addItem(self.secondary_axis_widget)
        self.secondary_axis.linkToView(self.secondary_axis_widget)
        self.secondary_axis_widget.setXLink(self.plot_widget.plotItem)
        
        # Set the label and colour for the secondary axis
        self.secondary_curve = pg.PlotDataItem(pen=pg.mkPen(color='b', width=2))
        self.secondary_axis_widget.addItem(self.secondary_curve)

        # Set up the layout
        def updateViews():
            self.secondary_axis_widget.setGeometry(self.plot_widget.plotItem.vb.sceneBoundingRect())
            self.secondary_axis_widget.linkedViewChanged(self.plot_widget.plotItem.vb, self.secondary_axis_widget.XAxis)
        
        # Connect the updateViews function to the plot widget
        updateViews()
        self.plot_widget.plotItem.vb.sigResized.connect(updateViews)
        
        # Set the secondary axis label
        self.plot_widget.setAutoVisible(y=True)

        # Initialize live view flag
        self.is_live_view = True

    def set_live_view(self):
        self.plot_widget.enableAutoRange()
        self.is_live_view = True

    def toggle_live_view(self):
        self.is_live_view = self.live_button.isChecked()
        if self.is_live_view:
            self.plot_widget.enableAutoRange()
        else:
            self.plot_widget.disableAutoRange()

    # Toggle the connection to the Arduino and start/stop the serial thread to read data
    def toggle_connection(self) -> None:
        """
        Establish or close the serial connection to the Arduino.

        This method is called when the user clicks the connect/disconnect button.
        It handles the entire connection process, including port selection,
        baud rate setting, and initial communication with the Arduino.

        If connecting, it:
        1. Validates the selected port.
        2. Attempts to open the serial connection.
        3. Initializes the SerialThread for data reception.
        4. Sends initial settings to the Arduino.

        If disconnecting, it:
        1. Stops the SerialThread.
        2. Closes the serial connection.

        The method updates the UI to reflect the current connection state.

        Raises:
            serial.SerialException: If there's an error opening the serial port.
        """
        # Toggle the connection state based on the current connection status
        if self.serial_connection is None:
            # Check if a valid port is selected before connecting
            if self.is_valid_port_selected():
                try:
                    # Open the serial connection and start the SerialThread
                    port = self.port_combo.currentText().split(":")[0].strip()
                    baudrate = int(self.baudrate_combo.currentText())
                    # Open the serial connection and start the SerialThread
                    self.serial_connection = serial.Serial(port, baudrate, timeout=1)
                    self.connect_button.setText("Disconnect")
                    # Create a new SerialThread for reading data from the Arduino and start it
                    self.serial_thread = SerialThread(self.serial_connection, self.crc_func)
                    # Connect the data_received and message_received signals to the corresponding slots
                    self.serial_thread.data_received.connect(self.process_data)
                    self.serial_thread.message_received.connect(self.process_message)
                    self.serial_thread.start()
                    # Update the connection status in the UI and send the initial settings to the Arduino 
                    self.save_settings()
                    self.statusBar().showMessage("Connected to Arduino")
                    self.send_settings()
                except serial.SerialException as e:
                    logging.error(f"Failed to connect: {e}")
                    QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
                    self.statusBar().showMessage(f"Connection failed: {e}")
                except ValueError as e:
                    logging.error(f"Invalid baudrate: {e}")
                    QMessageBox.critical(self, "Connection Error", f"Invalid baudrate: {str(e)}")
            else:
                QMessageBox.warning(self, "No Port Selected", "Please select a valid COM port.")
        else:
            # Stop the SerialThread and close the serial connection
            try:
                self.serial_thread.stop()
                self.serial_thread.wait()
                self.serial_connection.close()
            except Exception as e:
                logging.error(f"Error during disconnection: {e}")
                QMessageBox.warning(self, "Disconnection Error", f"Error during disconnection: {str(e)}")
            finally:
                self.serial_connection = None
                self.serial_thread = None
                self.connect_button.setText("Connect")
                self.statusBar().showMessage("Disconnected from Arduino")

        self.update_connection_status()
        self.update_connection_button_state()

    # Check if a valid port is selected in the dropdown
    def is_valid_port_selected(self) -> bool:
        return ":" in self.port_combo.currentText()

    def update_connection_status(self) -> None:
        # Update the connection status in the UI
        if self.serial_connection and self.serial_connection.is_open:
            self.statusBar().showMessage("Connected to Arduino")
            self.connect_button.setText("Disconnect")
            self.connect_button.setStyleSheet("background-color: green; color: white;")
        else:
            self.statusBar().showMessage("Not connected to Arduino")
            self.connect_button.setText("Connect")
            self.connect_button.setStyleSheet("")
    
    def tabChanged(self, index: int) -> None:
        # Update the plot when switching to the main tab
        self.update_connection_status()

    def send_polling_rate(self) -> None:
        # Send the updated polling rate to the Arduino
        # Check if connected before sending the polling rate
        if not self.serial_connection:
            # Display a warning if not connected
            QMessageBox.warning(self, "Connection Error",
                                "Not connected to Arduino. Please connect first.",QMessageBox.Ok)
            self.tab_widget.setCurrentIndex(0)  # Switch to Main tab to show connection controls
        else:
            # Get the polling rate value from the spinbox
            value = self.polling_rate_spinbox.value()
            # Save the polling rate to QSettings
            self.settings.setValue("polling_rate", value)
            # Send the polling rate update to the Arduino
            self.send_binary_message(0x04, struct.pack('<I', value))
            # Print a message to the console
            print(f"Sent polling rate update: {value} Hz")

    def send_pulses_per_rev(self) -> None:
        # Send the updated pulses per revolution to the Arduino
        # Check if connected before sending the pulses per revolution
        if not self.serial_connection:
            QMessageBox.warning(self, "Connection Error",
                                "Not connected to Arduino. Please connect first.", QMessageBox.Ok)
            self.tab_widget.setCurrentIndex(0)  # Switch to Main tab to show connection controls
        else:
            # Get the pulses per revolution value from the spinbox
            value = self.ppr_spinbox.value()
            # Save the pulses per revolution to QSettings
            self.settings.setValue("pulses_per_rev", value)
            # Send the pulses per revolution update to the Arduino
            self.send_binary_message(0x06, struct.pack('<B', value))
            # Print a message to the console
            print(f"Sent pulses per revolution update: {value}")

    def update_polling_rate(self, value: int) -> None:
        # Update the polling rate value in the settings and send it to the Arduino
        self.settings.setValue("polling_rate", value)
        self.send_binary_message(0x04, struct.pack('<I', value))

    def update_pulses_per_rev(self, value: int) -> None:
        # Update the pulses per revolution value in the settings and send it to the Arduino
        if not self.serial_connection:
            QMessageBox.warning(self, "Connection Error",
                                "Not connected to Arduino. Please connect first.",
                                QMessageBox.Ok)
            self.tab_widget.setCurrentIndex(0)  # Switch to Main tab to show connection controls
        else:
            # Save the pulses per revolution to QSettings
            self.settings.setValue("pulses_per_rev", value)
            self.send_binary_message(0x06, struct.pack('<B', value))
        

    def send_binary_message(self, message_type: int, payload: bytes) -> None:
        """
        Send a binary message to the Arduino.

        This method constructs a complete message with prefix, message type,
        payload length, payload, and CRC, then sends it over the serial connection.

        Args:
            message_type (int): The type of message being sent (e.g., 0x02 for calibration).
            payload (bytes): The message payload.

        Raises:
            serial.SerialException: If there's an error writing to the serial port.
        """
        # Check if connected before sending the message
        if self.serial_connection:
            # Construct the message with prefix, message type, payload length, payload, and CRC
            # Prefix (1 byte), message type (1 byte), message length (4 bytes), payload, CRC (2 bytes)

            prefix = 0xFF
            message_length = len(payload)
            crc = self.crc_func(payload)
            # Construct the message and send it over the serial connection
            message = struct.pack('<BBI', prefix, message_type, message_length) + payload + struct.pack('<H', crc)
            self.serial_connection.write(message)
        else:
            # Display a warning if not connected
            print("Not connected to Arduino")
            QMessageBox.warning(self, "Not Connected", "Please connect to the Arduino before sending settings.")


    # Process the data received from the serial port
    def process_data(self, data: dict[str, any]) -> None:
        """
        Process incoming sensor data from the Arduino.

        This method is called whenever new sensor data is received. It adds
        the new data to the existing dataset and updates the UI.

        Args:
            data (dict): A dictionary containing the latest sensor readings.

        The method:
        1. Calculates the elapsed time since data logging started.
        2. Adds the new data point to the numpy array.
        3. Updates the instantaneous value labels in the UI.
        """

        try:
            # Calculate the elapsed time since data logging started
            current_time = np.datetime64(datetime.now())
            # If the start time is None, set it to the current time
            if self.start_time is None:
                # Set the start time to the current time
                self.start_time = current_time
            # Calculate the elapsed time in seconds
            elapsed_time = (current_time - self.start_time) / np.timedelta64(1, 's')
            # Add the new data point to the numpy array and update the labels in the UI
            new_row = np.array([(current_time, elapsed_time, 
                                 data['Thrust'], data['Torque'], data['RPM'], 
                                 data['Voltage'], data['Current'], self.current_throttle)],
                               dtype=self.data.dtype)
            self.data = np.concatenate((self.data, new_row))
            self.update_labels(new_row[0])
        except KeyError as e:
            logging.error(f"Missing key in data: {e}")
            QMessageBox.warning(self, "Data Error", f"Missing data field: {str(e)}")
        except ValueError as e:
            logging.error(f"Error processing data values: {e}")
            QMessageBox.warning(self, "Data Error", f"Invalid data value: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error processing data: {e}")
            QMessageBox.critical(self, "Data Processing Error", f"An unexpected error occurred: {str(e)}")

    def process_message(self, message: str) -> None:
        # Process incoming messages from the Arduino
        self.message_queue.append(message)
        self.update_terminal()
        # Optionally, can also show a popup for important messages
        # QMessageBox.information(self, "Status Update", message)

    def test_crc(self):
        test_data = bytes([0x01, 0x02, 0x03, 0x04])
        crc = self.crc_func(test_data)
        print(f"Test CRC: {crc:04X}")

    # Update the labels for the instantaneous values (Thrust, Torque, RPM)
    def update_labels(self, data: np.ndarray) -> None:
        # Update the labels for the instantaneous values in the UI
        self.thrust_label.setText(f"Thrust: {data['Thrust']:.2f} N")
        self.torque_label.setText(f"Torque: {data['Torque']:.2f} Nm")
        self.rpm_label.setText(f"RPM: {data['RPM']:.0f}")
        self.voltage_label.setText(f"Voltage: {data['Voltage']:.2f} V")
        self.current_label.setText(f"Current: {data['Current']:.2f} A")
        self.throttle_label.setText(f"Throttle: {data['Throttle']}%")

    # Update the terminal-style window with messages
    def update_terminal(self) -> None:
        # Update the terminal-style window with the latest messages in the queue
        for terminal in [self.main_terminal, self.settings_terminal]:
            terminal.clear()
            terminal.append("\n".join(filter(bool, self.message_queue)))

    def get_plot_data(self) -> np.ndarray:
        #Copy the data to avoid potential threading issues
        return np.copy(self.data)

    # Update the plot with the latest data
    def update_plot(self, data=None) -> None:
        if data is None:
            data = self.data

        if not isinstance(data, np.ndarray) or data.size == 0:
            return

        x_data = data['ElapsedTime']

        if self.thrust_checkbox.isChecked():
            self.thrust_curve.setData(x_data, data['Thrust'])
        else:
            self.thrust_curve.clear()

        if self.torque_checkbox.isChecked():
            self.torque_curve.setData(x_data, data['Torque'])
        else:
            self.torque_curve.clear()

        if self.secondary_checkbox.isChecked():
            secondary_var = self.secondary_axis_combo.currentText()
            self.secondary_curve.setData(x_data, data[secondary_var])
            self.secondary_axis.show()
        else:
            self.secondary_curve.clear()
            self.secondary_axis.hide()

        if self.is_live_view and x_data.size > 0:
            self.plot_widget.setXRange(max(0, x_data[-1] - 60), x_data[-1], padding=0)
        
        self.plot_widget.enableAutoRange(axis='y')
        self.secondary_axis_widget.enableAutoRange(axis='y')

    def closeEvent(self, event) -> None:
        # Stop the plot thread when closing the application
        self.plot_thread.stop()
        self.plot_thread.wait()
        super().closeEvent(event)    
    
    def update_legend(self) -> None:
        # Update the legend on the plot with the current curves
        self.plot_widget.plotItem.legend.clear()
        self.plot_widget.plotItem.legend.addItem(self.thrust_curve, 'Thrust')
        self.plot_widget.plotItem.legend.addItem(self.torque_curve, 'Torque')
        secondary_var = self.secondary_axis_combo.currentText()
        self.plot_widget.plotItem.legend.addItem(self.secondary_curve, secondary_var)
        
    def update_secondary_axis_options(self) -> None:
        """
        Update the options for the secondary Y-axis on the plot.

        This method is called when the data structure changes or when
        initializing the plot. It populates the dropdown menu with
        available data fields for the secondary axis.

        The method:
        1. Identifies available data fields (excluding certain fields).
        2. Updates the dropdown menu with these options.
        3. Attempts to maintain the previously selected option if still available.
        4. Updates the plot and legend to reflect any changes.
        """
        # Get the available data fields for the secondary axis (excluding certain fields)
        excluded_fields = ['Timestamp', 'ElapsedTime', 'Thrust', 'Torque', 'Throttle']
        options = [field for field in self.data.dtype.names if field not in excluded_fields]
        # Update the dropdown menu with the available options
        current_selection = self.secondary_axis_combo.currentText()
        # Clear the existing options and add the new ones
        self.secondary_axis_combo.clear()
        self.secondary_axis_combo.addItems(options)
        # Attempt to maintain the previously selected option if still available
        if current_selection in options:
            self.secondary_axis_combo.setCurrentText(current_selection)
        elif 'RPM' in options:
            self.secondary_axis_combo.setCurrentText('RPM')
        elif options:
            self.secondary_axis_combo.setCurrentIndex(0)
        # Update the plot and legend to reflect any changes
        self.update_plot()
        self.update_legend()

    def on_secondary_axis_changed(self):
        # Update the plot and legend when the secondary axis selection changes
        self.update_plot(self.data)
        self.update_legend()

    # Export the data to a CSV file with a timestamped filename for easy reference later
    def export_csv(self) -> None:
        """
        Export the current dataset to a CSV file.

        This method is called when the user selects 'Export CSV' from the File menu.
        It saves all collected sensor data to a CSV file with a timestamp in the filename.

        The method:
        1. Generates a filename with the current timestamp.
        2. Opens a file dialog for the user to choose the save location.
        3. Writes the header row and all data points to the CSV file.

        Raises:
            IOError: If there's an error writing to the file.
        """
        # Generate a filename with the current timestamp
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"thrust_stand_data_{timestamp}.csv"
            # Open a file dialog to choose the save location
            filename, _ = QFileDialog.getSaveFileName(self, "Save CSV", default_filename, "CSV Files (*.csv)")
            if filename:
                header = "Timestamp,ElapsedTime,Thrust,Torque,RPM,Voltage,Current,Throttle"
                np.savetxt(filename, self.data, delimiter=",", header=header, comments="", 
                        fmt=['%s', '%.3f', '%.2f', '%.2f', '%.0f', '%.2f', '%.2f', '%d'])
                logging.info(f"Data exported to {filename}")
                QMessageBox.information(self, "Export Successful", f"Data exported to {filename}")
        # Handle exceptions for errors during CSV export
        except IOError as e:
            logging.error(f"Error writing to file: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to write to file: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error during CSV export: {e}")
            QMessageBox.critical(self, "Export Error", f"An unexpected error occurred: {str(e)}")

    # Clear the data from the plot and the data frame in memory
    def clear_data(self) -> None:
        # Clear the data from the plot and the data frame
        reply = QMessageBox.question(self, 'Clear Data', 'Are you sure you want to clear the data?', QMessageBox.Yes | QMessageBox.No)
        # Check if the user confirmed the data clear action
        if reply == QMessageBox.Yes:
            #Clear data array and reset start time
            self.data = np.array([], dtype=self.data.dtype)
            self.start_time = None
            self.update_plot(self.data)
            print("Data cleared")
        else:
            print("Data not cleared")

    # Get a list of available COM ports for the dropdown
    def get_available_ports(self) -> list[str]:
        # Get a list of available COM ports and filter out non-Arduino ports
        available_ports = []
        for port in comports():
            if ("USB" in port.description.upper() or "CH340" in port.description.upper() or "ARDUINO" in port.description.upper()) and "BLUETOOTH" not in port.description.upper():
                available_ports.append(f"{port.device}: {port.description}")
        return available_ports

    # Update the list of available COM ports in the dropdown
    def update_port_list(self, show_error=True) -> None:
        # Update the list of available COM ports in the dropdown
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        ports = self.get_available_ports()
        # Add the available ports to the dropdown and select the current port if available
        if ports:
            self.port_combo.addItems(ports)
            if current_port in ports:
                self.port_combo.setCurrentText(current_port)
        else:
            self.port_combo.addItem("No ports found")
            if show_error:
                QMessageBox.warning(self, "No Ports Found", "No suitable COM ports were found. Please check your connection and try again.")

        self.update_connection_button_state()

    def update_connection_button_state(self):
        # Enable or disable the connect button based on the selected port and connection status 
        self.connect_button.setEnabled(self.is_valid_port_selected())

    def tare_sensor(self, sensor_type: int):
        if not self.serial_connection:
            QMessageBox.warning(self, "Not Connected", "Please connect to the Arduino before taring.")
            return
        
        sensor_name = "Thrust" if sensor_type == 0 else "Torque"
        self.send_binary_message(0x08, struct.pack('<B', sensor_type))
        QMessageBox.information(self, "Tare", f"Starting {sensor_name} sensor tare. Please wait.")

    def calibrate_gain(self, sensor_type: int):
        if not self.serial_connection:
            QMessageBox.warning(self, "Not Connected", "Please connect to the Arduino before calibrating.")
            return
        
        sensor_name = "Thrust" if sensor_type == 0 else "Torque"
        calibration_value = self.thrust_calibration_value.text() if sensor_type == 0 else self.torque_calibration_value.text()
        
        try:
            cal_value = float(calibration_value)
            self.send_binary_message(0x09, struct.pack('<Bf', sensor_type, cal_value))
            QMessageBox.information(self, "Calibration", f"Starting {sensor_name} sensor gain calibration. Please wait.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for calibration.")

    # Calibrate the sensors with a known value (tare) and a calibration value
    def calibrate(self, sensor_type: int) -> None:
        if not self.serial_connection:
            logging.error("Attempted calibration without active connection")
            QMessageBox.warning(self, "Not Connected", "Please connect to the Arduino before calibrating.")
            return

        calibration_value = self.calibration_value.text()
        if not calibration_value:
            logging.warning("No calibration value provided")
            QMessageBox.warning(self, "Invalid Input", "Please enter a calibration value.")
            return
        
        try:
            cal_value = float(calibration_value)
            command = struct.pack('<Bf', sensor_type, cal_value)
            self.send_binary_message(0x02, command)
            logging.info(f"Sent calibration command for sensor {sensor_type}")

            # Use a QTimer to wait for the tare completion message
            self.calibration_timer = QTimer()
            self.calibration_timer.setSingleShot(True)
            self.calibration_timer.timeout.connect(lambda: self.calibration_timeout(sensor_type))
            self.calibration_timer.start(10000)  # 10 second timeout

            # Connect a slot to handle the calibration messages
            self.serial_thread.message_received.connect(self.handle_calibration_message)
            
        except ValueError:
            logging.error("Invalid calibration value provided")
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for calibration.")
        except struct.error as e:
            logging.error(f"Error packing calibration command: {e}")
            QMessageBox.critical(self, "Calibration Error", f"Failed to prepare calibration command: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error during calibration: {e}")
            QMessageBox.critical(self, "Calibration Error", f"An unexpected error occurred: {str(e)}")

    def handle_calibration_message(self, message):
        if "Starting tare" in message:
            QMessageBox.information(self, 'Calibration', 'Tare process started. Please wait.')
        elif "Tare completed" in message:
            self.calibration_timer.stop()
            # Use a flag to prevent multiple popups
            if not hasattr(self, 'calibration_dialog_shown'):
                self.calibration_dialog_shown = True
                reply = QMessageBox.question(self, 'Calibration', 
                                            'Tare completed. Apply calibration load and click OK to proceed, or Cancel to stop.',
                                            QMessageBox.Ok | QMessageBox.Cancel)
                if reply == QMessageBox.Ok:
                    self.send_binary_message(0x02, struct.pack('<B', 1))
                    # Start another timer for completion message
                    self.calibration_timer.timeout.connect(lambda: self.calibration_completion_timeout())
                    self.calibration_timer.start(40000)  # 40 second timeout
                else:
                    self.send_binary_message(0x02, struct.pack('<B', 0))
                    logging.info("Calibration cancelled by user")
                    self.cleanup_calibration()
                delattr(self, 'calibration_dialog_shown')
        elif "Calibration completed" in message:
            self.calibration_timer.stop()
            QMessageBox.information(self, 'Calibration', 'Calibration completed successfully.')
            self.cleanup_calibration()

    def cleanup_calibration(self):
        self.serial_thread.message_received.disconnect(self.handle_calibration_message)
        if self.calibration_timer.isActive():
            self.calibration_timer.stop()
        if hasattr(self, 'calibration_dialog_shown'):
            delattr(self, 'calibration_dialog_shown')

    def calibration_timeout(self, sensor_type):
        logging.warning(f"Calibration for sensor {sensor_type} timed out")
        QMessageBox.warning(self, 'Calibration', 'Calibration timed out. Please try again.')
        self.cleanup_calibration()

    def calibration_completion_timeout(self):
        logging.warning("Calibration completion timed out")
        QMessageBox.warning(self, 'Calibration', 'Calibration completion timed out. Please check the sensor and try again.')
        self.cleanup_calibration()

    def send_settings(self) -> None:
        # Send the updated settings to the Arduino (polling rate and pulses per revolution)
        if not self.serial_connection:
            logging.error("Attempted to send settings without an active connection")
            QMessageBox.warning(self, "Connection Error", "Please connect to the Arduino before sending settings.")
            return

        try:
            # Get the polling rate and pulses per revolution values from the spinboxes and validate them
            polling_rate = self.polling_rate_spinbox.value()
            pulses_per_rev = self.ppr_spinbox.value()
            # Validate the settings values before sending
            if not (1 <= polling_rate <= 1000):
                raise ValueError(f"Invalid polling rate: {polling_rate}. Must be between 1 and 1000 Hz.")
            # Validate the pulses per revolution value before sending
            if not (1 <= pulses_per_rev <= 10):
                raise ValueError(f"Invalid pulses per revolution: {pulses_per_rev}. Must be between 1 and 10.")
            # Save the settings to QSettings before sending
            self.settings.setValue("polling_rate", polling_rate)
            self.settings.setValue("pulses_per_rev", pulses_per_rev)
            self.send_binary_message(0x07, struct.pack('<HB', polling_rate, pulses_per_rev))
            # Print a message to the console and log the settings update
            logging.info(f"Sent settings update: Polling rate {polling_rate} Hz, Pulses per rev {pulses_per_rev}")
        except ValueError as e:
            logging.error(f"Invalid settings value: {e}")
            QMessageBox.warning(self, "Invalid Settings", str(e))
        except struct.error as e:
            logging.error(f"Error packing settings data: {e}")
            QMessageBox.critical(self, "Error", "Failed to prepare settings data for transmission.")
        except Exception as e:
            logging.exception("Unexpected error while sending settings")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def wait_for_calibration_message(self, expected_content, timeout=45) -> bool:
        # Wait for a specific message from the Arduino during the calibration process
        start_time = time.time()
        # Loop until the timeout is reached or the expected message is received
        while time.time() - start_time < timeout:
            if self.message_queue:
                # Check if the expected message is in the queue and return True if found
                message = self.message_queue.popleft()
                if expected_content.lower() in message.lower():
                    return True
            # Wait a short time before checking again
            time.sleep(0.1)
        return False

    def set_polling_frequency(self, frequency: int) -> None:
        # Set the polling frequency for the Arduino to update the data
        # Check if connected before setting the polling frequency value
        if self.serial_connection:
            command = struct.pack('<I', frequency)
            # Send the polling frequency command to the Arduino (prefix, message type, message length, payload, CRC)
            self.send_binary_message(0x04, command)
            print(f"Set polling frequency to {frequency} Hz")

    def send_binary_message(self, message_type: int, payload: bytes) -> None:
        """
        Send a binary message to the Arduino.

        Args:
            message_type (int): The type of message being sent.
            payload (bytes): The message payload.

        Raises:
            serial.SerialException: If there's an error writing to the serial port.
        """        
        # Send a binary message to the Arduino
        if not self.serial_connection:
            logging.error("Attempted to send message without an active connection")
            QMessageBox.warning(self, "Not Connected", "Please connect to the Arduino before sending settings.")
            return
        # Construct the message with prefix, message type, payload length, payload, and CRC
        try:
            prefix = 0xFF
            message_length = len(payload)
            crc = self.crc_func(payload)
            # Construct the message and send it over the serial connection (prefix, message type, message length, payload, CRC)
            message = struct.pack('<BBI', prefix, message_type, message_length) + payload + struct.pack('<H', crc)
            self.serial_connection.write(message)
        except struct.error as e:
            logging.error(f"Error packing message data: {e}")
            QMessageBox.critical(self, "Error", "Failed to prepare message for transmission.")
        except serial.SerialException as e:
            logging.error(f"Serial communication error: {e}")
            QMessageBox.critical(self, "Communication Error", "Failed to send message to Arduino. Check your connection.")
        except Exception as e:
            logging.exception("Unexpected error while sending message")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    # Send an emergency stop command to the Arduino to stop the motor and set the throttle to 0
    def emergency_stop(self) -> None:
        if self.serial_connection:
            self.throttle_value.setText("0")
            self.set_throttle()
            print("Sent emergency stop command")
        else:
            print("Not connected to Arduino")

    # Set the throttle value for the motor (0-100%) using the throttle control
    def set_throttle(self) -> None:
        """
        Set the throttle value for the motor based on user input.
        This method is called when the user inputs a new throttle value in the UI.
        """
        if self.serial_connection:
            throttle = self.throttle_value.text()
            try:
                self.set_throttle_value(int(throttle))
            except ValueError:
                print("Please enter a valid throttle value (0-100)")
        else:
            print("Not connected to Arduino")

    def set_throttle_value(self, value: int) -> None:
        """
        Set the throttle value for the motor.
        This method can be called programmatically or from set_throttle.
        """
        if not self.serial_connection:
            print("Not connected to Arduino")
            return

        try:
            throttle = int(value)
            if 0 <= throttle <= 100:
                self.current_throttle = throttle
                self.send_binary_message(0x05, struct.pack('<B', self.current_throttle))
                print(f"Sent throttle command: {self.current_throttle}%")
                self.throttle_label.setText(f"Throttle: {self.current_throttle}%")
                self.throttle_value.setText(str(self.current_throttle))  # Update the input field
            else:
                raise ValueError("Throttle value must be between 0 and 100")
        except ValueError as e:
            print(f"Invalid throttle value: {e}")

    def open_data_file(self) -> None:
        # Open a file dialog to choose a CSV file with sensor data to load
        try:
            filename, _ = QFileDialog.getOpenFileName(self, "Open Data File", "", "CSV Files (*.csv)")
            if not filename:
                return  # User cancelled the operation
            # Load the data from the selected CSV file and update the plot
            self.data = np.genfromtxt(filename, delimiter=',', skip_header=1, 
                                      dtype=[('Timestamp', 'datetime64[ns]'), 
                                             ('ElapsedTime', 'float64'),
                                             ('Thrust', 'float64'), 
                                             ('Torque', 'float64'), 
                                             ('RPM', 'float64'),
                                             ('Voltage', 'float64'),
                                             ('Current', 'float64'),
                                             ('Throttle', 'int32')])
            self.update_plot()
            logging.info(f"Data loaded from {filename}")
        except ValueError as e:
            # Display a warning if the file format is incorrect or data is missing
            logging.error(f"Error parsing CSV file: {e}")
            QMessageBox.critical(self, "File Error", "The selected file is not in the expected format.")
        except IOError as e:
            logging.error(f"Error reading file: {e}")
            QMessageBox.critical(self, "File Error", f"Could not read the file: {e}")
        except Exception as e:
            logging.exception("Unexpected error while opening data file")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    # Save the COM port and baudrate settings to QSettings for future use
    def save_settings(self) -> None:
        """
        Save the current settings to QSettings for future use.

        This method saves the COM port, baudrate, polling rate, and pulses per revolution settings.
        """
        self.settings.setValue("com_port", self.port_combo.currentText())
        self.settings.setValue("baudrate", self.baudrate_combo.currentText())
        self.settings.setValue("polling_rate", self.polling_rate_spinbox.value())
        self.settings.setValue("pulses_per_rev", self.ppr_spinbox.value())

    def load_settings(self) -> None:
        """
        Load settings from QSettings and update the UI accordingly.

        This method loads the COM port, baudrate, polling rate, and pulses per revolution settings.
        """
        com_port = self.settings.value("com_port", "")
        baudrate = self.settings.value("baudrate", "115200")
        polling_rate = self.settings.value("polling_rate", 100, type=int)
        pulses_per_rev = self.settings.value("pulses_per_rev", 1, type=int)
        
        if com_port in self.get_available_ports():
            self.port_combo.setCurrentText(com_port)
        
        if baudrate in BAUDRATES:
            self.baudrate_combo.setCurrentText(baudrate)
        
        self.polling_rate_spinbox.setValue(polling_rate)
        self.ppr_spinbox.setValue(pulses_per_rev)

def main():
    """
    Main entry point of the application.

    Sets up the QApplication, creates the main window, and starts the event loop.
    """
    app = QApplication(sys.argv)
    window = ArduinoDataLogger()
    window.show()
    window.post_init()
    sys.exit(app.exec_())

# Close the serial connection and stop the serial thread when the window is closed
if __name__ == '__main__':
    main()
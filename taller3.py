#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import shutil
import subprocess
import smtplib
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from fpdf import FPDF
import qrcode
import webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, 
                             QTableWidget, QTableWidgetItem, QTabWidget, QMessageBox,
                             QFileDialog, QDialog, QFormLayout, QDoubleSpinBox, QGridLayout,
                             QScrollArea, QDateEdit, QGroupBox)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QIcon, QPixmap, QImageReader

# Configuración de directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
CLIENTS_FILE = os.path.join(DATABASE_DIR, "clientes.json")
DEVICES_FILE = os.path.join(DATABASE_DIR, "equipos.json")
IMAGES_DIR = os.path.join(DATABASE_DIR, "images")
OUTPUT_DIR = os.path.join(BASE_DIR, "recibos")
FACTURAS_DIR = os.path.join(BASE_DIR, "facturas")
BACKUP_DIR = os.path.join(BASE_DIR, "backup")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

# Crear directorios si no existen
os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FACTURAS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# Configuración de email
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'turepairshop@gmail.com',
    'password': 'tucontraseña'
}

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CONTROL DE REPARACIONES', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acerca del Sistema")
        self.setWindowIcon(QIcon(LOGO_PATH))
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Sistema de Control de Taller</h2>"))
        layout.addWidget(QLabel("Desarrollado por MasterSv"))
        layout.addWidget(QLabel("Versión: 2.0"))
        layout.addWidget(QLabel("<br><b>Donaciones:</b>"))
        layout.addWidget(QLabel("BTC: 35qS9dKvT2qZh7ALnZfWp8vJyF7Q3JXNi"))
        layout.addWidget(QLabel("PayPal: linuxsv.os@gmail.com"))
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class ImagePreviewDialog(QDialog):
    def __init__(self, image_paths):
        super().__init__()
        self.setWindowTitle("Vista Previa de Imágenes")
        self.setWindowIcon(QIcon(LOGO_PATH))
        self.setMinimumSize(800, 600)
        
        scroll = QScrollArea()
        widget = QWidget()
        layout = QGridLayout(widget)
        
        for i, path in enumerate(image_paths):
            lbl = QLabel()
            pixmap = QPixmap(path).scaled(400, 300, Qt.KeepAspectRatio)
            lbl.setPixmap(pixmap)
            layout.addWidget(lbl, i//3, i%3)
        
        scroll.setWidget(widget)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control de Reparaciones")
        self.setWindowIcon(QIcon(LOGO_PATH))
        self.resize(960, 640)
        self.image_paths = []
        
        # Inicializar archivos JSON si no existen
        self.initialize_json_files()
        
        self.setup_ui()
        self.create_menu()
    
    def initialize_json_files(self):
        """Crea los archivos JSON si no existen con estructura inicial"""
        if not os.path.exists(CLIENTS_FILE):
            with open(CLIENTS_FILE, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(DEVICES_FILE):
            with open(DEVICES_FILE, 'w') as f:
                json.dump([], f)
    
    def setup_ui(self):
        self.tabs = QTabWidget()
        
        # Pestañas
        self.client_tab = QWidget()
        self.device_tab = QWidget()
        self.receipt_tab = QWidget()
        self.reports_tab = QWidget()
        self.delivery_tab = QWidget()
        
        self.tabs.addTab(self.client_tab, "Clientes")
        self.tabs.addTab(self.device_tab, "Equipos")
        self.tabs.addTab(self.receipt_tab, "Recibos")
        self.tabs.addTab(self.reports_tab, "Reportes")
        self.tabs.addTab(self.delivery_tab, "Entregas")
        
        self.setup_client_tab()
        self.setup_device_tab()
        self.setup_receipt_tab()
        self.setup_reports_tab()
        self.setup_delivery_tab()
        
        self.setCentralWidget(self.tabs)
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # Menú Archivo
        file_menu = menubar.addMenu("Archivo")
        backup_action = file_menu.addAction("Crear Backup")
        backup_action.triggered.connect(self.create_backup)
        restore_action = file_menu.addAction("Restaurar Backup")
        restore_action.triggered.connect(self.restore_backup)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("Ayuda")
        about_action = help_menu.addAction("Acerca de")
        about_action.triggered.connect(self.show_about)
    
    def setup_client_tab(self):
        layout = QVBoxLayout()
        
        # Formulario de cliente
        form_layout = QFormLayout()
        self.client_name = QLineEdit()
        self.client_phone = QLineEdit()
        self.client_email = QLineEdit()
        self.client_address = QTextEdit()
        self.client_nit = QLineEdit()
        
        form_layout.addRow("Nombre:", self.client_name)
        form_layout.addRow("Teléfono:", self.client_phone)
        form_layout.addRow("Email:", self.client_email)
        form_layout.addRow("Dirección:", self.client_address)
        form_layout.addRow("NIT/CI:", self.client_nit)
        
        # Botones
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Agregar Cliente")
        add_btn.clicked.connect(self.add_client)
        clear_btn = QPushButton("Limpiar")
        clear_btn.clicked.connect(self.clear_client_form)
        delete_btn = QPushButton("Eliminar Cliente")
        delete_btn.clicked.connect(self.delete_client)
        delete_btn.setStyleSheet("background-color: #ff6666; color: white;")
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(delete_btn)
        
        # Tabla de clientes
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(6)
        self.client_table.setHorizontalHeaderLabels(["ID", "Nombre", "Teléfono", "Email", "NIT/CI", "Saldo"])
        self.client_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.client_table.doubleClicked.connect(self.load_client_data)
        
        self.update_client_table()
        
        # Añadir widgets al layout
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(QLabel("Lista de Clientes:"))
        layout.addWidget(self.client_table)
        
        self.client_tab.setLayout(layout)
    
    def setup_device_tab(self):
        layout = QVBoxLayout()
        
        # Formulario de equipo
        form_layout = QFormLayout()
        self.device_client = QComboBox()
        self.update_client_combo()
        
        self.device_type = QComboBox()
        self.device_type.addItems(["Smartphone", "iPhone", "Tablet", "Computadora"])
        
        self.device_brand = QLineEdit()
        self.device_model = QLineEdit()
        self.device_serial = QLineEdit()
        self.device_issues = QTextEdit()
        self.device_cost = QDoubleSpinBox()
        self.device_cost.setRange(0, 9999)
        self.device_cost.setPrefix("$ ")
        self.device_advance = QDoubleSpinBox()
        self.device_advance.setRange(0, 9999)
        self.device_advance.setPrefix("$ ")
        
        # Sección para imágenes
        self.image_preview_layout = QHBoxLayout()
        btn_add_images = QPushButton("Agregar Imágenes (Máx 3)")
        btn_add_images.clicked.connect(self.load_images)
        btn_view_images = QPushButton("Ver Imágenes")
        btn_view_images.clicked.connect(self.show_image_preview)
        
        form_layout.addRow("Cliente:", self.device_client)
        form_layout.addRow("Tipo:", self.device_type)
        form_layout.addRow("Marca:", self.device_brand)
        form_layout.addRow("Modelo:", self.device_model)
        form_layout.addRow("N° Serie:", self.device_serial)
        form_layout.addRow("Problemas:", self.device_issues)
        form_layout.addRow("Costo:", self.device_cost)
        form_layout.addRow("Anticipo:", self.device_advance)
        form_layout.addRow(btn_add_images)
        form_layout.addRow(btn_view_images)
        form_layout.addRow("Vista Previa:", self.image_preview_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Recibir Equipo")
        add_btn.clicked.connect(self.add_device)
        clear_btn = QPushButton("Limpiar")
        clear_btn.clicked.connect(self.clear_device_form)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)
        
        # Tabla de equipos
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(9)
        self.device_table.setHorizontalHeaderLabels(["ID", "Cliente", "Tipo", "Marca", "Modelo", "Problemas", "Costo", "Estado", "Imágenes"])
        self.device_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.device_table.doubleClicked.connect(self.load_device_data)
        
        self.update_device_table()
        
        # Añadir widgets al layout
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(QLabel("Lista de Equipos:"))
        layout.addWidget(self.device_table)
        
        self.device_tab.setLayout(layout)
    
    def setup_receipt_tab(self):
        layout = QVBoxLayout()
        
        # Selección de equipo
        form_layout = QFormLayout()
        self.receipt_device = QComboBox()
        self.update_receipt_combo()
        
        form_layout.addRow("Equipo:", self.receipt_device)
        
        # Botones
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("Generar Recibo (PDF)")
        generate_btn.clicked.connect(self.generate_receipt)
        email_btn = QPushButton("Enviar por Email")
        email_btn.clicked.connect(self.send_receipt_email)
        whatsapp_btn = QPushButton("Enviar por WhatsApp")
        whatsapp_btn.clicked.connect(self.send_receipt_whatsapp)
        
        btn_layout.addWidget(generate_btn)
        btn_layout.addWidget(email_btn)
        btn_layout.addWidget(whatsapp_btn)
        
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        self.receipt_tab.setLayout(layout)
    
    def setup_reports_tab(self):
        layout = QVBoxLayout()
        
        # Filtros de fecha
        date_group = QGroupBox("Filtrar por fecha")
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        
        date_layout.addWidget(QLabel("Desde:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("Hasta:"))
        date_layout.addWidget(self.end_date)
        date_group.setLayout(date_layout)
        
        # Botones de reportes
        btn_layout = QHBoxLayout()
        daily_btn = QPushButton("Reporte Diario")
        daily_btn.clicked.connect(lambda: self.generate_report("diario"))
        weekly_btn = QPushButton("Reporte Semanal")
        weekly_btn.clicked.connect(lambda: self.generate_report("semanal"))
        monthly_btn = QPushButton("Reporte Mensual")
        monthly_btn.clicked.connect(lambda: self.generate_report("mensual"))
        custom_btn = QPushButton("Reporte Personalizado")
        custom_btn.clicked.connect(lambda: self.generate_report("personalizado"))
        
        btn_layout.addWidget(daily_btn)
        btn_layout.addWidget(weekly_btn)
        btn_layout.addWidget(monthly_btn)
        btn_layout.addWidget(custom_btn)
        
        # Área de reporte
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        
        # Botón para exportar a PDF
        export_btn = QPushButton("Exportar Reporte a PDF")
        export_btn.clicked.connect(self.export_report_to_pdf)
        
        # Añadir widgets al layout
        layout.addWidget(date_group)
        layout.addLayout(btn_layout)
        layout.addWidget(self.report_text)
        layout.addWidget(export_btn)
        
        self.reports_tab.setLayout(layout)
    
    def setup_delivery_tab(self):
        layout = QVBoxLayout()
        
        # Selección de equipo
        form_layout = QFormLayout()
        self.delivery_device = QComboBox()
        self.update_delivery_combo()
        
        form_layout.addRow("Equipo para entregar:", self.delivery_device)
        
        # Botón de entrega
        deliver_btn = QPushButton("Entregar Equipo y Generar Factura")
        deliver_btn.clicked.connect(self.deliver_device)
        
        layout.addLayout(form_layout)
        layout.addWidget(deliver_btn)
        self.delivery_tab.setLayout(layout)
    
    def clear_client_form(self):
        """Limpia el formulario de cliente"""
        self.client_name.clear()
        self.client_phone.clear()
        self.client_email.clear()
        self.client_address.clear()
        self.client_nit.clear()
    
    def clear_device_form(self):
        """Limpia el formulario de equipo"""
        self.device_brand.clear()
        self.device_model.clear()
        self.device_serial.clear()
        self.device_issues.clear()
        self.device_cost.setValue(0)
        self.device_advance.setValue(0)
        self.image_paths = []
        
        # Limpiar vista previa de imágenes
        for i in reversed(range(self.image_preview_layout.count())): 
            self.image_preview_layout.itemAt(i).widget().setParent(None)
    
    def load_clients(self):
        """Carga los clientes desde el archivo JSON con estructura validada"""
        try:
            with open(CLIENTS_FILE, 'r') as f:
                clients = json.load(f)
                
                # Validar estructura de cada cliente
                valid_clients = []
                for client in clients:
                    if isinstance(client, dict):
                        # Asegurar que tenga los campos mínimos requeridos
                        valid_client = {
                            'id': client.get('id', 0),
                            'name': client.get('name', ''),
                            'phone': client.get('phone', ''),
                            'email': client.get('email', ''),
                            'address': client.get('address', ''),
                            'nit': client.get('nit', ''),
                            'balance': client.get('balance', 0)
                        }
                        valid_clients.append(valid_client)
                
                return valid_clients
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def load_devices(self):
        """Carga los equipos desde el archivo JSON con estructura validada"""
        try:
            with open(DEVICES_FILE, 'r') as f:
                devices = json.load(f)
                
                # Validar estructura de cada equipo
                valid_devices = []
                for device in devices:
                    if isinstance(device, dict):
                        # Asegurar que tenga los campos mínimos requeridos
                        valid_device = {
                            'id': device.get('id', 0),
                            'client_id': device.get('client_id', 0),
                            'client_name': device.get('client_name', ''),
                            'type': device.get('type', ''),
                            'brand': device.get('brand', ''),
                            'model': device.get('model', ''),
                            'serial': device.get('serial', ''),
                            'issues': device.get('issues', ''),
                            'cost': device.get('cost', 0),
                            'advance': device.get('advance', 0),
                            'status': device.get('status', 'En reparación'),
                            'date_received': device.get('date_received', ''),
                            'date_delivered': device.get('date_delivered', ''),
                            'images': device.get('images', []),
                            'factura_num': device.get('factura_num', 0)
                        }
                        valid_devices.append(valid_device)
                
                return valid_devices
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def update_client_table(self):
        """Actualiza la tabla de clientes con los datos actuales"""
        clients = self.load_clients()
        self.client_table.setRowCount(len(clients))
        
        for row, client in enumerate(clients):
            self.client_table.setItem(row, 0, QTableWidgetItem(str(client['id'])))
            self.client_table.setItem(row, 1, QTableWidgetItem(client['name']))
            self.client_table.setItem(row, 2, QTableWidgetItem(client['phone']))
            self.client_table.setItem(row, 3, QTableWidgetItem(client['email']))
            self.client_table.setItem(row, 4, QTableWidgetItem(client['nit']))
            self.client_table.setItem(row, 5, QTableWidgetItem(str(client['balance'])))
    
    def update_device_table(self):
        """Actualiza la tabla de equipos con los datos actuales"""
        devices = self.load_devices()
        self.device_table.setRowCount(len(devices))
        
        for row, device in enumerate(devices):
            self.device_table.setItem(row, 0, QTableWidgetItem(str(device['id'])))
            self.device_table.setItem(row, 1, QTableWidgetItem(device['client_name']))
            self.device_table.setItem(row, 2, QTableWidgetItem(device['type']))
            self.device_table.setItem(row, 3, QTableWidgetItem(device['brand']))
            self.device_table.setItem(row, 4, QTableWidgetItem(device['model']))
            self.device_table.setItem(row, 5, QTableWidgetItem(device['issues']))
            self.device_table.setItem(row, 6, QTableWidgetItem(str(device['cost'])))
            self.device_table.setItem(row, 7, QTableWidgetItem(device['status']))
            self.device_table.setItem(row, 8, QTableWidgetItem(str(len(device['images']))))
    
    def update_client_combo(self):
        """Actualiza el combo box de clientes con validación"""
        self.device_client.clear()
        clients = self.load_clients()
        
        for client in clients:
            # Asegurarse de que el cliente tiene nombre e ID
            if 'name' in client and 'id' in client:
                self.device_client.addItem(client['name'], client['id'])
            else:
                print(f"Cliente inválido omitido: {client}")
    
    def update_receipt_combo(self):
        """Actualiza el combo box de equipos para recibos"""
        self.receipt_device.clear()
        devices = self.load_devices()
        
        for device in devices:
            if all(key in device for key in ['id', 'client_name', 'type']):
                self.receipt_device.addItem(
                    f"{device['id']} - {device['client_name']} - {device['type']}", 
                    device['id']
                )
    
    def update_delivery_combo(self):
        """Actualiza el combo box de equipos para entregas"""
        self.delivery_device.clear()
        devices = self.load_devices()
        
        for device in devices:
            if 'status' in device and device['status'] == 'En reparación':
                if all(key in device for key in ['id', 'client_name', 'type']):
                    self.delivery_device.addItem(
                        f"{device['id']} - {device['client_name']} - {device['type']}", 
                        device['id']
                    )
    
    def load_client_data(self, index):
        """Carga los datos del cliente seleccionado en la tabla"""
        row = index.row()
        clients = self.load_clients()
        
        if row < len(clients):
            client = clients[row]
            self.client_name.setText(client['name'])
            self.client_phone.setText(client['phone'])
            self.client_email.setText(client['email'])
            self.client_address.setPlainText(client['address'])
            self.client_nit.setText(client['nit'])
    
    def load_device_data(self, index):
        """Carga los datos del equipo seleccionado en la tabla"""
        row = index.row()
        devices = self.load_devices()
        
        if row < len(devices):
            device = devices[row]
            
            # Buscar el cliente correspondiente
            clients = self.load_clients()
            client = next((c for c in clients if c['id'] == device['client_id']), None)
            
            if client:
                self.device_client.setCurrentText(client['name'])
            
            self.device_type.setCurrentText(device['type'])
            self.device_brand.setText(device['brand'])
            self.device_model.setText(device['model'])
            self.device_serial.setText(device['serial'])
            self.device_issues.setPlainText(device['issues'])
            self.device_cost.setValue(device['cost'])
            self.device_advance.setValue(device['advance'])
            
            # Cargar imágenes si existen
            self.image_paths = device['images']
            self.update_image_preview()
    
    def load_images(self):
        """Carga imágenes del equipo"""
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar imágenes", "", 
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos los archivos (*)", 
            options=options)
        
        if files:
            self.image_paths = files[:3]  # Limitar a 3 imágenes
            self.update_image_preview()
    
    def update_image_preview(self):
        """Actualiza la vista previa de imágenes"""
        # Limpiar layout primero
        for i in reversed(range(self.image_preview_layout.count())): 
            self.image_preview_layout.itemAt(i).widget().setParent(None)
        
        # Mostrar miniaturas
        for path in self.image_paths[:3]:  # Mostrar máximo 3 imágenes
            lbl = QLabel()
            pixmap = QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio)
            lbl.setPixmap(pixmap)
            self.image_preview_layout.addWidget(lbl)
    
    def show_image_preview(self):
        """Muestra un diálogo con vista previa ampliada de las imágenes"""
        if not self.image_paths:
            QMessageBox.warning(self, "Advertencia", "No hay imágenes para mostrar")
            return
        
        dialog = ImagePreviewDialog(self.image_paths)
        dialog.exec_()
    
    def add_client(self):
        """Agrega un nuevo cliente a la base de datos con validación"""
        name = self.client_name.text().strip()
        phone = self.client_phone.text().strip()
        email = self.client_email.text().strip()
        address = self.client_address.toPlainText().strip()
        nit = self.client_nit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "El nombre del cliente es obligatorio")
            return
        
        clients = self.load_clients()
        
        # Generar ID único
        new_id = max([c.get('id', 0) for c in clients], default=0) + 1
        
        # Crear cliente con estructura completa
        new_client = {
            'id': new_id,
            'name': name,
            'phone': phone,
            'email': email,
            'address': address,
            'nit': nit,
            'balance': 0.0  # Inicializar saldo
        }
        
        clients.append(new_client)
        
        try:
            with open(CLIENTS_FILE, 'w') as f:
                json.dump(clients, f, indent=4)
            
            self.update_client_table()
            self.update_client_combo()
            self.clear_client_form()
            QMessageBox.information(self, "Éxito", "Cliente agregado correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el cliente: {str(e)}")
    
    def delete_client(self):
        """Elimina el cliente seleccionado"""
        selected_row = self.client_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Advertencia", "Seleccione un cliente para eliminar")
            return
        
        client_id = int(self.client_table.item(selected_row, 0).text())
        
        # Verificar si el cliente tiene equipos asociados
        devices = self.load_devices()
        client_devices = [d for d in devices if d.get('client_id') == client_id]
        
        if client_devices:
            QMessageBox.warning(self, "Error", 
                              "No se puede eliminar el cliente porque tiene equipos registrados. "
                              "Primero elimine o transfiera los equipos.")
            return
        
        # Confirmar eliminación
        reply = QMessageBox.question(
            self, 'Confirmar',
            '¿Está seguro que desea eliminar este cliente?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            clients = self.load_clients()
            clients = [c for c in clients if c.get('id') != client_id]
            
            try:
                with open(CLIENTS_FILE, 'w') as f:
                    json.dump(clients, f, indent=4)
                
                self.update_client_table()
                self.update_client_combo()
                self.clear_client_form()
                QMessageBox.information(self, "Éxito", "Cliente eliminado correctamente")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el cliente: {str(e)}")
    
    def add_device(self):
        """Agrega un nuevo equipo a la base de datos con validación"""
        client_id = self.device_client.currentData()
        device_type = self.device_type.currentText()
        brand = self.device_brand.text().strip()
        model = self.device_model.text().strip()
        serial = self.device_serial.text().strip()
        issues = self.device_issues.toPlainText().strip()
        cost = self.device_cost.value()
        advance = self.device_advance.value()
        
        if not client_id:
            QMessageBox.warning(self, "Error", "Seleccione un cliente")
            return
        
        if not brand or not model:
            QMessageBox.warning(self, "Error", "Marca y modelo son obligatorios")
            return
        
        devices = self.load_devices()
        clients = self.load_clients()
        
        # Obtener nombre del cliente
        client = next((c for c in clients if c['id'] == client_id), None)
        if not client:
            QMessageBox.warning(self, "Error", "Cliente no encontrado")
            return
        
        # Generar ID único
        new_id = max([d.get('id', 0) for d in devices], default=0) + 1
        
        # Guardar imágenes en directorio
        saved_images = []
        for i, img_path in enumerate(self.image_paths[:3]):  # Máximo 3 imágenes
            if os.path.exists(img_path):
                ext = os.path.splitext(img_path)[1]
                new_path = os.path.join(IMAGES_DIR, f"device_{new_id}_{i}{ext}")
                shutil.copy(img_path, new_path)
                saved_images.append(new_path)
        
        # Crear dispositivo con estructura completa
        new_device = {
            'id': new_id,
            'client_id': client_id,
            'client_name': client['name'],
            'type': device_type,
            'brand': brand,
            'model': model,
            'serial': serial,
            'issues': issues,
            'cost': float(cost),
            'advance': float(advance),
            'status': "En reparación",
            'date_received': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date_delivered': "",
            'images': saved_images,
            'factura_num': 0
        }
        
        try:
            with open(DEVICES_FILE, 'w') as f:
                devices.append(new_device)
                json.dump(devices, f, indent=4)
            
            # Actualizar saldo del cliente
            client['balance'] = client.get('balance', 0) + (cost - advance)
            with open(CLIENTS_FILE, 'w') as f:
                json.dump(clients, f, indent=4)
            
            self.update_device_table()
            self.update_receipt_combo()
            self.update_delivery_combo()
            self.clear_device_form()
            QMessageBox.information(self, "Éxito", "Equipo agregado correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el equipo: {str(e)}")
    
    def generate_receipt(self):
        """Genera un recibo PDF para el equipo seleccionado con mejor formato"""
        try:
            device_id = self.receipt_device.currentData()
            if not device_id:
                QMessageBox.warning(self, "Error", "Seleccione un equipo primero")
                return
            
            devices = self.load_devices()
            device = next((d for d in devices if d['id'] == device_id), None)
            
            if not device:
                QMessageBox.warning(self, "Error", "Equipo no encontrado")
                return

            clients = self.load_clients()
            client = next((c for c in clients if c['id'] == device['client_id']), None)
            
            if not client:
                QMessageBox.warning(self, "Error", "Cliente no encontrado")
                return

            # Crear PDF con mejor formato
            pdf = PDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Encabezado con logo y datos
            pdf.set_font('Arial', 'B', 16)
            
            # Logo a la izquierda
            if os.path.exists(LOGO_PATH):
                try:
                    pdf.image(LOGO_PATH, x=10, y=8, w=30)
                except Exception as e:
                    print(f"Error al cargar logo: {str(e)}")
            
            # Título centrado
            pdf.cell(0, 10, "RECIBO DE REPARACIÓN", 0, 1, 'C')
            
            # QR a la derecha
            try:
                qr_data = f"https://pay.link.com/?amount={device['cost'] - device['advance']}"
                img = qrcode.make(qr_data)
                qr_temp_path = os.path.join(BASE_DIR, "qr_temp.png")
                img.save(qr_temp_path)
                pdf.image(qr_temp_path, x=160, y=10, w=30)
                os.remove(qr_temp_path)
            except Exception as e:
                print(f"Error generando QR: {str(e)}")
            
            pdf.ln(20)  # Espacio después del encabezado
            
            # Información del cliente
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Cliente:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, client['name'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Teléfono:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, client['phone'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Fecha:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, datetime.now().strftime("%d/%m/%Y %H:%M"), 0, 1)
            
            pdf.ln(10)
            
            # Detalles del equipo
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Detalles del Equipo", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Tipo:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, device['type'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Marca:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, device['brand'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Modelo:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, device['model'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "N° Serie:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, device['serial'], 0, 1)
            
            pdf.ln(5)
            
            # Problemas reportados
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, "Problemas reportados:", 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.multi_cell(0, 10, device['issues'])
            
            pdf.ln(10)
            
            # Resumen financiero
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Resumen Financiero", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(100, 10, "Concepto", 1)
            pdf.cell(0, 10, "Monto", 1, 1)
            
            pdf.set_font('Arial', '', 12)
            pdf.cell(100, 10, "Costo total de reparación", 1)
            pdf.cell(0, 10, f"${device['cost']:.2f}", 1, 1)
            
            pdf.cell(100, 10, "Anticipo recibido", 1)
            pdf.cell(0, 10, f"${device['advance']:.2f}", 1, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(100, 10, "Saldo pendiente", 1)
            pdf.cell(0, 10, f"${device['cost'] - device['advance']:.2f}", 1, 1)
            
            pdf.ln(15)
            
            # Notas
            pdf.set_font('Arial', 'I', 10)
            pdf.multi_cell(0, 10, "Nota: Este recibo es válido como comprobante de entrega del equipo. "
                                "El pago pendiente debe ser cancelado al retirar el equipo.")
            
            # Guardar PDF
            output_path = os.path.join(OUTPUT_DIR, f"Recibo_{device_id}.pdf")
            pdf.output(output_path)
            
            QMessageBox.information(self, "Éxito", f"Recibo generado en: {output_path}")
            webbrowser.open(output_path)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar recibo: {str(e)}")
    
    def deliver_device(self):
        """Marca un equipo como entregado y genera factura con numeración automática y QR"""
        device_id = self.delivery_device.currentData()
        if not device_id:
            QMessageBox.warning(self, "Error", "Seleccione un equipo primero")
            return
        
        devices = self.load_devices()
        device = next((d for d in devices if d['id'] == device_id), None)
        
        if not device:
            QMessageBox.warning(self, "Error", "Equipo no encontrado")
            return
        
        clients = self.load_clients()
        client = next((c for c in clients if c['id'] == device['client_id']), None)
        
        if not client:
            QMessageBox.warning(self, "Error", "Cliente no encontrado")
            return
        
        # Obtener el próximo número de factura
        factura_num = self.get_next_factura_number()
        
        # Actualizar estado del equipo
        device['status'] = "Entregado"
        device['date_delivered'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        device['factura_num'] = factura_num
        
        try:
            with open(DEVICES_FILE, 'w') as f:
                json.dump(devices, f, indent=4)
            
            # Generar factura mejorada
            pdf = PDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Encabezado con logo y número de factura
            if os.path.exists(LOGO_PATH):
                try:
                    pdf.image(LOGO_PATH, x=10, y=8, w=30)
                except Exception as e:
                    print(f"Error al cargar logo: {str(e)}")
            
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, f"FACTURA N° {factura_num}", 0, 1, 'C')
            
            # QR de pago
            try:
                qr_data = f"https://pay.link.com/?amount={device['cost'] - device['advance']}"
                img = qrcode.make(qr_data)
                qr_temp_path = os.path.join(BASE_DIR, "qr_temp.png")
                img.save(qr_temp_path)
                pdf.image(qr_temp_path, x=160, y=10, w=30)
                os.remove(qr_temp_path)
            except Exception as e:
                print(f"Error generando QR: {str(e)}")
            
            pdf.ln(20)
            
            # Información de la factura
            pdf.set_font('Arial', '', 12)
            pdf.cell(40, 10, "Fecha:", 0, 0)
            pdf.cell(0, 10, datetime.now().strftime("%d/%m/%Y %H:%M"), 0, 1)
            
            pdf.ln(10)
            
            # Datos del cliente
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Datos del Cliente", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Nombre:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, client['name'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "NIT/CI:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, client['nit'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Dirección:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, client['address'], 0, 1)
            
            pdf.ln(10)
            
            # Detalles del servicio
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Detalles del Servicio", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Equipo:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f"{device['type']} {device['brand']}", 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Modelo:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, device['model'], 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, "Serie:", 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, device['serial'], 0, 1)
            
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, "Descripción del servicio:", 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.multi_cell(0, 10, device['issues'])
            
            pdf.ln(10)
            
            # Resumen financiero
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Resumen Financiero", 0, 1)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(120, 10, "Concepto", 1)
            pdf.cell(0, 10, "Monto", 1, 1)
            
            pdf.set_font('Arial', '', 12)
            pdf.cell(120, 10, "Reparación de equipo electrónico", 1)
            pdf.cell(0, 10, f"${device['cost']:.2f}", 1, 1)
            
            pdf.cell(120, 10, "Anticipo recibido", 1)
            pdf.cell(0, 10, f"${device['advance']:.2f}", 1, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(120, 10, "Total a pagar", 1)
            pdf.cell(0, 10, f"${device['cost'] - device['advance']:.2f}", 1, 1)
            
            pdf.ln(15)
            
            # Firmas
            pdf.set_font('Arial', '', 10)
            pdf.cell(90, 10, "_________________________", 0, 0, 'C')
            pdf.cell(20, 10, "", 0, 0)
            pdf.cell(90, 10, "_________________________", 0, 1, 'C')
            pdf.cell(90, 5, "Firma del Cliente", 0, 0, 'C')
            pdf.cell(20, 5, "", 0, 0)
            pdf.cell(90, 5, "Firma del Técnico", 0, 1, 'C')
            
            # Guardar factura
            factura_path = os.path.join(FACTURAS_DIR, f"Factura_{factura_num}.pdf")
            pdf.output(factura_path)
            
            # Actualizar combos y tablas
            self.update_delivery_combo()
            self.update_device_table()
            
            QMessageBox.information(self, "Éxito", f"Equipo marcado como entregado. Factura generada en: {factura_path}")
            webbrowser.open(factura_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo completar la entrega: {str(e)}")
    
    def get_next_factura_number(self):
        """Obtiene el próximo número de factura"""
        # Buscar el último número de factura usado
        devices = self.load_devices()
        last_num = 0
        
        for device in devices:
            if 'factura_num' in device and device['factura_num'] > last_num:
                last_num = device['factura_num']
        
        # Si no hay facturas previas, empezar desde un número base
        if last_num == 0:
            last_num = 1000  # Número inicial
        
        return last_num + 1
    
    def generate_report(self, report_type):
        """Genera reportes según el tipo especificado con validación"""
        try:
            devices = self.load_devices()
            
            if report_type == "diario":
                start_date = datetime.now().replace(hour=0, minute=0, second=0)
                end_date = datetime.now().replace(hour=23, minute=59, second=59)
            elif report_type == "semanal":
                start_date = datetime.now() - timedelta(days=datetime.now().weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0)
                end_date = start_date + timedelta(days=6)
                end_date = end_date.replace(hour=23, minute=59, second=59)
            elif report_type == "mensual":
                start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0)
                end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                end_date = end_date.replace(hour=23, minute=59, second=59)
            else:  # personalizado
                start_date = datetime(
                    self.start_date.date().year(),
                    self.start_date.date().month(),
                    self.start_date.date().day(),
                    0, 0, 0
                )
                end_date = datetime(
                    self.end_date.date().year(),
                    self.end_date.date().month(),
                    self.end_date.date().day(),
                    23, 59, 59
                )
            
            # Filtrar dispositivos por fecha
            filtered_devices = []
            for device in devices:
                try:
                    date_received = datetime.strptime(device['date_received'], "%Y-%m-%d %H:%M:%S")
                    if start_date <= date_received <= end_date:
                        filtered_devices.append(device)
                except (KeyError, ValueError):
                    continue
            
            # Generar reporte
            report = f"Reporte de {report_type.capitalize()}\n"
            report += f"Del {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}\n"
            report += "="*50 + "\n\n"
            
            # Resumen
            total_devices = len(filtered_devices)
            delivered = sum(1 for d in filtered_devices if d.get('status') == 'Entregado')
            in_repair = sum(1 for d in filtered_devices if d.get('status') == 'En reparación')
            total_income = sum(d.get('cost', 0) for d in filtered_devices)
            
            report += f"Total de equipos recibidos: {total_devices}\n"
            report += f"Equipos entregados: {delivered}\n"
            report += f"Equipos en reparación: {in_repair}\n"
            report += f"Ingresos totales: ${total_income:.2f}\n\n"
            
            # Detalle por equipo
            report += "Detalle por equipo:\n"
            report += "-"*50 + "\n"
            for device in filtered_devices:
                report += f"ID: {device.get('id', '')} - Cliente: {device.get('client_name', '')}\n"
                report += f"Equipo: {device.get('type', '')} {device.get('brand', '')} {device.get('model', '')}\n"
                report += f"Problema: {device.get('issues', '')[:50]}...\n"
                report += f"Costo: ${device.get('cost', 0):.2f} - Estado: {device.get('status', '')}\n"
                report += f"Fecha recibido: {device.get('date_received', '')}\n"
                if device.get('status') == 'Entregado':
                    report += f"Fecha entregado: {device.get('date_delivered', '')}\n"
                    report += f"N° Factura: {device.get('factura_num', '')}\n"
                report += "-"*50 + "\n"
            
            self.report_text.setPlainText(report)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el reporte: {str(e)}")
    
    def export_report_to_pdf(self):
        """Exporta el reporte actual a PDF"""
        report_text = self.report_text.toPlainText()
        if not report_text.strip():
            QMessageBox.warning(self, "Advertencia", "No hay reporte para exportar")
            return
        
        try:
            pdf = PDF()
            pdf.add_page()
            pdf.set_font('Arial', '', 12)
            
            # Dividir el texto en líneas y agregar al PDF
            for line in report_text.split('\n'):
                pdf.cell(0, 10, line, 0, 1)
            
            # Guardar PDF
            report_path = os.path.join(OUTPUT_DIR, f"Reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf.output(report_path)
            
            QMessageBox.information(self, "Éxito", f"Reporte exportado a: {report_path}")
            webbrowser.open(report_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el reporte: {str(e)}")
    
    def send_receipt_email(self):
        """Envía el recibo por email con validación"""
        device_id = self.receipt_device.currentData()
        if not device_id:
            QMessageBox.warning(self, "Error", "Seleccione un equipo primero")
            return
        
        devices = self.load_devices()
        device = next((d for d in devices if d['id'] == device_id), None)
        
        if not device:
            QMessageBox.warning(self, "Error", "Equipo no encontrado")
            return
        
        # Obtener datos del cliente
        clients = self.load_clients()
        client = next((c for c in clients if c['id'] == device['client_id']), None)
        
        if not client or not client.get('email'):
            QMessageBox.warning(self, "Error", "No hay email del cliente registrado")
            return
        
        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['email']
            msg['To'] = client['email']
            msg['Subject'] = f"Recibo de reparación #{device_id}"
            
            # Cuerpo del mensaje
            body = f"""
            Estimado {client.get('name', 'Cliente')},
            
            Adjunto encontrará el recibo por la reparación de su equipo:
            
            Equipo: {device.get('type', '')} {device.get('brand', '')}
            Modelo: {device.get('model', '')}
            Problema: {device.get('issues', '')}
            Costo total: ${device.get('cost', 0):.2f}
            Anticipo: ${device.get('advance', 0):.2f}
            Saldo pendiente: ${device.get('cost', 0) - device.get('advance', 0):.2f}
            
            Gracias por su preferencia.
            """
            msg.attach(MIMEText(body, 'plain'))
            
            # Adjuntar recibo
            receipt_path = os.path.join(OUTPUT_DIR, f"Recibo_{device_id}.pdf")
            if os.path.exists(receipt_path):
                with open(receipt_path, "rb") as attachment:
                    part = MIMEApplication(attachment.read(), Name=os.path.basename(receipt_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(receipt_path)}"'
                msg.attach(part)
            
            # Enviar email
            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
                server.send_message(msg)
            
            QMessageBox.information(self, "Éxito", "Recibo enviado por email correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo enviar el email: {str(e)}")
    
    def send_receipt_whatsapp(self):
        """Envía el recibo por WhatsApp con validación"""
        device_id = self.receipt_device.currentData()
        if not device_id:
            QMessageBox.warning(self, "Error", "Seleccione un equipo primero")
            return
        
        devices = self.load_devices()
        device = next((d for d in devices if d['id'] == device_id), None)
        
        if not device:
            QMessageBox.warning(self, "Error", "Equipo no encontrado")
            return
        
        # Obtener datos del cliente
        clients = self.load_clients()
        client = next((c for c in clients if c['id'] == device['client_id']), None)
        
        if not client or not client.get('phone'):
            QMessageBox.warning(self, "Error", "No hay teléfono del cliente registrado")
            return
        
        try:
            phone = client['phone'].strip().replace('+', '').replace(' ', '')
            message = f"Estimado {client.get('name', 'Cliente')}, aquí está su recibo de reparación. Gracias por su preferencia."
            whatsapp_url = f"https://wa.me/{phone}?text={message}"
            webbrowser.open(whatsapp_url)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir WhatsApp: {str(e)}")
    
    def create_backup(self):
        """Crea una copia de seguridad de los datos"""
        try:
            import zipfile
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
            
            with zipfile.ZipFile(backup_file, 'w') as zipf:
                for root, dirs, files in os.walk(DATABASE_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, DATABASE_DIR)
                        zipf.write(file_path, arcname)
            
            QMessageBox.information(self, "Éxito", f"Backup creado en: {backup_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear el backup: {str(e)}")
    
    def restore_backup(self):
        """Restaura los datos desde una copia de seguridad"""
        options = QFileDialog.Options()
        backup_file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de backup", 
            BACKUP_DIR, "Zip Files (*.zip)", options=options)
        
        if not backup_file:
            return
        
        try:
            import zipfile
            # Eliminar archivos actuales
            for filename in os.listdir(DATABASE_DIR):
                file_path = os.path.join(DATABASE_DIR, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"No se pudo eliminar {file_path}: {e}")
            
            # Extraer backup
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(DATABASE_DIR)
            
            # Actualizar interfaces
            self.update_client_table()
            self.update_device_table()
            self.update_client_combo()
            self.update_receipt_combo()
            self.update_delivery_combo()
            
            QMessageBox.information(self, "Éxito", "Backup restaurado correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo restaurar el backup: {str(e)}")
    
    def show_about(self):
        """Muestra el diálogo Acerca de"""
        dialog = AboutDialog()
        dialog.exec_()

if __name__ == "__main__":
    # Solucionar conflicto entre PyFPDF y fpdf2
    try:
        import pkg_resources
        pkg_resources.require("fpdf2")
    except:
        pass
    
    app = QApplication(sys.argv)
    
    if not os.path.exists(LOGO_PATH):
        from PIL import Image, ImageDraw
        try:
            img = Image.new('RGB', (100, 100), color=(73, 109, 137))
            d = ImageDraw.Draw(img)
            d.text((10, 40), "CR", fill=(255, 255, 0))
            img.save(LOGO_PATH)
        except ImportError:
            print("Instala Pillow para generar el logo: pip install Pillow")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

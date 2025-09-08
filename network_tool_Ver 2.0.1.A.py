"""
Windows Troubleshoot Tool - Final
Requirements:
  pip install PySide6 speedtest-cli requests

This file contains a single-file PySide6 GUI. It fixes a bug where the app window appeared completely black by ensuring:
 - central widget is set and has a layout
 - all child widgets are added to that layout (no orphan widgets)
 - stylesheets do not hide controls or set identical foreground/background
 - animations are stored as attributes to prevent GC
 - background gradient is drawn but does not block child widgets

Features included: Network (Ping/Tracert/NSLookup), System (refresh/export), Tools (TCP check, Speedtest, Upload, Email dialog).
"""

import sys
import os
import platform
import getpass
import socket
import uuid
import subprocess
import tempfile
import threading
import requests
import smtplib
import ssl
from email.message import EmailMessage
import shutil


from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

# optional WMI
try:
    import wmi
    HAS_WMI = True
except Exception:
    HAS_WMI = False

# ---- Utilities ----

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'Unknown'


def get_mac():
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(40, -8, -8)])
        return mac
    except Exception:
        return 'Unavailable'


def get_serial():
    if HAS_WMI and platform.system().lower().startswith('win'):
        try:
            c = wmi.WMI()
            for s in c.Win32_ComputerSystemProduct():
                return s.IdentifyingNumber or 'Unknown'
        except Exception:
            pass
    if platform.system().lower().startswith('win'):
        try:
            out = subprocess.check_output(['wmic', 'bios', 'get', 'serialnumber'], stderr=subprocess.DEVNULL, text=True)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            return lines[1] if len(lines) > 1 else 'Unknown'
        except Exception:
            return 'Unavailable'
    return 'N/A'

# ---- Worker threads ----
class TcpCheckWorker(QtCore.QThread):
    result = QtCore.Signal(str)

    def __init__(self, host: str, port: int, timeout: float = 3.0):
        super().__init__()
        self.host = host
        self.port = port
        self.timeout = timeout

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.host, int(self.port)))
            s.close()
            self.result.emit(f"{self.host}:{self.port} reachable")
        except Exception as e:
            self.result.emit(f"{self.host}:{self.port} unreachable ({e})")

class UploadWorker(QtCore.QThread):
    finished = QtCore.Signal(bool, str)

    def __init__(self, url: str, filepath: str):
        super().__init__()
        self.url = url
        self.filepath = filepath

    def run(self):
        try:
            with open(self.filepath, 'rb') as f:
                files = {'log': (os.path.basename(self.filepath), f)}
                r = requests.post(self.url, files=files, timeout=15)
            self.finished.emit(True, f"Status {r.status_code}")
        except Exception as e:
            self.finished.emit(False, str(e))

class EmailWorker(QtCore.QThread):
    finished = QtCore.Signal(bool, str)

    def __init__(self, smtp_server, port, sender, password, recipients, subject, body, attachment_path=None):
        super().__init__()
        self.smtp_server = smtp_server
        self.port = port
        self.sender = sender
        self.password = password
        self.recipients = recipients
        self.subject = subject
        self.body = body
        self.attachment_path = attachment_path

    def run(self):
        try:
            msg = EmailMessage()
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = self.subject
            msg.set_content(self.body)
            if self.attachment_path and os.path.exists(self.attachment_path):
                with open(self.attachment_path, 'rb') as f:
                    data = f.read()
                msg.add_attachment(data, maintype='application', subtype='octet-stream',
                                   filename=os.path.basename(self.attachment_path))
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.port, timeout=20) as server:
                server.starttls(context=context)
                server.login(self.sender, self.password)
                server.send_message(msg)
            self.finished.emit(True, "Email sent")
        except Exception as e:
            self.finished.emit(False, str(e))

# ---- UI helpers ----
class ModernButton(QtWidgets.QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._update_style()

    def enterEvent(self, e):
        self._hover = True
        self._update_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._update_style()
        super().leaveEvent(e)

    def _update_style(self):
        base = "#5752a2" if self._hover else "#3f3c6f"
        self.setStyleSheet(f"background:{base}; color:#eaf2ff; padding:6px 12px; border:none; border-radius:6px;")

# ---- Main Window ----
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows Troubleshoot Tool")
        self.resize(980, 640)
        self._build_ui()
        self._fade_in()

    def _build_ui(self):
        # central widget + layout must be set — this fixes 'black window' issues
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        hdr = QtWidgets.QLabel("Windows Troubleshoot Tool")
        hdr.setStyleSheet('font-size:18px; font-weight:600; color:#ffffff;')
        main_layout.addWidget(hdr)

        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setIconSize(QtCore.QSize(18, 18))
        self.tabs.setStyleSheet("""
            QTabBar::tab { background: #2d2a4a; color: #eaf2ff; padding: 6px 12px; border-radius:6px; margin:2px; }
            QTabBar::tab:selected{ background: #3f3c6f; }
            QTabWidget::pane { border: none; background: transparent; }
        """)
        main_layout.addWidget(self.tabs, 1)

        # Build functional tabs
        self._build_network_tab()
        self._build_system_tab()
        self._build_tools_tab()

        # basic app stylesheet (foreground/background contrasts fixed)
        self.setStyleSheet("""
            QWidget{font-family:Segoe UI, Arial; color:#eaf2ff; background: transparent}
            QLineEdit{background:#ffffff; color:#222222; border-radius:6px; padding:6px}
            QPlainTextEdit, QTextEdit{background:#0f1013; color:#eaf2ff; border-radius:6px; padding:8px}
            QPushButton{border-radius:6px}
        """)

    # ---------------- Network Tab ----------------
    def _build_network_tab(self):
        net = QtWidgets.QWidget()
        self.tabs.addTab(net, QtGui.QIcon(), "Network")
        layout = QtWidgets.QVBoxLayout(net)

        top = QtWidgets.QHBoxLayout()
        self.input_target = QtWidgets.QLineEdit()
        self.input_target.setPlaceholderText("Enter IP or domain, e.g. 8.8.8.8")
        self.input_target.setMinimumWidth(380)
        top.addWidget(self.input_target)

        self.btn_ping = ModernButton("Ping")
        self.btn_tracert = ModernButton("Tracert")
        self.btn_ns = ModernButton("NSLookup")
        for b in (self.btn_ping, self.btn_tracert, self.btn_ns):
            b.setFixedHeight(34)
            top.addWidget(b)

        layout.addLayout(top)

        self.net_output = QtWidgets.QPlainTextEdit()
        self.net_output.setReadOnly(True)
        self.net_output.setFont(QtGui.QFont("Consolas", 11))
        layout.addWidget(self.net_output, 1)

        # connects
        self.btn_ping.clicked.connect(lambda: self._run_network_cmd('ping'))
        self.btn_tracert.clicked.connect(lambda: self._run_network_cmd('tracert'))
        self.btn_ns.clicked.connect(lambda: self._run_network_cmd('nslookup'))

        self._net_proc = None

    def _append_net(self, text: str):
        self.net_output.appendPlainText(str(text))
        sb = self.net_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_net_buttons(self, enabled: bool):
        self.btn_ping.setEnabled(enabled)
        self.btn_tracert.setEnabled(enabled)
        self.btn_ns.setEnabled(enabled)

    def _run_network_cmd(self, cmd_name: str):
        target = self.input_target.text().strip()
        if not target:
            self._append_net("Enter a target first.")
            return

        if cmd_name == 'ping':
            program = 'ping'
            args = ['-n', '4', target] if sys.platform.startswith('win') else ['-c', '4', target]
        elif cmd_name == 'tracert':
            program = 'tracert' if sys.platform.startswith('win') else 'traceroute'
            args = [target]
        else:
            program = 'nslookup'
            args = [target]

        if shutil.which(program) is None:
            self._append_net(f"{program} not found on system")
            return

        if self._net_proc:
            try:
                self._net_proc.kill()
            except Exception:
                pass

        proc = QtCore.QProcess(self)
        proc.setProgram(program)
        proc.setArguments(args)
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._append_net(proc.readAllStandardOutput().data().decode(errors='ignore')))
        proc.finished.connect(lambda code, status: self._append_net(f"=== finished (code={code}) ==="))
        proc.started.connect(lambda: self._set_net_buttons(False))
        proc.finished.connect(lambda code, status: self._set_net_buttons(True))
        proc.start()
        self._net_proc = proc
        self._append_net(f"=== {program} {target} started ===")

    # ---------------- System Tab ----------------
    def _build_system_tab(self):
        sysw = QtWidgets.QWidget()
        self.tabs.addTab(sysw, QtGui.QIcon(), "System")
        v = QtWidgets.QVBoxLayout(sysw)

        btn_row = QtWidgets.QHBoxLayout()
        btn_refresh = ModernButton("Refresh System Info")
        btn_export = ModernButton("Export to TXT")
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_export)
        btn_row.addStretch()
        v.addLayout(btn_row)

        self.sys_output = QtWidgets.QPlainTextEdit()
        self.sys_output.setReadOnly(True)
        self.sys_output.setFont(QtGui.QFont("Consolas", 11))
        v.addWidget(self.sys_output, 1)

        btn_refresh.clicked.connect(self._load_sysinfo)
        btn_export.clicked.connect(self._export_sysinfo)

        self._load_sysinfo()

    def _load_sysinfo(self):
        lines = []
        lines.append(f"Hostname: {socket.gethostname()}")
        lines.append(f"User: {getpass.getuser()}")
        lines.append(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
        lines.append(f"Processor: {platform.processor()}")
        lines.append(f"IP: {get_local_ip()}")
        lines.append(f"MAC: {get_mac()}")
        lines.append(f"Serial: {get_serial()}")
        self.sys_output.setPlainText("".join(lines))

    def _export_sysinfo(self):
        txt = self.sys_output.toPlainText().strip()
        if not txt:
            QtWidgets.QMessageBox.warning(self, "Export", "No system info. Please refresh first.")
            return
        path = os.path.join(os.getcwd(), "system_info.txt")
        try:
            with open(path, "w", encoding='utf-8') as f:
                f.write(txt)
            QtWidgets.QMessageBox.information(self, "Export", f"Saved to {path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export Error", str(e))

    # ---------------- Tools Tab ----------------
    def _build_tools_tab(self):
        tools = QtWidgets.QWidget()
        self.tabs.addTab(tools, QtGui.QIcon(), "Tools")
        v = QtWidgets.QVBoxLayout(tools)

        tcp_row = QtWidgets.QHBoxLayout()
        self.tcp_host = QtWidgets.QLineEdit()
        self.tcp_host.setPlaceholderText("Host (e.g. google.com)")
        self.tcp_host.setMinimumWidth(260)
        self.tcp_port = QtWidgets.QLineEdit()
        self.tcp_port.setPlaceholderText("Port (e.g. 443)")
        self.tcp_port.setMaximumWidth(120)
        tcp_btn = ModernButton("Check TCP Port")
        tcp_row.addWidget(self.tcp_host)
        tcp_row.addWidget(self.tcp_port)
        tcp_row.addWidget(tcp_btn)
        tcp_row.addStretch()
        v.addLayout(tcp_row)

        speed_row = QtWidgets.QHBoxLayout()
        self.speed_btn = ModernButton("Run Speedtest")
        speed_row.addWidget(self.speed_btn)
        speed_row.addStretch()
        v.addLayout(speed_row)

        self.tools_output = QtWidgets.QPlainTextEdit()
        self.tools_output.setReadOnly(True)
        self.tools_output.setFont(QtGui.QFont("Consolas", 11))
        v.addWidget(self.tools_output, 1)

        bottom = QtWidgets.QHBoxLayout()
        upload_btn = ModernButton("Upload Logs")
        email_btn = ModernButton("Send Email")
        bottom.addWidget(upload_btn)
        bottom.addWidget(email_btn)
        bottom.addStretch()
        v.addLayout(bottom)

        tcp_btn.clicked.connect(self._check_tcp)
        self.speed_btn.clicked.connect(self._start_speedtest)
        upload_btn.clicked.connect(self._upload_logs)
        email_btn.clicked.connect(self._send_email_dialog)

        self._speed_proc = None

    def _append_tools(self, text: str):
        self.tools_output.appendPlainText(str(text))
        sb = self.tools_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _check_tcp(self):
        host = self.tcp_host.text().strip()
        port_text = self.tcp_port.text().strip()
        if not host or not port_text.isdigit():
            self._append_tools('Invalid host or port')
            return
        worker = TcpCheckWorker(host, int(port_text))
        worker.result.connect(self._append_tools)
        worker.start()
        self._append_tools(f'Checking {host}:{port_text}...')

    def _start_speedtest(self):
        self._append_tools('Running speedtest...')
        if shutil.which('speedtest'):
            prog = 'speedtest'
            args = []
        else:
            prog = sys.executable
            args = ['-m', 'speedtest', '--secure']
        proc = QtCore.QProcess(self)
        proc.setProgram(prog)
        proc.setArguments(args)
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._append_tools(proc.readAllStandardOutput().data().decode(errors='ignore')))
        proc.finished.connect(lambda code, status: self._append_tools(f'=== speedtest done (code={code}) ==='))
        proc.start()
        self._speed_proc = proc

    def _upload_logs(self):
        combined = self.net_output.toPlainText() + "" + self.tools_output.toPlainText() + "" + self.sys_output.toPlainText()
        tmp = os.path.join(tempfile.gettempdir(), 'troubleshoot_combined.txt')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(combined)
        url, ok = QtWidgets.QInputDialog.getText(self, 'Upload logs', 'Enter upload URL (https://...):')
        if not ok or not url.strip():
            return
        uploader = UploadWorker(url.strip(), tmp)
        uploader.finished.connect(lambda ok, msg: self._append_tools(f'Upload: {msg}' if ok else f'Upload failed: {msg}'))
        uploader.start()
        self._append_tools('Uploading logs...')

    def _send_email_dialog(self):
        dlg = EmailDialog(self)
        dlg.sent.connect(lambda ok, msg: self._append_tools(f'Email: {msg}' if ok else f'Email failed: {msg}'))
        dlg.exec()

    def _fade_in(self):
        eff = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        self._anim = QtCore.QPropertyAnimation(eff, b'opacity')
        self._anim.setDuration(600)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

# ---- Email dialog ----
class EmailDialog(QtWidgets.QDialog):
    sent = QtCore.Signal(bool, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Send Email Report')
        self.resize(520, 320)
        layout = QtWidgets.QFormLayout(self)

        self.smtp = QtWidgets.QLineEdit('smtp.gmail.com')
        self.port = QtWidgets.QLineEdit('587')
        self.sender = QtWidgets.QLineEdit()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.recipients = QtWidgets.QLineEdit()
        self.subject = QtWidgets.QLineEdit('Troubleshoot Report')
        self.body = QtWidgets.QPlainTextEdit('See attached logs.')

        layout.addRow('SMTP server:', self.smtp)
        layout.addRow('Port:', self.port)
        layout.addRow('Sender (email):', self.sender)
        layout.addRow('App password:', self.password)
        layout.addRow('Recipients (comma):', self.recipients)
        layout.addRow('Subject:', self.subject)
        layout.addRow('Body:', self.body)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addRow(btn_box)
        btn_box.accepted.connect(self._on_send)
        btn_box.rejected.connect(self.reject)

    def _on_send(self):
        smtp = self.smtp.text().strip()
        try:
            port = int(self.port.text().strip())
        except Exception:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Invalid port')
            return
        sender = self.sender.text().strip()
        password = self.password.text().strip()
        recipients = [r.strip() for r in self.recipients.text().split(',') if r.strip()]
        subject = self.subject.text().strip()
        body = self.body.toPlainText()

        parent: MainWindow = self.parent()
        combined = parent.net_output.toPlainText() + '' + parent.tools_output.toPlainText() + '' + parent.sys_output.toPlainText()
        tmp = os.path.join(tempfile.gettempdir(), 'troubleshoot_email_attach.txt')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(combined)

        worker = EmailWorker(smtp, port, sender, password, recipients, subject, body, tmp)
        worker.finished.connect(lambda ok, msg: (self.sent.emit(ok, msg), QtWidgets.QMessageBox.information(self, 'Email', msg) if ok else QtWidgets.QMessageBox.critical(self, 'Email', msg), self.accept()))
        worker.start()

# ---- Run ----
if __name__ == '__main__':
    import shutil
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

import sys
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import requests

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer

# ---------------- SVG helper ----------------

def svg_icon(svg_str: str, size: int = 24) -> QtGui.QIcon:
    pix = QtGui.QPixmap(size, size)
    pix.fill(QtCore.Qt.transparent)
    renderer = QSvgRenderer(QtCore.QByteArray(svg_str.encode('utf-8')))
    painter = QtGui.QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QtGui.QIcon(pix)

# ---------------- Small utilities ----------------

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'Unknown'


def get_serial_number() -> str:
    try:
        out = subprocess.check_output(['wmic', 'bios', 'get', 'serialnumber'], stderr=subprocess.DEVNULL, text=True)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return lines[1] if len(lines) > 1 else 'Unknown'
    except Exception:
        return 'Unavailable'

# ---------------- Modern button ----------------
class ModernButton(QtWidgets.QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(False)

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

    def _update_style(self, hover: bool):
        bg = '#5752a2' if hover else '#3f3c6f'
        self.setStyleSheet(f"background:{bg}; color:#eaf2ff; padding:6px 12px; border:none; border-radius:6px;")

# ---------------- Workers ----------------
class TcpCheckWorker(QtCore.QThread):
    result = QtCore.Signal(str)

    def __init__(self, host: str, port: int, timeout: float = 3.0):
        super().__init__()
        self.host = host
        self.port = port
        self.timeout = timeout

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.host, int(self.port)))
            s.close()
            self.result.emit(f"{self.host}:{self.port} reachable")
        except Exception as e:
            self.result.emit(f"{self.host}:{self.port} unreachable ({e})")

# ---------------- Main window ----------------
class GradientWidget(QtWidgets.QWidget):
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        r = self.rect()
        grad = QtGui.QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0.0, QtGui.QColor('#1f1c2c'))
        grad.setColorAt(1.0, QtGui.QColor('#4b4466'))
        p.fillRect(r, grad)
        super().paintEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Windows Troubleshoot Tool')
        self.resize(980, 640)

        container = GradientWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        self.setCentralWidget(container)

        # Header
        header = QtWidgets.QLabel('Windows Troubleshoot Tool')
        header.setStyleSheet('font-size:20px; font-weight:600; color: #ffffff;')
        layout.addWidget(header)

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet(self._tabs_style())
        layout.addWidget(self.tabs, 1)

        # Build tabs
        self._build_network_tab()
        self._build_system_tab()
        self._build_tools_tab()

        # Fade-in
        self._fade_in()

    def _tabs_style(self) -> str:
        return '''
            QTabBar::tab { background: #2d2a4a; color: #eaf2ff; padding: 6px 14px; border-radius: 8px; margin: 2px; }
            QTabBar::tab:selected { background: #3f3c6f; }
            QTabWidget::pane { border: none; background: transparent; }
        '''

    # ---------------- Network Tab ----------------
    def _build_network_tab(self):
        net = QtWidgets.QWidget()
        self.tabs.addTab(net, svg_icon(self._svg_net(), 20), 'Network')
        v = QtWidgets.QVBoxLayout(net)

        row = QtWidgets.QHBoxLayout()
        self.net_host = QtWidgets.QLineEdit()
        self.net_host.setPlaceholderText('Enter hostname or IP...')
        self.net_host.setMinimumWidth(380)
        self.net_host.setStyleSheet('background:#f5f7fa; color:#222; padding:6px; border-radius:6px;')
        row.addWidget(self.net_host)

        self.btn_ping = ModernButton('Ping')
        self.btn_ping.clicked.connect(lambda: self._run_cmd('ping'))
        row.addWidget(self.btn_ping)

        self.btn_tracert = ModernButton('Tracert')
        self.btn_tracert.clicked.connect(lambda: self._run_cmd('tracert'))
        row.addWidget(self.btn_tracert)

        self.btn_ns = ModernButton('NSLookup')
        self.btn_ns.clicked.connect(lambda: self._run_cmd('nslookup'))
        row.addWidget(self.btn_ns)

        row.addStretch()
        v.addLayout(row)

        self.net_output = QtWidgets.QPlainTextEdit()
        self.net_output.setReadOnly(True)
        self.net_output.setStyleSheet('background:#0f1013; color:#f5faff; border-radius:6px; padding:8px;')
        self.net_output.setFont(QtGui.QFont('Consolas', 11))
        v.addWidget(self.net_output, 1)

        self.current_process = None

    def _append_net(self, text: str):
        self.net_output.appendPlainText(str(text))
        sb = self.net_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_net_buttons(self, enabled: bool):
        self.btn_ping.setEnabled(enabled)
        self.btn_tracert.setEnabled(enabled)
        self.btn_ns.setEnabled(enabled)

    def _run_cmd(self, cmd_name: str):
        target = self.net_host.text().strip()
        if not target:
            self._append_net('Enter a target first.')
            return

        # choose platform-specific args for ping
        if cmd_name == 'ping':
            if sys.platform.startswith('win'):
                args = ['-n', '4', target]
            else:
                args = ['-c', '4', target]
            program = 'ping'
        else:
            program = cmd_name
            args = [target]

        # start QProcess
        if shutil.which(program) is None:
            self._append_net(f'{program} not found on system')
            return

        if self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass

        proc = QtCore.QProcess(self)
        proc.setProgram(program)
        proc.setArguments(args)
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._append_net(proc.readAllStandardOutput().data().decode(errors='ignore')))
        proc.finished.connect(lambda code, status: self._append_net(f'=== finished (code={code}) ==='))
        proc.started.connect(lambda: self._set_net_buttons(False))
        proc.finished.connect(lambda code, status: self._set_net_buttons(True))
        proc.start()
        self.current_process = proc

    # ---------------- System Tab ----------------
    def _build_system_tab(self):
        sysw = QtWidgets.QWidget()
        self.tabs.addTab(sysw, svg_icon(self._svg_pc(), 20), 'System')
        v = QtWidgets.QFormLayout(sysw)

        lbl_host = QtWidgets.QLabel(socket.gethostname())
        lbl_ip = QtWidgets.QLabel(get_local_ip())
        lbl_serial = QtWidgets.QLabel(get_serial_number())

        lbl_host.setStyleSheet('color:#ffffff')
        lbl_ip.setStyleSheet('color:#ffffff')
        lbl_serial.setStyleSheet('color:#ffffff')

        v.addRow('Hostname:', lbl_host)
        v.addRow('Local IP:', lbl_ip)
        v.addRow('Serial Number:', lbl_serial)

        btn = ModernButton('Refresh')
        btn.clicked.connect(lambda: self._refresh_system(lbl_host, lbl_ip, lbl_serial))
        v.addRow(btn)

    def _refresh_system(self, host_lbl, ip_lbl, serial_lbl):
        host_lbl.setText(socket.gethostname())
        ip_lbl.setText(get_local_ip())
        serial_lbl.setText(get_serial_number())

    # ---------------- Tools Tab ----------------
    def _build_tools_tab(self):
        tools = QtWidgets.QWidget()
        self.tabs.addTab(tools, svg_icon(self._svg_tool(), 20), 'Tools')
        v = QtWidgets.QVBoxLayout(tools)

        row = QtWidgets.QHBoxLayout()
        self.tcp_host = QtWidgets.QLineEdit()
        self.tcp_host.setPlaceholderText('Host')
        self.tcp_host.setStyleSheet('background:#f5f7fa; color:#222; padding:6px; border-radius:6px;')
        row.addWidget(self.tcp_host)

        self.tcp_port = QtWidgets.QLineEdit()
        self.tcp_port.setPlaceholderText('Port')
        self.tcp_port.setMaximumWidth(140)
        self.tcp_port.setStyleSheet('background:#f5f7fa; color:#222; padding:6px; border-radius:6px;')
        row.addWidget(self.tcp_port)

        btn_check = ModernButton('Check TCP Port')
        btn_check.clicked.connect(self._check_tcp)
        row.addWidget(btn_check)
        row.addStretch()
        v.addLayout(row)

        self.tools_output = QtWidgets.QPlainTextEdit()
        self.tools_output.setReadOnly(True)
        self.tools_output.setStyleSheet('background:#0f1013; color:#f5faff; border-radius:6px; padding:8px;')
        self.tools_output.setFont(QtGui.QFont('Consolas', 11))
        v.addWidget(self.tools_output, 1)

        speed_btn = ModernButton('Run Speedtest')
        speed_btn.clicked.connect(self._start_speedtest)
        v.addWidget(speed_btn)

        # placeholders for upload/email
        bottom = QtWidgets.QHBoxLayout()
        up_btn = ModernButton('Upload Logs')
        up_btn.clicked.connect(self._upload_logs)
        em_btn = ModernButton('Save Report')
        em_btn.clicked.connect(self._save_report)
        bottom.addWidget(up_btn)
        bottom.addWidget(em_btn)
        bottom.addStretch()
        v.addLayout(bottom)

        self._speed_process = None

    def _append_tools(self, text: str):
        self.tools_output.appendPlainText(str(text))
        sb = self.tools_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _check_tcp(self):
        host = self.tcp_host.text().strip()
        port_text = self.tcp_port.text().strip()
        if not host or not port_text.isdigit():
            self._append_tools('Invalid host or port')
            return
        port = int(port_text)
        self._append_tools(f'Checking {host}:{port}...')
        worker = TcpCheckWorker(host, port)
        worker.result.connect(self._append_tools)
        worker.start()

    def _start_speedtest(self):
        # use sys.executable -m speedtest for stability
        self._append_tools('Running speedtest...')
        if shutil.which('speedtest') is not None:
            program = 'speedtest'
            args = []
        else:
            program = sys.executable
            args = ['-m', 'speedtest']

        proc = QtCore.QProcess(self)
        proc.setProgram(program)
        proc.setArguments(args)
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._append_tools(proc.readAllStandardOutput().data().decode(errors='ignore')))
        proc.finished.connect(lambda code, status: self._append_tools(f'=== speedtest done (code={code}) ==='))
        proc.start()
        self._speed_process = proc

    def _upload_logs(self):
        txt = self.net_output.toPlainText() + '\n' + self.tools_output.toPlainText()
        tmp = os.path.join(tempfile.gettempdir(), 'troubleshoot_log.txt')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(txt)

        def w():
            try:
                r = requests.post('https://example.com/upload', files={'log': open(tmp, 'rb')}, timeout=15)
                QtCore.QTimer.singleShot(0, lambda: self._append_tools(f'Upload finished. Status {r.status_code}'))
            except Exception as e:
                QtCore.QTimer.singleShot(0, lambda: self._append_tools(f'Upload failed: {e}'))

        threading.Thread(target=w, daemon=True).start()

    def _save_report(self):
        txt = self.net_output.toPlainText() + '\n' + self.tools_output.toPlainText()
        tmp = os.path.join(tempfile.gettempdir(), 'troubleshoot_report.txt')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(txt)
        self._append_tools(f'Report saved to {tmp}')

    def _fade_in(self):
        eff = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        anim = QtCore.QPropertyAnimation(eff, b'opacity')
        anim.setDuration(800)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()

    # ---------------- Simple SVGs ----------------
    def _svg_net(self) -> str:
        return '''<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10"/></svg>'''

    def _svg_pc(self) -> str:
        return '''<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8v1H8z"/></svg>'''

    def _svg_tool(self) -> str:
        return '''<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 13v6a2 2 0 0 1-2 2h-6l-4-4V9a2 2 0 0 1 2-2h6l4 4z"/></svg>'''

# ---------------- Run ----------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

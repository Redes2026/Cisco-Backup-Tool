#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         CISCO SWITCH BACKUP TOOL - v1.0                      ║
║   Soporte: Catalyst 2960 / 3560 / 9200 / 9300                ║
║   Protocolo: SSH via Netmiko                                 ║
║   Alberto Arellano A. / CCNA / CCNP / Automation / IA        ║
╚══════════════════════════════════════════════════════════════╝
Dependencias:
    pip install netmiko
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
import datetime
import queue
import re
import socket
import ipaddress
import subprocess
import platform
import time

try:
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
#  UTILIDADES DE CONECTIVIDAD (pre-checks)
# ─────────────────────────────────────────────────────────────
def validate_ip(host: str) -> tuple[bool, str]:
    """
    Valida que el host sea una IP válida o un hostname con formato correcto.
    Retorna (valido, mensaje).
    """
    host = host.strip()
    if not host:
        return False, "Campo de IP vacío."

    # Intentar como dirección IP
    try:
        ipaddress.ip_address(host)
        return True, ""
    except ValueError:
        pass

    # Validar como hostname (letras, números, guiones, puntos)
    hostname_re = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
        r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
    )
    if hostname_re.match(host):
        return True, ""

    return False, f"'{host}' no es una IP ni hostname válido."


def check_duplicates(hosts: list[str]) -> list[str]:
    """Retorna lista de IPs duplicadas."""
    seen = set()
    dupes = []
    for h in hosts:
        if h in seen:
            dupes.append(h)
        seen.add(h)
    return dupes


def tcp_ping(host: str, port: int = 22, timeout: float = 3.0) -> tuple[bool, str]:
    """
    Verifica si el puerto TCP (default 22/SSH) está abierto en el host.
    Mucho más rápido que esperar el timeout completo de Netmiko.
    Retorna (accesible, mensaje).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, f"Puerto {port}/TCP accesible."
        else:
            return False, f"Puerto {port}/TCP cerrado o filtrado (código {result})."
    except socket.gaierror:
        return False, f"No se puede resolver el host '{host}'. Verifica DNS o la IP."
    except socket.timeout:
        return False, f"Timeout al verificar puerto {port}/TCP en {host}."
    except OSError as e:
        return False, f"Error de red: {e}"


def icmp_ping(host: str, timeout: int = 2) -> tuple[bool, str]:
    """
    Envía un ping ICMP. Retorna (alcanzable, mensaje).
    Funciona en Windows y Linux/macOS.
    """
    try:
        system = platform.system().lower()
        if system == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout), host]

        proc = subprocess.run(
            cmd, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=timeout + 2
        )
        if proc.returncode == 0:
            return True, f"ICMP ping OK a {host}."
        else:
            return False, f"Host {host} no responde a ICMP ping."
    except subprocess.TimeoutExpired:
        return False, f"Timeout ICMP ping a {host}."
    except FileNotFoundError:
        return False, "Comando ping no disponible en este sistema."
    except Exception as e:
        return False, f"Error ping: {e}"


def pre_check_host(host: str, ssh_port: int = 22,
                   tcp_timeout: float = 3.0) -> dict:
    """
    Ejecuta todas las verificaciones previas a la conexión SSH:
      1. Validación de formato IP/hostname
      2. Verificación TCP puerto 22
    Retorna dict con: valid, reachable, ssh_open, message, skip
    """
    result = {
        "host"      : host,
        "valid"     : False,
        "reachable" : False,
        "ssh_open"  : False,
        "message"   : "",
        "skip"      : False,   # True = no intentar SSH
    }

    # 1. Validar formato
    valid, msg = validate_ip(host)
    if not valid:
        result["message"] = f"IP/hostname inválido: {msg}"
        result["skip"]    = True
        return result
    result["valid"] = True

    # 2. Verificar puerto TCP 22
    ssh_ok, ssh_msg = tcp_ping(host, port=ssh_port, timeout=tcp_timeout)
    result["ssh_open"] = ssh_ok
    result["reachable"] = ssh_ok

    if not ssh_ok:
        # 2b. Hacer ping ICMP para distinguir "host apagado" vs "SSH bloqueado"
        icmp_ok, icmp_msg = icmp_ping(host, timeout=2)
        if icmp_ok:
            result["message"] = (
                f"Host {host} RESPONDE a ping pero el puerto SSH (22) está "
                f"cerrado o filtrado. Verifica que SSH esté habilitado: "
                f"'ip ssh version 2' / 'line vty 0 15 → transport input ssh'"
            )
        else:
            result["message"] = (
                f"Host {host} NO alcanzable (sin respuesta ICMP ni TCP/22). "
                f"Verifica: IP correcta, cable/VLAN, que el equipo esté encendido."
            )
        result["skip"] = True
        return result

    result["message"] = ssh_msg
    return result


# ─────────────────────────────────────────────────────────────
#  CONSTANTES Y PALETA
# ─────────────────────────────────────────────────────────────
BG_DARK      = "#0d1117"
BG_PANEL     = "#161b22"
BG_CARD      = "#1c2128"
BG_INPUT     = "#21262d"
ACCENT_BLUE  = "#1f6feb"
ACCENT_GREEN = "#3fb950"
ACCENT_RED   = "#f85149"
ACCENT_ORANGE= "#d29922"
ACCENT_CYAN  = "#39c5cf"
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED   = "#7d8590"
TEXT_DIM     = "#484f58"
BORDER       = "#30363d"

FONT_TITLE   = ("Consolas", 18, "bold")
FONT_HEADING = ("Consolas", 11, "bold")
FONT_LABEL   = ("Consolas", 9)
FONT_MONO    = ("Consolas", 9)
FONT_BTN     = ("Consolas", 10, "bold")
FONT_SMALL   = ("Consolas", 8)


# ─────────────────────────────────────────────────────────────
#  LÓGICA DE RESPALDO SSH
# ─────────────────────────────────────────────────────────────
def detect_device_type(hostname: str) -> str:
    """Devuelve el device_type de Netmiko según el modelo detectado o usa generic."""
    return "cisco_ios"


def backup_device(host: str, username: str, password: str,
                  secret: str = "", output_dir: str = ".",
                  log_callback=None, timeout: int = 30) -> dict:
    """
    Conecta vía SSH y obtiene la running-config.
    Maneja correctamente el enable password con múltiples estrategias.
    Retorna dict con keys: success, hostname, filename, message
    """
    def log(msg, level="info"):
        if log_callback:
            log_callback(host, msg, level)

    result = {"success": False, "host": host, "filename": "", "message": ""}

    if not NETMIKO_AVAILABLE:
        result["message"] = "Netmiko no instalado. Ejecuta: pip install netmiko"
        log(result["message"], "error")
        return result

    # Determinar el enable secret:
    # Prioridad: 1) secret explícito, 2) mismo password de login
    enable_secret = secret.strip() if secret and secret.strip() else password

    device = {
        "device_type"        : "cisco_ios",
        "host"               : host,
        "username"           : username,
        "password"           : password,
        "secret"             : enable_secret,
        "timeout"            : timeout,
        "session_timeout"    : timeout + 30,
        "conn_timeout"       : timeout,
        "auth_timeout"       : timeout,
        "banner_timeout"     : 20,
        "fast_cli"           : False,
        "global_delay_factor": 2,
    }

    connection = None
    try:
        log(f"Conectando a {host} por SSH (usuario: {username})...", "info")
        connection = ConnectHandler(**device)
        log("Sesión SSH establecida.", "success")

        # ── Verificar y escalar a modo EXEC privilegiado ──────────
        in_enable = connection.check_enable_mode()
        log(f"Modo privilegiado activo: {in_enable}", "info")

        if not in_enable:
            log("Escalando a modo privilegiado (enable)...", "info")
            try:
                # Netmiko usa automáticamente device['secret'] para responder
                # al prompt 'Password:' del comando enable
                connection.enable()
                if connection.check_enable_mode():
                    log("✓ Enable mode OK.", "success")
                else:
                    # Segundo intento: enviar enable manualmente
                    log("Reintentando enable manualmente...", "warning")
                    output = connection.send_command_timing(
                        "enable",
                        strip_prompt=False,
                        strip_command=False
                    )
                    if "Password" in output or "password" in output:
                        output = connection.send_command_timing(
                            enable_secret,
                            strip_prompt=False,
                            strip_command=False
                        )
                    if not connection.check_enable_mode():
                        raise Exception(
                            "No se pudo obtener modo privilegiado. "
                            "Verifica el Enable Password."
                        )
                    log("✓ Enable mode OK (intento manual).", "success")

            except Exception as enable_err:
                # Si el error es de contraseña de enable, reportar claramente
                err_str = str(enable_err).lower()
                if "password" in err_str or "enable" in err_str or "invalid" in err_str:
                    raise Exception(
                        f"Enable password incorrecto para {host}. "
                        f"Ingresa el Enable Password en el campo correspondiente."
                    )
                raise

        # ── Obtener hostname real del dispositivo ─────────────────
        log("Obteniendo información del dispositivo...", "info")
        hostname = host  # fallback

        # Método 1: show version
        try:
            version_out = connection.send_command(
                "show version | include uptime",
                read_timeout=20
            )
            m = re.search(r"^(\S+)\s+uptime", version_out, re.MULTILINE)
            if m:
                hostname = m.group(1)
        except Exception:
            pass

        # Método 2: show running-config | include hostname
        if hostname == host:
            try:
                hn_out = connection.send_command(
                    "show running-config | include ^hostname",
                    read_timeout=15
                )
                m = re.search(r"^hostname\s+(\S+)", hn_out, re.MULTILINE)
                if m:
                    hostname = m.group(1)
            except Exception:
                pass

        log(f"Dispositivo: {hostname} ({host})", "info")

        # ── Deshabilitar paginación para obtener config completa ──
        connection.send_command_timing("terminal length 0")

        # ── Descargar running-config ──────────────────────────────
        log("Descargando running-config...", "info")
        config = connection.send_command(
            "show running-config",
            read_timeout=90,
            strip_prompt=True,
            strip_command=True,
            expect_string=r"#",
        )

        connection.disconnect()
        log("Sesión SSH cerrada.", "info")

        # Validar que tenemos algo razonable
        if not config:
            raise Exception("La configuración descargada está vacía.")
        if len(config) < 50:
            raise Exception(f"Configuración demasiado corta ({len(config)} bytes). Posible error.")
        if "Invalid input" in config or "% Error" in config:
            raise Exception(f"El dispositivo devolvió un error: {config[:200]}")

        # ── Guardar archivo ───────────────────────────────────────
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_host = host.replace(".", "_")
        filename  = f"{hostname}_{safe_host}_{timestamp}.txt"
        filepath  = os.path.join(output_dir, filename)

        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("! ============================================================\n")
            f.write(f"! Respaldo  : {hostname}  ({host})\n")
            f.write(f"! Fecha     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"! Usuario   : {username}\n")
            f.write(f"! Tamaño    : {len(config)} bytes\n")
            f.write("! Herramienta: Cisco Backup Tool v1.0\n")
            f.write("! ============================================================\n\n")
            f.write(config)

        log(f"✓ Respaldo guardado: {filename}  ({len(config):,} bytes)", "success")
        result.update({
            "success" : True,
            "filename": filepath,
            "message" : f"OK — {filename}"
        })

    except NetmikoAuthenticationException:
        msg = (f"Error de autenticación SSH en {host}. "
               f"Verifica usuario '{username}' y contraseña.")
        result["message"] = msg
        log(msg, "error")

    except NetmikoTimeoutException:
        msg = f"Timeout ({timeout}s) al conectar a {host}. Verifica IP y acceso SSH."
        result["message"] = msg
        log(msg, "error")

    except Exception as e:
        result["message"] = str(e)
        log(f"✗ {e}", "error")

    finally:
        # Garantizar cierre de sesión aunque haya excepción
        try:
            if connection and connection.is_alive():
                connection.disconnect()
        except Exception:
            pass

    return result


# ─────────────────────────────────────────────────────────────
#  WIDGETS PERSONALIZADOS
# ─────────────────────────────────────────────────────────────
class StyledEntry(tk.Frame):
    def __init__(self, parent, placeholder="", show="", width=28, **kw):
        super().__init__(parent, bg=BG_INPUT,
                         highlightbackground=BORDER,
                         highlightthickness=1, **kw)
        self._ph = placeholder
        self._show = show
        self._active = False

        self.entry = tk.Entry(
            self, bg=BG_INPUT, fg=TEXT_MUTED,
            insertbackground=ACCENT_BLUE,
            relief="flat", font=FONT_MONO,
            width=width, bd=4,
            highlightthickness=0
        )
        self.entry.pack(fill="x")
        self.entry.insert(0, placeholder)
        self.entry.bind("<FocusIn>",  self._on_focus)
        self.entry.bind("<FocusOut>", self._off_focus)

    def _on_focus(self, _):
        if not self._active:
            self.entry.delete(0, "end")
            self.entry.config(fg=TEXT_PRIMARY, show=self._show)
            self._active = True
        self.config(highlightbackground=ACCENT_BLUE)

    def _off_focus(self, _):
        if not self.entry.get():
            self.entry.config(fg=TEXT_MUTED, show="")
            self.entry.insert(0, self._ph)
            self._active = False
        self.config(highlightbackground=BORDER)

    def get(self):
        val = self.entry.get()
        return "" if val == self._ph else val

    def set(self, val):
        self.entry.delete(0, "end")
        if val:
            self.entry.config(fg=TEXT_PRIMARY, show=self._show)
            self.entry.insert(0, val)
            self._active = True
        else:
            self.entry.config(fg=TEXT_MUTED, show="")
            self.entry.insert(0, self._ph)
            self._active = False


class IconButton(tk.Button):
    def __init__(self, parent, text, color=ACCENT_BLUE,
                 hover_color=None, **kw):
        self._color = color
        self._hover = hover_color or self._darken(color)
        super().__init__(
            parent, text=text, bg=color, fg=TEXT_PRIMARY,
            font=FONT_BTN, relief="flat", bd=0,
            padx=16, pady=8, cursor="hand2",
            activebackground=self._hover,
            activeforeground=TEXT_PRIMARY, **kw
        )
        self.bind("<Enter>", lambda _: self.config(bg=self._hover))
        self.bind("<Leave>", lambda _: self.config(bg=self._color))

    @staticmethod
    def _darken(hex_color):
        r = max(0, int(hex_color[1:3], 16) - 30)
        g = max(0, int(hex_color[3:5], 16) - 30)
        b = max(0, int(hex_color[5:7], 16) - 30)
        return f"#{r:02x}{g:02x}{b:02x}"


class StatusBadge(tk.Label):
    COLORS = {
        "pending"     : (TEXT_DIM,     "Pendiente"),
        "checking"    : (ACCENT_CYAN,  "⟳ Verificando"),
        "running"     : (ACCENT_ORANGE,"⟳ Conectando"),
        "success"     : (ACCENT_GREEN, "✓ OK"),
        "error"       : (ACCENT_RED,   "✗ Error"),
        "warning"     : (ACCENT_ORANGE,"⚠ Warning"),
        "unreachable" : (ACCENT_RED,   "✗ Inaccesible"),
        "invalid"     : (ACCENT_RED,   "✗ IP inválida"),
        "no_ssh"      : (ACCENT_RED,   "✗ SSH cerrado"),
        "retrying"    : (ACCENT_ORANGE,"↻ Reintento"),
    }
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_CARD, font=FONT_SMALL, **kw)
        self.set("pending")

    def set(self, status):
        color, label = self.COLORS.get(status, (TEXT_MUTED, status))
        self.config(fg=color, text=label)


# ─────────────────────────────────────────────────────────────
#  VENTANA PRINCIPAL
# ─────────────────────────────────────────────────────────────
class CiscoBackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cisco Switch Backup Tool")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)
        self.minsize(900, 640)

        # centrar ventana
        w, h = 1100, 720
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._queue   = queue.Queue()
        self._devices = []   # lista de filas: [ip_var, status_badge, ...]
        self._running = False
        self._output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "cisco_backups"))

        self._build_ui()
        self._check_queue()

        if not NETMIKO_AVAILABLE:
            self._log("⚠  Netmiko NO está instalado. Instálalo con:  pip install netmiko", "warning")
            self._log("   Los respaldos reales no funcionarán hasta instalarlo.", "warning")
        else:
            self._log("✓  Netmiko detectado. Listo para conectar.", "success")

    # ── UI Principal ──────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=BG_PANEL, pady=0)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT_BLUE, height=3).pack(fill="x")
        inner_hdr = tk.Frame(hdr, bg=BG_PANEL, padx=24, pady=14)
        inner_hdr.pack(fill="x")

        tk.Label(inner_hdr, text="⬡ CISCO SWITCH BACKUP TOOL",
                 font=FONT_TITLE, bg=BG_PANEL, fg=ACCENT_BLUE).pack(side="left")
        tk.Label(inner_hdr,
                 text="Catalyst 2960 · 3560 · 9200 · 9300  |  SSH / running-config",
                 font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_MUTED).pack(side="left", padx=16, pady=6)

        ver = tk.Label(inner_hdr, text="v1.1", font=FONT_SMALL,
                       bg=ACCENT_BLUE, fg="#fff", padx=8, pady=3)
        ver.pack(side="right")

        # ── Cuerpo principal: izquierda + derecha ──
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left  = tk.Frame(body, bg=BG_DARK)
        right = tk.Frame(body, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=False, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True)

        self._build_credentials(left)
        self._build_devices_panel(left)
        self._build_output_dir(left)
        self._build_actions(left)
        self._build_log_panel(right)

    # ── Panel credenciales ────────────────────────────────────
    def _build_credentials(self, parent):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))
        tk.Frame(card, bg=ACCENT_BLUE, height=2).pack(fill="x")

        tk.Label(card, text="  CREDENCIALES SSH", font=FONT_HEADING,
                 bg=BG_CARD, fg=TEXT_PRIMARY, pady=8).pack(anchor="w")

        fields = tk.Frame(card, bg=BG_CARD, padx=12, pady=4)
        fields.pack(fill="x")

        def row(label, widget_creator):
            f = tk.Frame(fields, bg=BG_CARD)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, font=FONT_LABEL,
                     bg=BG_CARD, fg=TEXT_MUTED, width=14, anchor="w").pack(side="left")
            w = widget_creator(f)
            w.pack(side="left", fill="x", expand=True)
            return w

        self.e_user    = row("Usuario SSH :", lambda p: StyledEntry(p, "admin", width=22))
        self.e_pass    = row("Password    :", lambda p: StyledEntry(p, "••••••", show="•", width=22))
        self.e_enable  = row("Enable Pwd  :", lambda p: StyledEntry(p, "(opcional)", show="•", width=22))
        self.e_timeout = row("Timeout (s) :", lambda p: StyledEntry(p, "30", width=22))

        tk.Frame(card, bg=BG_DARK, height=8).pack()

    # ── Panel dispositivos ────────────────────────────────────
    def _build_devices_panel(self, parent):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, pady=(0, 8))
        tk.Frame(card, bg=ACCENT_CYAN, height=2).pack(fill="x")

        # header de la lista
        hdr = tk.Frame(card, bg=BG_CARD, padx=12, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  DISPOSITIVOS", font=FONT_HEADING,
                 bg=BG_CARD, fg=TEXT_PRIMARY).pack(side="left")

        add_btn = IconButton(hdr, "+ Agregar", color="#1a3a1a",
                             hover_color="#1f5c1f",
                             command=self._add_device_row)
        add_btn.config(font=FONT_SMALL, padx=8, pady=4)
        add_btn.pack(side="right")

        clr_btn = IconButton(hdr, "✕ Limpiar", color="#3a1a1a",
                             hover_color="#5c1f1f",
                             command=self._clear_devices)
        clr_btn.config(font=FONT_SMALL, padx=8, pady=4)
        clr_btn.pack(side="right", padx=(0, 6))

        # Cabecera columnas
        col_hdr = tk.Frame(card, bg=BG_PANEL, padx=12, pady=4)
        col_hdr.pack(fill="x")
        for txt, w in [("  IP / Hostname", 22), ("Estado", 12), ("", 4)]:
            tk.Label(col_hdr, text=txt, font=FONT_SMALL,
                     bg=BG_PANEL, fg=TEXT_DIM, width=w, anchor="w").pack(side="left")

        # Scroll container
        canvas_frame = tk.Frame(card, bg=BG_CARD)
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._canvas = tk.Canvas(canvas_frame, bg=BG_CARD,
                                 highlightthickness=0, height=160)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._devices_frame = tk.Frame(self._canvas, bg=BG_CARD)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._devices_frame, anchor="nw", width=0)
        self._devices_frame.bind("<Configure>", self._on_devices_resize)
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        # Importar desde archivo
        imp = tk.Frame(card, bg=BG_CARD, padx=12, pady=6)
        imp.pack(fill="x")
        tk.Label(imp, text="Importar IPs desde archivo .txt (una por línea):",
                 font=FONT_SMALL, bg=BG_CARD, fg=TEXT_MUTED).pack(side="left")
        IconButton(imp, "📂 Importar", color=BG_INPUT,
                   command=self._import_from_file).config(
                       font=FONT_SMALL, padx=6, pady=3)
        # re-pack the button with pack
        for w in imp.winfo_children():
            if isinstance(w, tk.Button):
                w.pack(side="left", padx=8)

        # agregar 3 filas por defecto
        for _ in range(3):
            self._add_device_row()

    def _on_devices_resize(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _add_device_row(self, ip=""):
        row_idx = len(self._devices)
        row = tk.Frame(self._devices_frame, bg=BG_CARD, pady=2)
        row.pack(fill="x", padx=4)

        # número
        tk.Label(row, text=f"{row_idx+1:02d}", font=FONT_SMALL,
                 bg=BG_CARD, fg=TEXT_DIM, width=3).pack(side="left")

        ip_entry = StyledEntry(row, placeholder="192.168.1.1", width=20)
        if ip:
            ip_entry.set(ip)
        ip_entry.pack(side="left", padx=(2, 8))

        badge = StatusBadge(row, width=12)
        badge.pack(side="left", padx=4)

        del_btn = tk.Button(row, text="✕", font=FONT_SMALL,
                            bg=BG_CARD, fg=TEXT_DIM,
                            relief="flat", cursor="hand2",
                            command=lambda r=row, d=(ip_entry, badge): self._remove_row(r, d))
        del_btn.pack(side="left", padx=4)

        self._devices.append((ip_entry, badge, row))
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _remove_row(self, row_frame, device_tuple):
        row_frame.destroy()
        self._devices = [d for d in self._devices
                         if d[0] is not device_tuple[0]]

    def _clear_devices(self):
        for entry, badge, row in self._devices:
            row.destroy()
        self._devices.clear()

    def _import_from_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de IPs",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path) as f:
                ips = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            for ip in ips:
                self._add_device_row(ip)
            self._log(f"✓ Importadas {len(ips)} IPs desde {os.path.basename(path)}", "success")
        except Exception as e:
            self._log(f"Error importando archivo: {e}", "error")

    # ── Directorio de salida ──────────────────────────────────
    def _build_output_dir(self, parent):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))
        tk.Frame(card, bg=ACCENT_GREEN, height=2).pack(fill="x")

        f = tk.Frame(card, bg=BG_CARD, padx=12, pady=10)
        f.pack(fill="x")
        tk.Label(f, text="  CARPETA DE RESPALDOS", font=FONT_HEADING,
                 bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w")
        f2 = tk.Frame(f, bg=BG_CARD, pady=4)
        f2.pack(fill="x")
        dir_entry = tk.Entry(f2, textvariable=self._output_dir,
                             bg=BG_INPUT, fg=TEXT_PRIMARY,
                             font=FONT_MONO, relief="flat",
                             insertbackground=ACCENT_BLUE, bd=4)
        dir_entry.pack(side="left", fill="x", expand=True)
        IconButton(f2, "📁", color=BG_INPUT,
                   command=self._choose_dir).pack(side="left", padx=(6, 0))

    def _choose_dir(self):
        d = filedialog.askdirectory(title="Carpeta de respaldos")
        if d:
            self._output_dir.set(d)

    # ── Botones de acción ─────────────────────────────────────
    def _build_actions(self, parent):
        f = tk.Frame(parent, bg=BG_DARK, pady=6)
        f.pack(fill="x")

        self.btn_start = IconButton(
            f, "▶  INICIAR RESPALDOS",
            color=ACCENT_BLUE,
            command=self._start_backup
        )
        self.btn_start.pack(fill="x", pady=(0, 6))

        row2 = tk.Frame(f, bg=BG_DARK)
        row2.pack(fill="x")

        IconButton(row2, "🔄  Resetear Estados",
                   color=BG_INPUT,
                   command=self._reset_statuses).pack(side="left", fill="x",
                                                       expand=True, padx=(0, 4))
        IconButton(row2, "📂  Abrir Carpeta",
                   color=BG_INPUT,
                   command=self._open_output_dir).pack(side="left", fill="x",
                                                        expand=True, padx=(4, 0))

        row3 = tk.Frame(f, bg=BG_DARK)
        row3.pack(fill="x", pady=(6, 0))
        IconButton(row3, "ℹ   Acerca de",
                   color="#1a1a2e",
                   hover_color="#16213e",
                   command=self._show_about).pack(fill="x")

        row4 = tk.Frame(f, bg=BG_DARK)
        row4.pack(fill="x", pady=(6, 0))
        IconButton(row4, "📡  Monitor SNMP",
                   color="#0d2b2b",
                   hover_color="#0f3d3d",
                   command=self._open_snmp_monitor).pack(fill="x")

    # ── Panel de log ──────────────────────────────────────────
    def _build_log_panel(self, parent):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        tk.Frame(card, bg=ACCENT_ORANGE, height=2).pack(fill="x")

        log_hdr = tk.Frame(card, bg=BG_CARD, padx=12, pady=8)
        log_hdr.pack(fill="x")
        tk.Label(log_hdr, text="  CONSOLA DE OPERACIONES",
                 font=FONT_HEADING, bg=BG_CARD, fg=TEXT_PRIMARY).pack(side="left")
        IconButton(log_hdr, "Limpiar", color=BG_INPUT,
                   command=self._clear_log).config(font=FONT_SMALL, padx=8, pady=3)
        for w in log_hdr.winfo_children():
            if isinstance(w, tk.Button):
                w.pack(side="right")

        self.log_box = scrolledtext.ScrolledText(
            card, bg=BG_DARK, fg=TEXT_PRIMARY,
            font=FONT_MONO, relief="flat", bd=0,
            insertbackground=ACCENT_BLUE,
            state="disabled", wrap="word",
            padx=10, pady=8
        )
        self.log_box.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Tags de color
        self.log_box.tag_config("info",    foreground=TEXT_MUTED)
        self.log_box.tag_config("success", foreground=ACCENT_GREEN)
        self.log_box.tag_config("error",   foreground=ACCENT_RED)
        self.log_box.tag_config("warning", foreground=ACCENT_ORANGE)
        self.log_box.tag_config("host",    foreground=ACCENT_CYAN)
        self.log_box.tag_config("dim",     foreground=TEXT_DIM)

        # Barra de estado resumen
        self.status_bar = tk.Label(
            card, text="Listo.",
            font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_MUTED,
            anchor="w", padx=12, pady=4
        )
        self.status_bar.pack(fill="x")

        # Progress
        self.progress = ttk.Progressbar(card, mode="determinate")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=BG_DARK,
                        background=ACCENT_BLUE, thickness=4)
        self.progress.pack(fill="x", padx=6, pady=(0, 6))

    # ── Helpers UI ────────────────────────────────────────────
    def _log(self, message, level="info"):
        """Escribe en el log con color."""
        def _write():
            self.log_box.config(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}] ", "dim")
            self.log_box.insert("end", message + "\n", level)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _write)

    def _log_host(self, host, message, level="info"):
        def _write():
            self.log_box.config(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}] ", "dim")
            self.log_box.insert("end", f"[{host}] ", "host")
            self.log_box.insert("end", message + "\n", level)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _write)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _reset_statuses(self):
        for entry, badge, _ in self._devices:
            badge.set("pending")
        self._log("Estados reseteados.", "dim")

    def _open_output_dir(self):
        d = self._output_dir.get()
        os.makedirs(d, exist_ok=True)
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(d)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])

    def _open_snmp_monitor(self):
        """Abre el Monitor SNMP como ventana independiente."""
        try:
            # Intentar importar el módulo desde el mismo directorio
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            from snmp_monitor import SNMPMonitorWindow
            SNMPMonitorWindow(self)
        except ImportError:
            messagebox.showerror(
                "Módulo no encontrado",
                "No se encontró snmp_monitor.py\n\n"
                "Asegúrate de que el archivo snmp_monitor.py\n"
                "esté en el mismo directorio que este script.\n\n"
                "También instala la dependencia:\n"
                "  pip install pysnmp"
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el monitor:\n{e}")

    def _show_about(self):
        """Ventana modal Acerca de."""
        win = tk.Toplevel(self)
        win.title("Acerca de — Cisco Backup Tool")
        win.configure(bg=BG_DARK)
        win.resizable(False, False)
        win.grab_set()  # modal

        # Centrar sobre la ventana principal
        w, h = 520, 440
        px = self.winfo_x() + (self.winfo_width()  - w) // 2
        py = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{px}+{py}")

        # ── Franja superior ──
        top = tk.Frame(win, bg=ACCENT_BLUE, height=4)
        top.pack(fill="x")

        # ── Ícono / logo ASCII ──
        logo_frame = tk.Frame(win, bg=BG_DARK, pady=20)
        logo_frame.pack(fill="x")

        logo_text = (
            "  ██████╗██╗███████╗ ██████╗ ██████╗ \n"
            " ██╔════╝██║██╔════╝██╔════╝██╔═══██╗\n"
            " ██║     ██║███████╗██║     ██║   ██║\n"
            " ██║     ██║╚════██║██║     ██║   ██║\n"
            " ╚██████╗██║███████║╚██████╗╚██████╔╝\n"
            "  ╚═════╝╚═╝╚══════╝ ╚═════╝ ╚═════╝ "
        )
        tk.Label(logo_frame, text=logo_text,
                 font=("Consolas", 7, "bold"),
                 bg=BG_DARK, fg=ACCENT_BLUE,
                 justify="center").pack()

        tk.Label(logo_frame, text="SWITCH BACKUP TOOL",
                 font=("Consolas", 10, "bold"),
                 bg=BG_DARK, fg=ACCENT_CYAN).pack(pady=(4, 0))

        # ── Separador ──
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=30)

        # ── Descripción ──
        desc_frame = tk.Frame(win, bg=BG_PANEL, padx=30, pady=18)
        desc_frame.pack(fill="x")

        desc = (
            "Herramienta para obtener respaldos automáticos\n"
            "de la configuración running-config de equipos\n"
            "Cisco Catalyst vía protocolo SSH."
        )
        tk.Label(desc_frame, text=desc,
                 font=("Consolas", 9),
                 bg=BG_PANEL, fg=TEXT_PRIMARY,
                 justify="center").pack()

        # Modelos soportados
        models_frame = tk.Frame(desc_frame, bg=BG_PANEL, pady=8)
        models_frame.pack()
        for model, color in [
            ("Catalyst 2960", ACCENT_GREEN),
            ("Catalyst 3560", ACCENT_CYAN),
            ("Catalyst 9200", ACCENT_BLUE),
            ("Catalyst 9300", ACCENT_ORANGE),
        ]:
            tk.Label(models_frame, text=f"  {model}  ",
                     font=FONT_SMALL, bg=color,
                     fg=BG_DARK, padx=6, pady=3).pack(side="left", padx=4)

        # ── Separador ──
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=30, pady=(8, 0))

        # ── Autor ──
        author_frame = tk.Frame(win, bg=BG_DARK, pady=18, padx=30)
        author_frame.pack(fill="x")

        tk.Label(author_frame, text="AUTOR",
                 font=("Consolas", 8, "bold"),
                 bg=BG_DARK, fg=TEXT_DIM).pack(anchor="w")

        tk.Label(author_frame,
                 text="Alberto Arellano A.",
                 font=("Consolas", 14, "bold"),
                 bg=BG_DARK, fg=TEXT_PRIMARY).pack(anchor="w", pady=(4, 0))

        certs_frame = tk.Frame(author_frame, bg=BG_DARK, pady=8)
        certs_frame.pack(anchor="w")
        for cert, color in [
            ("CCNA",        "#1f6feb"),
            ("CCNP",        "#388bfd"),
            ("Automation",  "#3fb950"),
            ("Cybersecurity","#d29922"),
        ]:
            badge = tk.Label(certs_frame, text=f" {cert} ",
                             font=("Consolas", 8, "bold"),
                             bg=BG_PANEL,
                             fg=color,
                             highlightbackground=color,
                             highlightthickness=1,
                             padx=5, pady=3)
            badge.pack(side="left", padx=(0, 6))

        # ── Versión y protocolo ──
        info_frame = tk.Frame(win, bg=BG_DARK, padx=30)
        info_frame.pack(fill="x")
        tk.Label(info_frame,
                 text="Versión 1.0   |   Protocolo SSH   |   Netmiko",
                 font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM).pack(side="left")

        # ── Franja inferior + botón cerrar ──
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=0, pady=(14, 0))
        btn_frame = tk.Frame(win, bg=BG_PANEL, pady=10)
        btn_frame.pack(fill="x")
        IconButton(btn_frame, "  Cerrar  ",
                   color=ACCENT_BLUE,
                   command=win.destroy).pack()

    def _set_status_bar(self, text):
        self.after(0, lambda: self.status_bar.config(text=text))

    def _set_progress(self, val):
        self.after(0, lambda: self.progress.config(value=val))

    # ── Lógica de respaldo ────────────────────────────────────
    def _start_backup(self):
        if self._running:
            return

        username = self.e_user.get()
        password = self.e_pass.get()
        enable   = self.e_enable.get()
        timeout_str = self.e_timeout.get()

        if not username or not password:
            messagebox.showwarning("Credenciales faltantes",
                                   "Ingresa usuario y contraseña SSH.")
            return

        try:
            timeout = int(timeout_str) if timeout_str else 30
        except ValueError:
            timeout = 30

        devices_to_backup = []
        for entry, badge, _ in self._devices:
            ip = entry.get().strip()
            if ip:
                devices_to_backup.append((ip, entry, badge))

        if not devices_to_backup:
            messagebox.showwarning("Sin dispositivos",
                                   "Agrega al menos una IP de dispositivo.")
            return

        self._running = True
        self.btn_start.config(state="disabled", text="⏳  Ejecutando...")

        self._log("=" * 60, "dim")
        self._log(f"Iniciando respaldo de {len(devices_to_backup)} dispositivo(s)...", "info")
        self._log(f"Usuario: {username}   |   Timeout: {timeout}s", "info")
        self._log(f"Carpeta: {self._output_dir.get()}", "info")
        self._log("=" * 60, "dim")

        total = len(devices_to_backup)
        self.progress.config(maximum=total, value=0)

        def worker():
            ok = err = skipped = 0

            # ── 1. Validar IPs duplicadas antes de empezar ──────
            all_ips = [ip for ip, _, _ in devices_to_backup]
            dupes   = check_duplicates(all_ips)
            if dupes:
                self._log(
                    f"⚠  IPs duplicadas detectadas: {', '.join(set(dupes))}. "
                    f"Se procesará solo la primera aparición.",
                    "warning"
                )
                # Filtrar duplicados: solo primera ocurrencia
                seen_ips     = set()
                unique_devs  = []
                for ip, entry, badge in devices_to_backup:
                    if ip not in seen_ips:
                        unique_devs.append((ip, entry, badge))
                        seen_ips.add(ip)
                    else:
                        self.after(0, lambda b=badge: b.set("warning"))
                        self._log_host(ip, "Duplicado — omitido.", "warning")
                        skipped += 1
                devices_to_backup_final = unique_devs
            else:
                devices_to_backup_final = devices_to_backup

            total_final = len(devices_to_backup_final)
            self.progress.config(maximum=max(total_final, 1), value=0)

            for idx, (ip, entry, badge) in enumerate(devices_to_backup_final):

                # ── 2. Pre-check: formato IP y accesibilidad ────
                self.after(0, lambda b=badge: b.set("checking"))
                self._log_host(ip, "Verificando accesibilidad...", "info")

                check = pre_check_host(ip, ssh_port=22, tcp_timeout=3.0)

                if not check["valid"]:
                    self.after(0, lambda b=badge: b.set("invalid"))
                    self._log_host(ip, f"✗ {check['message']}", "error")
                    err += 1
                    self._set_progress(idx + 1)
                    self._set_status_bar(f"Progreso: {idx+1}/{total_final} — ✓ {ok}  ✗ {err}  ⊘ {skipped}")
                    continue

                if check["skip"]:
                    # Host inaccesible o SSH cerrado
                    badge_state = "no_ssh" if check["reachable"] else "unreachable"
                    self.after(0, lambda b=badge, s=badge_state: b.set(s))
                    self._log_host(ip, f"✗ {check['message']}", "error")
                    err += 1
                    self._set_progress(idx + 1)
                    self._set_status_bar(f"Progreso: {idx+1}/{total_final} — ✓ {ok}  ✗ {err}  ⊘ {skipped}")
                    continue

                self._log_host(ip, f"✓ Puerto SSH/22 accesible. Iniciando conexión...", "success")
                self.after(0, lambda b=badge: b.set("running"))

                # ── 3. Intento de backup con reintentos ─────────
                MAX_RETRIES = 2
                result      = None

                for attempt in range(1, MAX_RETRIES + 1):
                    if attempt > 1:
                        self.after(0, lambda b=badge: b.set("retrying"))
                        self._log_host(ip,
                            f"↻ Reintento {attempt}/{MAX_RETRIES} "
                            f"(esperando 5s)...", "warning")
                        time.sleep(5)

                    result = backup_device(
                        host=ip, username=username, password=password,
                        secret=enable, output_dir=self._output_dir.get(),
                        log_callback=self._log_host, timeout=timeout
                    )

                    if result["success"]:
                        break  # Éxito — no reintentar

                    # Si el error es de autenticación no tiene sentido reintentar
                    msg_lower = result["message"].lower()
                    if any(k in msg_lower for k in
                           ["autenticación", "authentication", "password", "credential"]):
                        self._log_host(ip,
                            "Error de credenciales — no se reintentará.", "error")
                        break

                # ── 4. Registrar resultado final ────────────────
                if result and result["success"]:
                    ok += 1
                    self.after(0, lambda b=badge: b.set("success"))
                else:
                    err += 1
                    self.after(0, lambda b=badge: b.set("error"))

                self._set_progress(idx + 1)
                self._set_status_bar(
                    f"Progreso: {idx+1}/{total_final} — ✓ {ok}  ✗ {err}  ⊘ {skipped}"
                )

            # ── 5. Resumen final ─────────────────────────────────
            self._log("=" * 60, "dim")
            summary = (
                f"COMPLETADO: ✓ {ok} exitosos  "
                f"✗ {err} fallidos  "
                f"⊘ {skipped} omitidos  "
                f"de {total} total."
            )
            level = "success" if err == 0 and skipped == 0 else "warning"
            self._log(summary, level)
            self._set_status_bar(
                f"Finalizado: ✓ {ok} exitosos  ✗ {err} fallidos  ⊘ {skipped} omitidos"
            )
            self.after(0, lambda: self.btn_start.config(
                state="normal", text="▶  INICIAR RESPALDOS"))
            self._running = False

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _check_queue(self):
        """Procesa mensajes del queue (por si se necesita en extensiones)."""
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass
        self.after(100, self._check_queue)


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CiscoBackupApp()
    app.mainloop()

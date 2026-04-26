# Cisco Switch Backup Tool v1

Herramienta gráfica profesional desarrollada en Python para la automatización de respaldos de configuración (`running-config`) en dispositivos Cisco Catalyst mediante el protocolo SSH.

## 🚀 Características
* **Compatibilidad:** Diseñado para series Catalyst 2960, 3560, 9200 y 9300.
* **Pre-checks Inteligentes:** Realiza validaciones de IP, pruebas de puerto TCP 22 y ping ICMP antes de intentar la conexión para optimizar el tiempo.
* **Interfaz Moderna:** GUI intuitiva desarrollada con Tkinter con soporte para temas oscuros.
* **Gestión Masiva:** Permite agregar dispositivos manualmente o importar una lista desde archivos `.txt`.
* **Seguridad:** Manejo seguro de credenciales SSH y contraseñas de modo privilegiado (Enable).
* **Monitor SNMP:** Incluye una interfaz base para monitoreo de red (requiere módulo adicional).

## 📋 Requisitos
* Python 3.10 o superior.
* Librería **Netmiko** para la gestión de conexiones SSH.
* Librería **tkinter** para el GUI.

## 🔧 Instalación
1. Clona el repositorio:
   ```bash
   git clone [https://github.com/Redes2026/cisco-switch-backup-tool.git](https://github.com/TU_USUARIO/cisco-switch-backup-tool.git)


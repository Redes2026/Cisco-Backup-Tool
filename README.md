# Cisco Switch Backup Tool v1.2

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Esta herramienta automatiza la recolección de archivos de configuración (`running-config`) de switches Cisco Catalyst, proporcionando una interfaz gráfica intuitiva y robusta para administradores de red.

## 🚀 Características Principales
* **Pre-validación Inteligente:** Antes de conectar, el script verifica la validez de la IP, realiza un ping ICMP y comprueba la disponibilidad del puerto TCP 22 (SSH) para evitar esperas innecesarias por timeouts.
* **Interfaz Multitarea:** Implementa hilos (`threading`) para asegurar que la interfaz gráfica no se bloquee durante el proceso de respaldo masivo.
* **Gestión de Lotes:** Soporte para agregar dispositivos manualmente o mediante la importación de archivos de texto con listas de IPs.
* **Log en Tiempo Real:** Consola integrada con códigos de colores para monitorear el estado de cada conexión y posibles errores de autenticación o red.
* **Nomenclatura Automática:** Los archivos se guardan automáticamente con el formato `Hostname_IP_Fecha_Hora.txt`.

## 🛠️ Requisitos Técnicos
* **Python 3.10+**
* **Bibliotecas:** * `netmiko` (Manejo de SSH)
  * `tkinter` (Interfaz gráfica)

## 🔧 Instalación y Configuración

1. Clona este repositorio:
   ```bash
   git clone [https://github.com/Redes2026/Cisco-Backup-Tool.git](https://github.com/Redes2026/Cisco-Backup-Tool.git)

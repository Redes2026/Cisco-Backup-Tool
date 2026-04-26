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

2. Instala las dependencias:
    ```bash
    pip install netmiko
    pip install tkinter

3. Ejecuta la aplicación:
    ```bash
    python3 cisco_backup_toolv1.1.py

📋 Compatibilidad Probada

La herramienta ha sido diseñada pensando en la estabilidad de equipos Cisco Catalyst, incluyendo las series:

    Catalyst 2960 / 3560 / 3750

    Catalyst 9200 / 9300

🤝 Contribuciones

Las sugerencias para mejorar el manejo de errores o añadir soporte para otros fabricantes son bienvenidas. Por favor, abre un "Issue" o envía un "Pull Request".
📄 Licencia

Este proyecto está bajo la Licencia MIT.

Desarrollado por:
Alberto Arellano A.
Ingeniero en Electrónica y Computación | Magister en Informática Aplicada
Cisco Certified Instructor

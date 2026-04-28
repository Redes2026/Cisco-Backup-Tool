# Cisco Backup Tool | Automated Network Configuration Backup with Python

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Herramienta de automatización para respaldo de configuraciones en dispositivos Cisco IOS/IOS-XE usando Python y SSH, diseñada para entornos de redes empresariales y laboratorios de simulación.

<img width="1106" height="845" alt="imagen" src="https://github.com/user-attachments/assets/55efda2d-c85f-49d0-9c59-3b3253d02ba6" />


## 🚀 Características Principales
* **Backup automático de running-config**
* **Soporte multi-dispositivo**
* **Conexión SSH segura**
* **Pre-validación Inteligente:** Antes de conectar, el script verifica la validez de la IP, realiza un ping ICMP y comprueba la disponibilidad del puerto TCP 22 (SSH) para evitar esperas innecesarias por timeouts.
* **Interfaz Multitarea:** Implementa hilos (`threading`) para asegurar que la interfaz gráfica no se bloquee durante el proceso de respaldo masivo.
* **Gestión de Lotes:** Soporte para agregar dispositivos manualmente o mediante la importación de archivos de texto con listas de IPs.
* **Log en Tiempo Real:** Consola integrada con códigos de colores para monitorear el estado de cada conexión y posibles errores de autenticación o red.
* **Nomenclatura Automática:** Los archivos se guardan automáticamente con el formato `Hostname_IP_Fecha_Hora.txt`.
* **Preparado para entornos de laboratorio y producción**

## 🛠️ Requisitos Técnicos
* **Python 3.10+**
* **Bibliotecas:**
  * `netmiko` (Manejo de SSH)
  * `tkinter` (Interfaz gráfica)
  * `scrapli` (Mejora Conexión)

## 🔧 Instalación y Configuración

1. Clona este repositorio:
   ```bash
   git clone https://github.com/Redes2026/Cisco-Backup-Tool.git

2. Instala las dependencias:
    ```bash
    pip install netmiko
    pip install tkinter
    pip install scrapli scrapli-community

🛠️ Uso

 1. Ejecuta el script principal:
    ```bash
    python3 cisco_backup_toolv1.1.py

2. Ingresa tus credenciales SSH (Usuario, Password y Enable Password).

3. Agrega las IPs de tus switches o importa un archivo de texto.

4. Selecciona la carpeta de destino y presiona "Iniciar Respaldos".


🤝 Contribuciones

Las sugerencias para mejorar el manejo de errores o añadir soporte para otros fabricantes son bienvenidas. Por favor, abre un "Issue" o envía un "Pull Request".
📄 Licencia

Este proyecto está bajo la Licencia MIT.

👤 Autor

Alberto Arellano A.
Cisco Certified Instructor (CCNA/CCNP/Automation/Network Security).
Especialista en Networking, Automatización con Python/Ansible y Redes MPLS.

Nota: Esta herramienta se proporciona para fines educativos y administrativos. Siempre verifica el acceso SSH en tus dispositivos.

# InkPOS — Sistema POS y Gestión de Inventario para Papelería AJ

[![Django](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.8-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

---

## 📌 Contexto del Negocio y Problemática

**Papelería AJ** es una microempresa comercial que históricamente ha operado bajo un esquema de registro totalmente manual (libretas, notas en papel y cálculo mental). Esta forma de trabajo genera fricción operativa diaria que impacta la salud financiera y la continuidad del negocio:

* **Descuadres de Caja:** Discrepancias constantes entre el efectivo/dinero recaudado al final de la jornada y los comprobantes o registros manuales de venta.
* **Descuadres de Inventario:** Carencia de certeza sobre el stock real disponible en anaqueles y bodega; pérdidas no identificadas y riesgo de roturas de stock.
* **Decisiones de Reabastecimiento Empíricas:** Las compras a proveedores se realizan por percepción o urgencia inmediata, en lugar de apoyarse en métricas históricas de rotación de productos.

### ¿A quién afecta?

1. **Al Administrador:** Pérdida de visibilidad y control sobre el estado financiero, flujo de caja y nivel de existencias; dificultades para proyectar compras e inversiones.
2. **A los Empleados/Cajeros:** Sobrecarga de trabajo al tener que calcular y registrar transacciones sin una herramienta digital que valide precios, disponibilidad o totalizaciones.
3. **Al Negocio:** Riesgo directo sobre la sostenibilidad, rentabilidad y escalabilidad de la papelería.

---

## 🎯 Propósito del Sistema

**InkPOS** nace con el objetivo de centralizar, automatizar y digitalizar el ciclo operativo de **Papelería AJ**:

* Garantizar **trazabilidad completa** de cada transacción comercial.
* Proporcionar información fidedigna y en **tiempo real** del inventario.
* Automatizar el descuento de existencias con cada venta efectuada.
* Recopilar datos históricos para respaldar decisiones estratégicas de compra y rotación.

---

## 👥 Roles de Usuario y Control de Acceso

El sistema implementa control de acceso basado en roles (RBAC) con interfaces y permisos diferenciados:

| Rol | Alcance y Permisos |
| :--- | :--- |
| **Administrador** (`is_staff` / `es_admin`) | Control integral del sistema: gestión de catálogo de productos (creación, edición, eliminación, ajuste de precios/stock), reportes analíticos de ventas, administración de empleados, auditoría de facturas y configuración general. |
| **Empleado / Cajero** | Acceso operativo centrado en la atención al cliente: punto de venta (POS) para emisión de facturas, búsqueda y visualización de disponibilidad de productos en tiempo real y registro de devoluciones. |

> **Nota:** La aplicación redirige de manera automática según el rol al iniciar sesión: los administradores acceden al panel de **Reportes/Gestión**, mientras que los empleados son dirigidos directamente al módulo de **Ventas (POS)**.

---

## 🚀 Alcance de la Versión Inicial (Fase 1)

1. **Gestión de Inventario y Productos:**
   * Catálogo de productos con código único incremental autogenerado (`001`, `002`...).
   * Control de stock mínimo, precio unitario y nombre comercial.
   * Filtros y ordenamiento dinámico por stock y precio.
   * Modales de registro con validaciones visuales instantáneas en interfaz.
2. **Punto de Venta (POS) y Facturación:**
   * Búsqueda ágil de artículos por código o nombre.
   * Identificación del cliente (asociado a documento de identidad).
   * Generación de comprobantes y detalle de factura (`DetalleFactura`).
   * Deducción automática e inmediata de unidades del inventario tras concretar la venta.
3. **Módulo de Autenticación y Asistente de Inicio (Setup Wizard):**
   * Detección automática del estado del sistema: si no existe ningún administrador registrado, se activa una pantalla de configuración inicial guiada (`Setup`).
   * Validación estricta de credenciales y cierre seguro de sesión.
4. **Administración de Empleados y Clientes:**
   * Registro de personal con asignación de rol, salario y teléfono de contacto.
   * Base de datos de clientes recurrentes para facturación personalizada.

---

## 🏗️ Arquitectura y Estructura del Proyecto

El proyecto está desarrollado sobre **Django 6.1** siguiendo una arquitectura modular basada en aplicaciones desacopladas:

```text
ink-pos/
├── core/                       # Configuración global del proyecto (settings, urls, wsgi)
├── app_autenticacion/          # Login, logout y asistente inicial de configuración (Setup)
├── app_productos/              # Catálogo, formularios, ordenamiento y control de stock
├── app_ventas/                 # Punto de venta (POS), facturación, detalles y devoluciones
├── app_empleados/              # Gestión de usuarios, perfiles de empleados y salarios
├── app_clientes/               # Gestión de cartera de clientes para facturas
├── app_common/                 # Utilidades comunes, formularios base estilizados con Bootstrap
├── static/                     # Archivos estáticos (JavaScript, CSS, assets SVG)
│   └── js/FormValidationIntercept.js  # Interceptor dinámico de validaciones frontend
├── templates/                  # Plantillas base (Master.html, Navbar.html) y componentes
├── Dockerfile                  # Imagen Docker optimizada (Python 3.14-slim)
├── docker-compose.yml          # Orquestación de servicios (Django App + PostgreSQL)
├── Entrypoint.sh               # Script de inicio con espera de base de datos y migraciones
├── requirements.txt            # Dependencias del proyecto
└── pyproject.toml              # Configuración de linters, formateadores y cobertura de pruebas
```

---

## 🛠️ Stack Tecnológico

* **Backend:** Python 3.13 / 3.14, Django 6.1, Gunicorn.
* **Frontend:** Django Templates (DTL), HTML5, CSS3, Bootstrap 5.3.8 (Modo oscuro nativo), Bootstrap Icons 1.13.1, JavaScript vanilla.
* **Base de Datos:**
  * **Desarrollo:** SQLite3 (activación automática en modo `DEBUG=True`).
  * **Producción:** PostgreSQL (mediante servicio contenerizado o `DATABASE_URL`).
* **DevOps & Despliegue:** Docker, Docker Compose, soporte para redes seguras privadas (NetBird / Reverse Proxy).
* **Calidad y Estándares de Código:** Black, Flake8, isort, Mypy con `django-stubs`, Coverage con umbral mínimo configurado del 90%.

---

## ⚙️ Instalación y Puesta en Marcha

### Prerrequisitos

* Python 3.13 o superior instalado.
* Git.
* (Opcional) Docker y Docker Compose para despliegue en contenedores.

---

### Opción A: Entorno Local (Desarrollo)

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/EmmanuelMG7/ink-pos.git
   cd ink-pos
   ```

2. **Crear y activar un entorno virtual:**
   * En Windows (PowerShell):

     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

   * En Linux / macOS:

     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias:**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Aplicar migraciones de la base de datos:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Iniciar el servidor de desarrollo:**

   ```bash
   python manage.py runserver
   ```

6. **Primer uso y configuración:**
   * Abre tu navegador en `http://127.0.0.1:8000/`.
   * Si es la primera ejecución, el sistema te redirigirá a `/auth/setup/` para crear el primer **Usuario Administrador**.
   * Una vez creado, inicia sesión y accede a todas las funciones administrativas.

---

### Opción B: Ejecución con Docker Compose (Producción / Staging)

1. **Configurar variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto tomando como base las variables requeridas:

   ```env
   SECRET_KEY=tu_clave_secreta_segura
   DEBUG=False
   ALLOWED_HOSTS=localhost,127.0.0.1
   DB_NAME=inkpos_db
   DB_USER=postgres
   DB_PASSWORD=tu_password_seguro
   PROXY_HOSTNAME=pos.papeleriaaj.local
   WEB_PROXY_IP=10.0.0.50
   ```

2. **Compilar y levantar los contenedores:**

   ```bash
   docker compose up -d --build
   ```

   El contenedor ejecutará automáticamente:
   * Verificación de disponibilidad de PostgreSQL (`pg_isready`).
   * Aplicación de migraciones (`python manage.py migrate`).
   * Recolección de archivos estáticos (`python manage.py collectstatic`).
   * Inicio del servidor de aplicaciones con **Gunicorn**.

---

## 🧪 Calidad de Código y Pruebas

El proyecto cuenta con herramientas para garantizar alta calidad y mantenibilidad del software:

* **Ejecutar pruebas unitarias con cobertura:**

  ```bash
  coverage run -m django test --settings=core.settings
  coverage report -m
  ```

* **Formateo y orden de importaciones:**

  ```bash
  black .
  isort .
  ```

* **Análisis estático y tipado:**

  ```bash
  flake8
  mypy .
  ```

---

## 🗺️ Roadmap y Mejoras Futuras

* [ ] Generación e impresión de recibos y facturas en formato POS (ticket térmico de 58mm/80mm).
* [ ] Exportación de reportes de ventas diarias, semanales y mensuales en formato Excel (XLSX) y PDF.
* [ ] Alertas visuales y notificaciones por correo de stock crítico o próximo a agotarse.
* [ ] Módulo de control de apertura y cierre de caja chica (Turnos de trabajo / Arqueo de caja).
* [ ] Lector de código de barras físico compatible con el buscador del POS.
* [ ] Facturación electrónica según la normativa fiscal correspondiente.

---

## 📄 Licencia

Este proyecto ha sido desarrollado a medida para **Papelería AJ** como solución a su transformación digital y optimización operativa. Todos los derechos reservados.

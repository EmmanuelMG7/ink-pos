from django import forms
from django.contrib.auth.models import User
from django.template import Context, Template
from django.test import TestCase
from django.utils.translation import activate, get_language
from django.utils.translation import gettext as _

from app_autenticacion.forms import LoginForm, SetupAdminForm
from app_common.forms import BootstrapForm, BootstrapModelForm
from app_empleados.forms import EmpleadoForm
from app_empleados.models import Empleado
from app_inventario.forms import ProductoForm


class I18nTranslationsTests(TestCase):
    """Pruebas del sistema de internacionalización (i18n) y traducciones de InkPOS."""

    def setUp(self):
        activate("es")

    def test_default_language_is_spanish(self):
        """Verifica que el idioma activo por defecto sea español."""
        self.assertEqual(get_language(), "es")

    def test_explicit_model_and_form_keys_in_spanish(self):
        """Verifica que las claves explícitas models.* y form.* se traduzcan en español."""
        activate("es")
        keys_map = {
            "models.empleado.field.salario": "Salario",
            "models.empleado.field.identificacion": "Identificación",
            "models.empleado.field.telefono": "Teléfono",
            "models.cliente.field.identificacion": "Identificación",
            "models.cliente.field.direccion": "Dirección",
            "models.producto.field.precio_venta": "Precio de venta",
            "models.producto.field.costo_compra": "Costo de compra",
            "form.login.field.usuario": "Usuario",
            "form.login.field.contrasena": "Contraseña",
            "form.empleado.field.nombre": "Nombre",
            "form.producto.field.codigo": "Código",
        }
        for key, expected in keys_map.items():
            with self.subTest(key=key):
                self.assertEqual(_(key), expected)

    def test_explicit_model_and_form_keys_in_english(self):
        """Verifica que las claves explícitas models.* y form.* se traduzcan en inglés."""
        activate("en")
        keys_map = {
            "models.empleado.field.salario": "Salary",
            "models.empleado.field.identificacion": "Identification",
            "models.empleado.field.telefono": "Phone",
            "models.cliente.field.identificacion": "Identification",
            "models.cliente.field.direccion": "Address",
            "models.producto.field.precio_venta": "Sale Price",
            "models.producto.field.costo_compra": "Purchase Cost",
            "form.login.field.usuario": "Username",
            "form.login.field.contrasena": "Password",
            "form.empleado.field.nombre": "Name",
            "form.producto.field.codigo": "Code",
        }
        for key, expected in keys_map.items():
            with self.subTest(key=key):
                self.assertEqual(_(key), expected)

    def test_default_and_custom_error_messages_keys_in_spanish(self):
        """Verifica que las claves de error por defecto y personalizadas se traduzcan en español."""
        activate("es")
        errors_map = {
            "form.default.errormsg.required": "Este campo es obligatorio.",
            "form.default.errormsg.invalid": "Por favor ingresa un valor válido.",
            "form.default.errormsg.empty": "Este campo no puede estar vacío.",
            "form.login.errormsg.usuario.required": "El campo usuario es obligatorio.",
            "form.login.errormsg.contrasena.required": "El campo contraseña es obligatorio.",
            "form.producto.errormsg.nombre.unique": "Ya existe un producto con este nombre.",
        }
        for key, expected in errors_map.items():
            with self.subTest(key=key):
                self.assertEqual(_(key), expected)

    def test_default_and_custom_error_messages_keys_in_english(self):
        """Verifica que las claves de error por defecto y personalizadas se traduzcan en inglés."""
        activate("en")
        errors_map = {
            "form.default.errormsg.required": "This field is required.",
            "form.default.errormsg.invalid": "Please enter a valid value.",
            "form.default.errormsg.empty": "This field cannot be empty.",
            "form.login.errormsg.usuario.required": "The username field is required.",
            "form.login.errormsg.contrasena.required": "The password field is required.",
            "form.producto.errormsg.nombre.unique": "A product with this name already exists.",
        }
        for key, expected in errors_map.items():
            with self.subTest(key=key):
                self.assertEqual(_(key), expected)

    def test_bootstrap_form_uses_default_errormsg_keys(self):
        """
        Verifica el principio DRY y KISS:
        BootstrapForm aplica directamente form.default.errormsg.<tipo_error>
        sin generar claves dinámicas intermedias.
        """
        activate("es")

        class SimpleForm(BootstrapForm):
            campo_comun = forms.CharField(required=True)

        form = SimpleForm()
        self.assertEqual(
            str(form.fields["campo_comun"].error_messages["required"]),
            "Este campo es obligatorio.",
        )
        self.assertEqual(
            str(form.fields["campo_comun"].widget.attrs.get("data-required-feedback")),
            "Este campo es obligatorio.",
        )

        activate("en")
        form_en = SimpleForm()
        self.assertEqual(
            str(form_en.fields["campo_comun"].error_messages["required"]),
            "This field is required.",
        )
        self.assertEqual(
            str(form_en.fields["campo_comun"].widget.attrs.get("data-required-feedback")),
            "This field is required.",
        )

    def test_missing_translation_key_exposes_bug_evidently(self):
        """Si falta una clave, gettext retorna el identificador exacto exponiendo el error."""
        activate("es")
        clave_inexistente = "models.empleado.field.campo_que_no_existe"
        self.assertEqual(_(clave_inexistente), clave_inexistente)

    def test_form_can_override_model_field_label_with_form_key(self):
        """
        Verifica que un formulario pueda sobreescribir la frase de un campo del modelo
        asociándolo a su clave específica form.<nombre_form>.field.<campo>.
        """
        activate("es")

        class FormPersonalizado(BootstrapModelForm):
            class Meta:
                model = Empleado
                fields = ["salario"]
                labels = {
                    "salario": _("form.personalizado.field.salario"),
                }

        form = FormPersonalizado()
        # Si la clave específica del formulario no existe en .po, expone la clave del formulario
        self.assertEqual(str(form.fields["salario"].label), "form.personalizado.field.salario")

    def test_real_forms_labels_and_placeholders_orthography_spanish(self):
        """Verifica que los formularios reales tengan ortografía y tildes correctas en español."""
        activate("es")
        login_form = LoginForm()
        self.assertEqual(str(login_form.fields["usuario"].label), "Usuario")
        self.assertEqual(str(login_form.fields["contrasena"].label), "Contraseña")
        self.assertEqual(
            login_form.fields["usuario"].widget.attrs.get("placeholder"),
            "Usuario",
        )
        self.assertEqual(
            login_form.fields["contrasena"].widget.attrs.get("placeholder"),
            "Contraseña",
        )

        empleado_form = EmpleadoForm()
        self.assertEqual(str(empleado_form.fields["nombre"].label), "Nombre")
        self.assertEqual(str(empleado_form.fields["usuario"].label), "Usuario")
        self.assertEqual(str(empleado_form.fields["contrasena"].label), "Contraseña")
        self.assertEqual(str(empleado_form.fields["identificacion"].label), "Identificación")
        self.assertEqual(str(empleado_form.fields["telefono"].label), "Teléfono")
        self.assertEqual(
            empleado_form.fields["identificacion"].widget.attrs.get("placeholder"),
            "Identificación",
        )
        self.assertEqual(
            empleado_form.fields["telefono"].widget.attrs.get("placeholder"),
            "Teléfono",
        )

        setup_form = SetupAdminForm()
        self.assertEqual(str(setup_form.fields["identificacion"].label), "Identificación")
        self.assertEqual(str(setup_form.fields["usuario"].label), "Usuario")
        self.assertEqual(str(setup_form.fields["telefono"].label), "Teléfono")
        self.assertEqual(str(setup_form.fields["contrasena"].label), "Contraseña")

        producto_form = ProductoForm()
        self.assertEqual(str(producto_form.fields["codigo"].label), "Código")
        self.assertEqual(str(producto_form.fields["nombre"].label), "Nombre")
        self.assertEqual(str(producto_form.fields["precio_venta"].label), "Precio de venta")
        self.assertEqual(str(producto_form.fields["costo_compra"].label), "Costo de compra")
        self.assertEqual(str(producto_form.fields["stock_actual"].label), "Stock actual")
        self.assertEqual(str(producto_form.fields["stock_minimo"].label), "Stock mínimo")

    def test_real_forms_labels_and_placeholders_english(self):
        """Verifica que los formularios se traduzcan correctamente en inglés."""
        activate("en")
        login_form = LoginForm()
        self.assertEqual(str(login_form.fields["usuario"].label), "Username")
        self.assertEqual(str(login_form.fields["contrasena"].label), "Password")
        self.assertEqual(
            login_form.fields["usuario"].widget.attrs.get("placeholder"),
            "Username",
        )
        self.assertEqual(
            login_form.fields["contrasena"].widget.attrs.get("placeholder"),
            "Password",
        )

        empleado_form = EmpleadoForm()
        self.assertEqual(str(empleado_form.fields["nombre"].label), "Name")
        self.assertEqual(str(empleado_form.fields["usuario"].label), "Username")
        self.assertEqual(str(empleado_form.fields["contrasena"].label), "Password")
        self.assertEqual(str(empleado_form.fields["identificacion"].label), "Identification")
        self.assertEqual(str(empleado_form.fields["telefono"].label), "Phone")

    def test_kiss_bootstrap_form_sets_placeholder_from_label(self):
        """
        Verifica el principio KISS en BootstrapForm:
        El widget recibe automáticamente como placeholder el label traducido.
        """

        class FormularioSimple(BootstrapForm):
            codigo = forms.CharField(label=_("form.producto.field.codigo"))
            descripcion = forms.CharField(label=_("descripcion"))

        form = FormularioSimple()
        self.assertEqual(form.fields["codigo"].widget.attrs.get("placeholder"), "Código")
        self.assertEqual(form.fields["descripcion"].widget.attrs.get("placeholder"), "Descripción")

    def test_browser_with_english_header_renders_unmixed_english(self):
        """Verifica que un navegador en inglés reciba la página en inglés sin mezclar."""
        User.objects.create_user(username="admin_i18n", password="Password123*", is_staff=True)
        response = self.client.get("/auth/login/", headers={"accept-language": "en-US,en;q=0.9"})
        self.assertEqual(response.status_code, 200)

        # Campos y botones en inglés
        self.assertContains(response, 'placeholder="Username"')
        self.assertContains(response, 'placeholder="Password"')
        self.assertContains(response, "Log In")

        # Sin mezcla con español
        self.assertNotContains(response, 'placeholder="Usuario"')
        self.assertNotContains(response, 'placeholder="Contraseña"')
        self.assertNotContains(response, "Iniciar Sesión")

    def test_browser_with_spanish_header_renders_unmixed_spanish(self):
        """Verifica que un navegador en español reciba la página en español sin mezclar."""
        User.objects.create_user(username="admin_es", password="Password123*", is_staff=True)
        response = self.client.get("/auth/login/", headers={"accept-language": "es-ES,es;q=0.9"})
        self.assertEqual(response.status_code, 200)

        # Campos y botones en español con tildes correctas
        self.assertContains(response, 'placeholder="Usuario"')
        self.assertContains(response, 'placeholder="Contraseña"')
        self.assertContains(response, "Iniciar Sesión")

        # Sin mezcla con inglés
        self.assertNotContains(response, 'placeholder="Username"')
        self.assertNotContains(response, 'placeholder="Password"')
        self.assertNotContains(response, "Log In")

    def test_bootstrap_input_field_template_renders_translated_label(self):
        """Verifica que bootstrap_input_field renderice el label traducido con tilde."""

        class FormTemplateTest(BootstrapForm):
            identificacion = forms.CharField(label=_("models.empleado.field.identificacion"))

        form = FormTemplateTest()
        template = Template(
            "{% with field=form.identificacion %}"
            "{% include 'bootstrap_input_field.html' %}"
            "{% endwith %}"
        )
        rendered = template.render(Context({"form": form}))

        self.assertIn("Identificación", rendered)
        self.assertIn('placeholder="Identificación"', rendered)
        self.assertIn(
            '<label for="id_identificacion">\n      Identificación\n    </label>', rendered
        )

from unittest.mock import patch

from django import forms as dj_forms
from django.contrib.auth.models import User
from django.test import TestCase

from app_empleados.forms import EmpleadoForm
from app_empleados.models import Empleado


class EmpleadoFormTests(TestCase):
    def test_empleado_form_edicion_y_save_commit_false(self):
        """Prueba inicialización de formulario en edición y save con commit=False."""
        user = User.objects.create_user(
            username="empleadoedit",
            first_name="Luis",
            password="OldPassword123!",
        )
        empleado = Empleado.objects.create(
            auth_user=user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="44556677",
            telefono="3101112233",
        )

        # 1. Unbound form con instancia
        form_unbound = EmpleadoForm(instance=empleado)
        self.assertEqual(form_unbound.fields["usuario"].initial, "empleadoedit")
        self.assertEqual(form_unbound.fields["nombre"].initial, "Luis")
        self.assertFalse(form_unbound.fields["contrasena"].required)
        self.assertIsNotNone(form_unbound.admin_checkbox)

        # 2. Guardar en edición sin cambiar contraseña
        form_edit = EmpleadoForm(instance=empleado)
        form_edit.cleaned_data = {
            "usuario": "empleadoedit",
            "nombre": "Luis Editado",
            "es_admin": True,
            "contrasena": "",
        }
        inst_actualizada = form_edit.save(commit=True)
        self.assertEqual(inst_actualizada.auth_user.first_name, "Luis Editado")
        self.assertTrue(inst_actualizada.es_admin)

        # 3. Bound form editando con nueva contraseña y commit=False
        data_edit_pass = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "44556677",
            "usuario": "empleadoedit",
            "nombre": "Luis Final",
            "telefono": "3101112233",
            "contrasena": "NewPass123!",
            "admin_checkbox": "true",
        }
        form_edit_pass = EmpleadoForm(data=data_edit_pass, instance=empleado)
        self.assertTrue(form_edit_pass.is_valid())
        inst_no_commit = form_edit_pass.save(commit=False)
        self.assertEqual(inst_no_commit.auth_user.first_name, "Luis Final")
        self.assertTrue(inst_no_commit.auth_user.check_password("NewPass123!"))

        # 4. Error al cambiar a un usuario existente de otro empleado
        User.objects.create_user(username="otrouser", password="123")
        data_conflict = data_edit_pass.copy()
        data_conflict["usuario"] = "otrouser"
        form_conflict = EmpleadoForm(data=data_conflict, instance=empleado)
        self.assertFalse(form_conflict.is_valid())
        self.assertIn("usuario", form_conflict.errors)

        # 5. Cleaners con valores vacíos
        form_empty = EmpleadoForm()
        form_empty.cleaned_data = {
            "identificacion": None,
            "telefono": None,
            "usuario": None,
        }
        self.assertIsNone(form_empty.clean_identificacion())
        self.assertIsNone(form_empty.clean_telefono())
        self.assertIsNone(form_empty.clean_usuario())

        # 6. clean() con cleaned_data None
        form_none = EmpleadoForm()
        with patch.object(dj_forms.ModelForm, "clean", return_value=None):
            res = form_none.clean()
            self.assertEqual(res, {})

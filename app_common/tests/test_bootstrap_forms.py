from django import forms
from django.core.validators import RegexValidator
from django.test import TestCase

from app_common.forms.bootstrap import BootstrapForm, BootstrapModelForm
from app_common.forms.validators import (
    AlphanumericValidator,
    OnlyTextValidator,
    PasswordValidator,
    UsernameValidator,
)
from app_inventario.models import Categoria


class DummyForm(BootstrapForm):
    default_messages = {
        "required": "Campo requerido.",
        "invalid": "Invalido.",
        "valid": "Ignorado",
        "empty_code": "",
    }

    campo_tipo = forms.CharField(widget=forms.TextInput, required=False)
    campo_checkbox = forms.BooleanField(required=False)
    campo_radio = forms.ChoiceField(
        choices=[("a", "A"), ("b", "B")],
        widget=forms.RadioSelect,
        required=False,
    )
    campo_select = forms.ChoiceField(choices=[("1", "Uno")], required=False)
    campo_hidden = forms.CharField(widget=forms.HiddenInput, required=False)
    campo_feedback = forms.CharField(required=False)
    campo_regex_no_msg = forms.CharField(
        validators=[RegexValidator(r"^[0-9]+$")],
        required=False,
    )
    campo_regex_con_msg = forms.CharField(
        validators=[RegexValidator(r"^[a-z]+$", message="Solo minusculas.")],
        required=False,
    )
    campo_password = forms.CharField(
        validators=[PasswordValidator],
        widget=forms.PasswordInput,
        required=False,
    )
    campo_alpha = forms.CharField(
        validators=[AlphanumericValidator],
        required=False,
    )
    campo_text = forms.CharField(
        validators=[OnlyTextValidator],
        required=False,
    )
    campo_user = forms.CharField(
        validators=[UsernameValidator],
        required=False,
    )


class DummyModelForm(BootstrapModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre"]


class BootstrapFormTests(TestCase):
    def test_bootstrap_form_init_unbound(self):
        setattr(DummyForm.base_fields["campo_feedback"], "valid_feedback", "Dato correcto")
        form = DummyForm()

        # widget class type converted to instance
        self.assertIsInstance(form.fields["campo_tipo"].widget, forms.TextInput)
        self.assertIn("form-control", form.fields["campo_tipo"].widget.attrs["class"])

        # widgets styled properly
        self.assertIn("form-check-input", form.fields["campo_checkbox"].widget.attrs["class"])
        self.assertIn("form-check-input", form.fields["campo_radio"].widget.attrs["class"])
        self.assertIn("form-select", form.fields["campo_select"].widget.attrs["class"])

        # valid_feedback applied
        self.assertEqual(
            form.fields["campo_feedback"].widget.attrs.get("data-valid-feedback"),
            "Dato correcto",
        )

        # regex validators synced
        self.assertIn("password-complexity", form.fields["campo_password"].widget.attrs["class"])
        self.assertEqual(form.fields["campo_password"].widget.attrs.get("minlength"), "8")
        self.assertIn("alphanumeric-only", form.fields["campo_alpha"].widget.attrs["class"])
        self.assertIn("text-only", form.fields["campo_text"].widget.attrs["class"])
        self.assertIn("username-only", form.fields["campo_user"].widget.attrs["class"])
        self.assertEqual(
            form.fields["campo_regex_con_msg"].widget.attrs.get("data-invalid-feedback"),
            "Solo minusculas.",
        )
        self.assertIn(
            "data-invalid-feedback",
            form.fields["campo_regex_no_msg"].widget.attrs,
        )

    def test_bootstrap_form_bound_validation_states(self):
        # Bound form with invalid data
        form = DummyForm(data={"campo_regex_con_msg": "12345"})
        self.assertFalse(form.is_valid())
        self.assertIn("is-invalid", form.fields["campo_regex_con_msg"].widget.attrs["class"])

        # Field without error gets is-valid
        self.assertIn("is-valid", form.fields["campo_tipo"].widget.attrs["class"])

        # Transition: force an is-valid field to have errors and vice versa
        form.fields["campo_regex_con_msg"].widget.attrs["class"] += " is-valid"
        form.fields["campo_tipo"].widget.attrs["class"] += " is-invalid"
        form.aplicar_estados_bootstrap()

        clases_regex = form.fields["campo_regex_con_msg"].widget.attrs["class"].split()
        self.assertNotIn("is-valid", clases_regex)
        self.assertIn("is-invalid", clases_regex)
        clases_tipo = form.fields["campo_tipo"].widget.attrs["class"].split()
        self.assertNotIn("is-invalid", clases_tipo)
        self.assertIn("is-valid", clases_tipo)

    def test_bootstrap_model_form(self):
        mform = DummyModelForm(data={"nombre": "Bebidas"})
        self.assertTrue(mform.is_valid())
        self.assertIn("is-valid", mform.fields["nombre"].widget.attrs["class"])

    def test_bootstrap_form_widget_as_type(self):
        class FormConWidgetTipo(BootstrapForm):
            def __init__(self, *args, **kwargs):
                self.base_fields["custom"] = forms.Field()
                self.base_fields["custom"].widget = forms.TextInput
                super().__init__(*args, **kwargs)

        f = FormConWidgetTipo()
        self.assertIsInstance(f.fields["custom"].widget, forms.TextInput)

    def test_bootstrap_form_validator_sin_mensaje(self):
        val = RegexValidator(r"^[0-9]+$")
        val.message = None

        class FormRegexSinMsg(BootstrapForm):
            campo = forms.CharField(validators=[val], required=False)

        f = FormRegexSinMsg()
        self.assertIn("data-invalid-feedback", f.fields["campo"].widget.attrs)

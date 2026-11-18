import json
from unittest.mock import MagicMock

from django import forms
from django.http import QueryDict
from django.test import TestCase

from app_common.forms.fields import MultipleTagsField
from app_common.forms.widgets import MultipleHiddenWidget


class TestFormsFieldsWidgets(TestCase):
    def test_multiple_hidden_widget_render(self):
        widget = MultipleHiddenWidget()
        self.assertEqual(widget.render("test", ["val1", "val2"]), "")

    def test_multiple_hidden_widget_value_from_datadict(self):
        widget = MultipleHiddenWidget()

        # QueryDict with multiple values
        qdict = QueryDict(mutable=True)
        qdict.setlist("items", ["item1", "item2", "item3"])
        self.assertEqual(
            widget.value_from_datadict(qdict, {}, "items"),
            ["item1", "item2", "item3"],
        )

        # QueryDict with single value
        qdict_single = QueryDict(mutable=True)
        qdict_single.setlist("items", ["only_one"])
        self.assertEqual(
            widget.value_from_datadict(qdict_single, {}, "items"),
            "only_one",
        )

        # QueryDict with empty list
        qdict_empty = QueryDict(mutable=True)
        self.assertEqual(widget.value_from_datadict(qdict_empty, {}, "items"), [])

        # Standard dict fallback
        std_dict = {"items": ["a", "b"]}
        self.assertEqual(
            widget.value_from_datadict(std_dict, {}, "items"),
            ["a", "b"],
        )

    def test_multiple_tags_field_empty_values(self):
        field = MultipleTagsField()
        self.assertEqual(field.clean(None), [])
        self.assertEqual(field.clean(""), [])
        self.assertEqual(field.clean([]), [])
        self.assertEqual(field.clean("   "), [])

    def test_multiple_tags_field_list_input(self):
        field = MultipleTagsField()
        result = field.clean([" Lapiceros ", "Colores", "lapiceros", "Ninguna", "Cuadernos"])
        self.assertEqual(result, ["Lapiceros", "Colores", "Cuadernos"])

    def test_multiple_tags_field_comma_separated_string(self):
        field = MultipleTagsField()
        result = field.clean("Arte, Escolar, oficina, ARTE, ninguna")
        self.assertEqual(result, ["Arte", "Escolar", "oficina"])

    def test_multiple_tags_field_json_string(self):
        field = MultipleTagsField()
        json_str = json.dumps(["Ferretería", "Pinturas", "ferretería"])
        result = field.clean(json_str)
        self.assertEqual(result, ["Ferretería", "Pinturas"])

    def test_multiple_tags_field_objects_with_nombre(self):
        field = MultipleTagsField()
        obj1 = MagicMock(nombre="Cuadernos")
        obj2 = MagicMock(nombre="Libretas")
        obj3 = MagicMock(nombre="cuadernos")
        result = field.clean([obj1, obj2, obj3])
        self.assertEqual(result, ["Cuadernos", "Libretas"])

    def test_multiple_tags_field_custom_ignore_and_case_sensitive(self):
        field = MultipleTagsField(ignore_values=["omitir"], case_sensitive=True)
        result = field.clean(["TagA", "taga", "omitir", "OMITIR", "TagB"])
        self.assertEqual(result, ["TagA", "taga", "TagB"])

    def test_multiple_tags_field_in_form_with_querydict(self):
        class SampleForm(forms.Form):
            tags = MultipleTagsField()

        qdict = QueryDict(mutable=True)
        qdict.appendlist("tags", "Uno")
        qdict.appendlist("tags", "Dos")
        qdict.appendlist("tags", "uno")

        form = SampleForm(data=qdict)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["tags"], ["Uno", "Dos"])

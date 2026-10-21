import json
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_datetime
from django_tables2 import RequestConfig

from app_common.cards.exceptions import CardError
from app_common.cards.registry import card_registry
from app_inventario.models import Categoria, Producto

from .models import AccionPromocion, ReglaPromocion
from .tables import PromocionTable


@login_required
@permission_required("app_promociones.view_reglapromocion", raise_exception=True)
def gestion_promociones(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        if not request.user.has_perm("app_promociones.add_reglapromocion"):
            raise PermissionDenied("No tienes permisos para crear promociones.")

        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        es_cupon = request.POST.get("es_cupon") in ("true", "1", "on")
        codigo_cupon_raw = request.POST.get("codigo_cupon", "").strip().upper()
        codigo_cupon = codigo_cupon_raw if (es_cupon and codigo_cupon_raw) else None
        es_acumulable = request.POST.get("es_acumulable") in ("true", "1", "on")
        raw_cards_str = request.POST.get("cards_payload", "[]")

        if not nombre:
            messages.error(request, "El nombre de la promoción es obligatorio.")
            return redirect("promociones:gestion")

        if es_cupon and not codigo_cupon:
            messages.error(request, "Debe especificar un código para el cupón promocional.")
            return redirect("promociones:gestion")

        if codigo_cupon and ReglaPromocion.objects.filter(codigo_cupon=codigo_cupon).exists():
            messages.error(
                request,
                f"Ya existe una promoción registrada con el código de cupón '{codigo_cupon}'.",
            )
            return redirect("promociones:gestion")

        try:
            cards_list: list[dict[str, Any]] = json.loads(raw_cards_str)
        except json.JSONDecodeError:
            cards_list = []

        conditions = [c for c in cards_list if c.get("card_id", "").startswith("cond_")]
        actions = [c for c in cards_list if c.get("card_id", "").startswith("act_")]
        limits = [c for c in cards_list if c.get("card_id", "").startswith("lim_")]

        if not actions:
            messages.error(request, "Debe configurar al menos un beneficio o acción.")
            return redirect("promociones:gestion")

        try:
            expresion_condicion = card_registry.compile_conditions(conditions)
        except CardError as exc:
            messages.error(request, f"Error en las condiciones: {exc}")
            return redirect("promociones:gestion")

        limits_dict: dict[str, Any] = {}
        for lim_conf in limits:
            card_id = lim_conf.get("card_id")
            if card_id:
                try:
                    lim_cls = card_registry.get_card(card_id)
                    lim_data = lim_cls.to_limit_data(lim_conf)
                    for k, v in lim_data.items():
                        if k in ("fecha_inicio", "fecha_fin") and isinstance(v, str) and v:
                            limits_dict[k] = parse_datetime(v) or v
                        else:
                            limits_dict[k] = v
                except CardError as exc:
                    messages.error(request, f"Error en límites: {exc}")
                    return redirect("promociones:gestion")

        try:
            with transaction.atomic():
                regla = ReglaPromocion(
                    nombre=nombre,
                    descripcion=descripcion,
                    es_cupon=es_cupon,
                    codigo_cupon=codigo_cupon,
                    es_acumulable=es_acumulable,
                    expresion_condicion=expresion_condicion,
                    config_tarjetas=cards_list,
                    **limits_dict,
                )
                regla.full_clean()
                regla.save()

                for act_conf in actions:
                    act_id = act_conf.get("card_id")
                    if act_id:
                        act_cls = card_registry.get_card(act_id)
                        act_data = act_cls.to_action_data(act_conf)
                        accion = AccionPromocion(regla_promocion=regla, **act_data)
                        accion.full_clean()
                        accion.save()

            messages.success(request, f'Promoción "{nombre}" configurada exitosamente.')
            return redirect("promociones:gestion")

        except ValidationError as exc:
            messages.error(request, f"Error de validación al crear la promoción: {exc}")
            return redirect("promociones:gestion")
        except Exception as exc:
            messages.error(request, f"Ocurrió un error inesperado: {exc}")
            return redirect("promociones:gestion")

    # Solicitud GET
    promociones = (
        ReglaPromocion.objects.all().prefetch_related("acciones").order_by("-fecha_creacion")
    )
    tabla = PromocionTable(promociones)
    RequestConfig(request, paginate={"per_page": 10}).configure(tabla)

    categorias = Categoria.objects.all().order_by("nombre")
    productos = Producto.objects.filter(activo=True).order_by("nombre")

    return render(
        request,
        "promociones/Gestion_Promociones.html",
        {
            "table": tabla,
            "categorias": categorias,
            "productos": productos,
        },
    )

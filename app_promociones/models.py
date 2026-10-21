from decimal import Decimal

import rule_engine
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from app_inventario.models import Categoria, Producto
from app_ventas.models import Factura


class ReglaPromocion(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, default="")
    es_cupon = models.BooleanField(default=False)
    codigo_cupon = models.CharField(max_length=50, blank=True, null=True, unique=True)
    es_acumulable = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    expresion_condicion = models.TextField(default="true")

    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    limite_usos_total = models.PositiveIntegerField(null=True, blank=True)
    veces_usado = models.PositiveIntegerField(default=0)
    limite_usos_por_cliente = models.PositiveIntegerField(null=True, blank=True)

    config_tarjetas = models.JSONField(default=list, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Regla de Promoción"
        verbose_name_plural = "Reglas de Promoción"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_regla_nombre_no_vacio",
            ),
            models.CheckConstraint(
                condition=models.Q(veces_usado__gte=0),
                name="chk_regla_veces_usado_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(limite_usos_total__isnull=True)
                | models.Q(limite_usos_total__gt=0),
                name="chk_regla_limite_usos_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(limite_usos_total__isnull=True)
                | models.Q(veces_usado__lte=models.F("limite_usos_total")),
                name="chk_regla_usos_no_superan_limite",
            ),
            models.CheckConstraint(
                condition=models.Q(limite_usos_por_cliente__isnull=True)
                | models.Q(limite_usos_por_cliente__gt=0),
                name="chk_regla_limite_cliente_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_fin__isnull=True)
                | models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="chk_regla_vigencia_fechas",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre de la regla no puede estar vacío."})

        if self.es_cupon:
            if not self.codigo_cupon or not self.codigo_cupon.strip():
                raise ValidationError(
                    {"codigo_cupon": "Debe definir un código para la promoción de tipo cupón."}
                )
            self.codigo_cupon = self.codigo_cupon.strip().upper()
        else:
            self.codigo_cupon = None

        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha final de vigencia no puede ser anterior a la inicial."}
            )

        if self.limite_usos_total is not None:
            if self.limite_usos_total <= 0:
                raise ValidationError(
                    {"limite_usos_total": "El límite de usos debe ser mayor a cero."}
                )
            if self.veces_usado > self.limite_usos_total:
                raise ValidationError(
                    {"veces_usado": "Las veces usado no pueden superar el límite de usos total."}
                )

        if self.limite_usos_por_cliente is not None and self.limite_usos_por_cliente <= 0:
            raise ValidationError(
                {"limite_usos_por_cliente": "El límite por cliente debe ser mayor a cero."}
            )

        # Validación sintáctica con rule-engine
        if self.expresion_condicion and self.expresion_condicion.strip():
            try:
                rule_engine.Rule(self.expresion_condicion.strip())
            except Exception as exc:
                msg = f"Expresión inválida para rule-engine: {exc}"
                raise ValidationError({"expresion_condicion": msg})

    def save(self, *args, skip_clean: bool = False, **kwargs) -> None:
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        tag = f" [Cupón: {self.codigo_cupon}]" if self.es_cupon else ""
        return f"{self.nombre}{tag}"


class AccionPromocion(models.Model):
    class TipoAccion(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje (%)"
        MONTO_FIJO = "MONTO_FIJO", "Monto Fijo ($)"
        ITEM_REGALO = "ITEM_REGALO", "Producto de Regalo"

    class AlcanceAccion(models.TextChoices):
        CARRITO = "CARRITO", "A todo el carrito"
        CATEGORIA = "CATEGORIA", "A categoría específica"
        PRODUCTO = "PRODUCTO", "A producto específico"
        ITEM_MAS_BARATO = "ITEM_MAS_BARATO", "Al ítem de menor valor"
        ITEM_MAS_CARO = "ITEM_MAS_CARO", "Al ítem de mayor valor"

    regla_promocion = models.ForeignKey(
        ReglaPromocion,
        on_delete=models.CASCADE,
        related_name="acciones",
    )
    orden = models.PositiveSmallIntegerField(default=1)
    tipo_accion = models.CharField(
        max_length=20,
        choices=TipoAccion.choices,
        default=TipoAccion.PORCENTAJE,
    )
    alcance_accion = models.CharField(
        max_length=20,
        choices=AlcanceAccion.choices,
        default=AlcanceAccion.CARRITO,
    )
    valor_accion = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tope_maximo_descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    categoria_objetivo = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acciones_promocion",
    )
    producto_objetivo = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acciones_promocion_objetivo",
    )
    producto_regalo = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acciones_promocion_regalo",
    )
    cantidad_regalo = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Acción de Promoción"
        verbose_name_plural = "Acciones de Promoción"
        ordering = ["orden", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_accion__gte=0),
                name="chk_accion_valor_gte_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo_accion="PORCENTAJE", valor_accion__lte=100)
                    | ~models.Q(tipo_accion="PORCENTAJE")
                ),
                name="chk_accion_porcentaje_max_100",
            ),
            models.CheckConstraint(
                condition=models.Q(tope_maximo_descuento__isnull=True)
                | models.Q(tope_maximo_descuento__gt=0),
                name="chk_accion_tope_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_regalo__gt=0),
                name="chk_accion_cantidad_regalo_gt_0",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.tipo_accion == AccionPromocion.TipoAccion.PORCENTAJE:
            if self.valor_accion < 0 or self.valor_accion > 100:
                raise ValidationError({"valor_accion": "El porcentaje debe estar entre 0 y 100."})
        elif self.tipo_accion == AccionPromocion.TipoAccion.MONTO_FIJO:
            if self.valor_accion <= 0:
                raise ValidationError({"valor_accion": "El monto fijo debe ser superior a cero."})
        elif self.tipo_accion == AccionPromocion.TipoAccion.ITEM_REGALO:
            if not self.producto_regalo:
                raise ValidationError(
                    {"producto_regalo": "Debe especificar el producto que se entrega de regalo."}
                )
            if self.cantidad_regalo <= 0:
                raise ValidationError(
                    {"cantidad_regalo": "La cantidad de regalo debe ser al menos 1."}
                )

        if self.alcance_accion == AccionPromocion.AlcanceAccion.CATEGORIA:
            if not self.categoria_objetivo:
                raise ValidationError(
                    {"categoria_objetivo": "Debe seleccionar una categoría objetivo."}
                )
        elif self.alcance_accion == AccionPromocion.AlcanceAccion.PRODUCTO:
            if not self.producto_objetivo:
                raise ValidationError(
                    {"producto_objetivo": "Debe seleccionar un producto objetivo."}
                )

        if self.tope_maximo_descuento is not None and self.tope_maximo_descuento <= 0:
            raise ValidationError(
                {"tope_maximo_descuento": "El tope máximo de descuento debe ser mayor a cero."}
            )

    def save(self, *args, skip_clean: bool = False, **kwargs) -> None:
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Acción #{self.orden} ({self.tipo_accion}) para {self.regla_promocion.nombre}"


class PromocionAplicada(models.Model):
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="promociones_aplicadas",
    )
    regla_promocion = models.ForeignKey(
        ReglaPromocion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aplicaciones",
    )
    nombre_regla_snapshot = models.CharField(max_length=150)
    codigo_cupon_snapshot = models.CharField(max_length=50, blank=True, null=True)
    monto_descontado_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    desglose_por_item = models.JSONField(default=list, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Promoción Aplicada"
        verbose_name_plural = "Promociones Aplicadas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto_descontado_total__gte=0),
                name="chk_prom_ap_monto_gte_0",
            ),
            models.CheckConstraint(
                condition=~models.Q(nombre_regla_snapshot=""),
                name="chk_prom_ap_nombre_no_vacio",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.nombre_regla_snapshot:
            self.nombre_regla_snapshot = self.nombre_regla_snapshot.strip()
        if not self.nombre_regla_snapshot:
            raise ValidationError(
                {"nombre_regla_snapshot": "El snapshot del nombre no puede estar vacío."}
            )
        if self.monto_descontado_total is not None and self.monto_descontado_total < 0:
            raise ValidationError(
                {"monto_descontado_total": "El monto descontado no puede ser negativo."}
            )

    def save(self, *args, skip_clean: bool = False, **kwargs) -> None:
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        fac = f"Fac #{self.factura_id}"
        return f"{self.nombre_regla_snapshot} (${self.monto_descontado_total}) - {fac}"

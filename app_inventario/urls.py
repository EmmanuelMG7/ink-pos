from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.gestion_productos, name="gestion"),
    path("catalogo/", views.catalogo, name="catalogo"),
    path("editar/<int:pk>/", views.editar_producto, name="editar_producto"),
    path("obtener/<int:pk>/", views.obtener_producto, name="obtener_producto"),
    path("eliminar/<int:pk>/", views.eliminar_producto, name="eliminar_producto"),
    path("carrito/agregar/", views.agregar_al_carrito_api, name="api_agregar_carrito"),
    path("carrito/", views.ver_carrito, name="ver_carrito"),
    path(
        "carrito/eliminar/<int:item_id>/",
        views.eliminar_del_carrito_api,
        name="api_eliminar_carrito",
    ),
    path(
        "carrito/modificar/<int:item_id>/",
        views.modificar_cantidad_api,
        name="api_modificar_carrito",
    ),
    path("checkout/", views.preparar_checkout, name="checkout"),
    path("checkout/confirmar/", views.confirmar_pedido_api, name="api_confirmar_pedido"),
    path(
        "checkout/comprobante/<int:pedido_id>/", views.comprobante_pedido, name="comprobante_pedido"
    ),
]

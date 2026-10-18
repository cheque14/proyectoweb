from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
    path("base/", views.base, name="base"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="home/login.html"),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page="home:login"), name="logout"),
    path("sign-up/", views.sign_up, name="sign_up"),
    path("perfil/", views.perfil, name="perfil"),
    path("noticia/", views.noticia, name="noticia"),
    path("noticia/<int:pk>/", views.noticia, name="noticia_detalle"),
    path("categoria/", views.categoria, name="categoria"),
    path("categoria/<int:pk>/", views.categoria, name="categoria_detalle"),
    path("contactanos/", views.contactanos, name="contactanos"),
    path(
        "crear-publicacion/",
        views.crear_publicacion,
        name="crear_publicacion",
    ),
    path("crear-usuario/", views.crear_usuario, name="crear_usuario"),
    path(
        "crud/cambiar-contrasena/",
        views.crud_cambiar_contraseña,
        name="crud_cambiar_contrasena",
    ),
    path("crud/categorias/", views.crud_categorias, name="crud_categorias"),
    path(
        "crud/categorias/<int:pk>/editar/",
        views.editar_categoria,
        name="editar_categoria",
    ),
    path(
        "crud/categorias/<int:pk>/eliminar/",
        views.eliminar_categoria,
        name="eliminar_categoria",
    ),
    path("crud/comentarios/", views.crud_comentarios, name="crud_comentarios"),
    path(
        "crud/comentarios/<int:pk>/aprobar/",
        views.aprobar_comentario,
        name="aprobar_comentario",
    ),
    path(
        "crud/comentarios/<int:pk>/bloquear/",
        views.bloquear_comentario,
        name="bloquear_comentario",
    ),
    path(
        "crud/comentarios/<int:pk>/eliminar/",
        views.eliminar_comentario,
        name="eliminar_comentario",
    ),
    path("crud/noticias/", views.crud_noticias, name="crud_noticias"),
    path(
        "crud/noticias/<int:pk>/editar/",
        views.editar_publicacion,
        name="editar_publicacion",
    ),
    path(
        "crud/noticias/<int:pk>/publicar/",
        views.publicar_publicacion,
        name="publicar_publicacion",
    ),
    path(
        "crud/noticias/<int:pk>/eliminar/",
        views.eliminar_publicacion,
        name="eliminar_publicacion",
    ),
    path("crud/perfil/", views.crud_perfil, name="crud_perfil"),
    path("crud/usuarios/", views.crud_usuarios, name="crud_usuarios"),
    path(
        "crud/usuarios/<int:user_id>/editar/",
        views.editar_usuario,
        name="editar_usuario",
    ),
    path(
        "crud/usuarios/<int:user_id>/estado/",
        views.bloquear_usuario,
        name="bloquear_usuario",
    ),
    path(
        "crud/usuarios/<int:user_id>/eliminar/",
        views.eliminar_usuario,
        name="eliminar_usuario",
    ),
]

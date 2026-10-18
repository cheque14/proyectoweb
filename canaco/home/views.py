from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Archivo,
    Categoria,
    Comentario,
    GaleriaPublicacion,
    Perfil,
    Publicacion,
)

User = get_user_model()


def es_operador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def operador_required(view_func):
    @login_required(login_url="home:login")
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not es_operador(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view


def index(request):
    publicaciones = list(Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).select_related(
        'categoria', 'autor', 'imagen_portada'
    ).order_by('-createdat')[:6])
    return render(
        request,
        'home/index.html',
        {
            'slider': publicaciones[:3],
            'publicaciones': publicaciones,
        },
    )

def base(request):
    return render(request, 'home/base.html')


def sign_up(request):
    if request.method != 'POST':
        return render(request, 'home/sign_up.html')

    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    apellido_paterno = request.POST.get('apellido_paterno', '').strip()
    apellido_materno = request.POST.get('apellido_materno', '').strip()
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    errors = []

    if not username:
        errors.append('El nombre de usuario es obligatorio.')
    elif User.objects.filter(username=username).exists():
        errors.append('El nombre de usuario ya está en uso.')

    if not email:
        errors.append('El correo electrónico es obligatorio.')
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors.append('Ingresa un correo electrónico válido.')
        if User.objects.filter(email=email).exists():
            errors.append('El correo electrónico ya está registrado.')

    if password1 != password2:
        errors.append('Las contraseñas no coinciden.')
    elif password1:
        user_for_validation = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=' '.join(filter(None, [apellido_paterno, apellido_materno])),
        )
        try:
            validate_password(password1, user=user_for_validation)
        except ValidationError as error:
            errors.extend(error.messages)
    else:
        errors.append('La contraseña es obligatoria.')

    if errors:
        for error in errors:
            messages.error(request, error)
        return render(request, 'home/sign_up.html')

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=' '.join(filter(None, [apellido_paterno, apellido_materno])),
        )
        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()

    messages.success(
        request,
        'Tu cuenta ha sido creada con éxito. Ahora puedes iniciar sesión.',
    )
    return redirect('home:login')


@login_required(login_url="home:login")
def perfil(request):
    return render(request, 'home/perfil.html')


@login_required(login_url="home:login")
def crud_perfil(request):
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        foto = request.FILES.get('foto')

        if not username:
            messages.error(request, 'El usuario es obligatorio.')
            return redirect('home:crud_perfil')

        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
            return redirect('home:crud_perfil')

        if email:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, 'Ingresa un correo electrónico válido.')
                return redirect('home:crud_perfil')
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, 'Ese correo electrónico ya está en uso.')
                return redirect('home:crud_perfil')

        with transaction.atomic():
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = ' '.join(
                filter(None, [apellido_paterno, apellido_materno])
            )
            user.save()

            perfil.apellido_paterno = apellido_paterno
            perfil.apellido_materno = apellido_materno

            if foto:
                archivo = Archivo.objects.create(
                    nombre=foto.name,
                    nombre_temporal=foto.name,
                    ruta=foto,
                    tipo=getattr(foto, 'content_type', '') or '',
                    tamano=foto.size,
                    fk_user=user,
                )
                perfil.foto_perfil = archivo

            perfil.save()

        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('home:perfil')

    return render(request, 'home/crud_perfil.html', {'perfil_usuario': perfil})


@login_required(login_url="home:login")
def crud_cambiar_contraseña(request):
    if request.method == 'POST':
        actual = request.POST.get('actual', '')
        nueva = request.POST.get('nueva', '')
        confirmar = request.POST.get('confirmar', '')
        user = request.user

        if not user.check_password(actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
        elif nueva != confirmar:
            messages.error(request, 'Las nuevas contraseñas no coinciden.')
        else:
            try:
                validate_password(nueva, user=user)
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)
            else:
                user.set_password(nueva)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada correctamente.')

        return redirect('home:crud_cambiar_contrasena')

    return render(request, 'home/crud_cambiar_contraseña.html')


@operador_required
def crud_usuarios(request):
    usuarios = User.objects.select_related('perfil').order_by('date_joined')
    return render(request, 'home/crud_usuarios.html', {'usuarios': usuarios})


@operador_required
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        rol = request.POST.get('rol', 'colaborador')
        errors = []

        if not username:
            errors.append('El nombre de usuario es obligatorio.')
        elif User.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya está en uso.')

        if not email:
            errors.append('El correo electrónico es obligatorio.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append('Ingresa un correo electrónico válido.')
            if User.objects.filter(email=email).exists():
                errors.append('El correo electrónico ya está registrado.')

        if password1 != password2:
            errors.append('Las contraseñas no coinciden.')
        elif password1:
            try:
                validate_password(password1)
            except ValidationError as error:
                errors.extend(error.messages)
        else:
            errors.append('La contraseña es obligatoria.')

        if rol not in {'colaborador', 'editor', 'administrador'}:
            errors.append('Selecciona un rol válido.')
        elif rol == 'administrador' and not request.user.is_superuser:
            errors.append('Solo un administrador puede asignar ese rol.')
        elif rol == 'editor' and not request.user.is_staff:
            errors.append('Solo un editor o administrador puede asignar ese rol.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'home/crear_usuario.html')

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=' '.join(
                    filter(None, [apellido_paterno, apellido_materno])
                ),
                is_staff=rol in {'editor', 'administrador'},
                is_superuser=rol == 'administrador',
            )
            Perfil.objects.update_or_create(
                user=user,
                defaults={
                    'apellido_paterno': apellido_paterno,
                    'apellido_materno': apellido_materno,
                },
            )
        messages.success(request, 'El usuario se creó correctamente.')
        return redirect('home:crud_usuarios')

    return render(request, 'home/crear_usuario.html')


@operador_required
def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    if usuario.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    perfil, _ = Perfil.objects.get_or_create(user=usuario)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        rol = request.POST.get('rol', 'colaborador')
        errors = []

        if not username:
            errors.append('El nombre de usuario es obligatorio.')
        elif User.objects.filter(username=username).exclude(pk=usuario.pk).exists():
            errors.append('El nombre de usuario ya está en uso.')

        if not email:
            errors.append('El correo electrónico es obligatorio.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append('Ingresa un correo electrónico válido.')
            if User.objects.filter(email=email).exclude(pk=usuario.pk).exists():
                errors.append('El correo electrónico ya está registrado.')

        if password1 or password2:
            if password1 != password2:
                errors.append('Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(password1, user=usuario)
                except ValidationError as error:
                    errors.extend(error.messages)

        if rol not in {'colaborador', 'editor', 'administrador'}:
            errors.append('Selecciona un rol válido.')
        elif rol == 'administrador' and not request.user.is_superuser:
            errors.append('Solo un administrador puede asignar ese rol.')
        elif rol == 'editor' and not request.user.is_staff:
            errors.append('Solo un editor o administrador puede asignar ese rol.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                'home/crear_usuario.html',
                {'usuario_editado': usuario, 'perfil_editado': perfil},
            )

        usuario.username = username
        usuario.email = email
        usuario.first_name = first_name
        usuario.last_name = ' '.join(
            filter(None, [apellido_paterno, apellido_materno])
        )
        usuario.is_staff = rol in {'editor', 'administrador'}
        usuario.is_superuser = rol == 'administrador'
        if password1:
            usuario.set_password(password1)
        usuario.save()

        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()

        messages.success(request, 'El usuario se actualizó correctamente.')
        return redirect('home:crud_usuarios')

    return render(
        request,
        'home/crear_usuario.html',
        {'usuario_editado': usuario, 'perfil_editado': perfil},
    )


@operador_required
@require_POST
def bloquear_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes bloquear tu propia cuenta.')
    elif usuario.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    else:
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        estado = 'desbloqueó' if usuario.is_active else 'bloqueó'
        messages.success(request, f'Se {estado} la cuenta de {usuario.username}.')
    return redirect('home:crud_usuarios')


@operador_required
@require_POST
def eliminar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
    elif usuario.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    else:
        username = usuario.username
        usuario.delete()
        messages.success(request, f'Se eliminó la cuenta de {username}.')
    return redirect('home:crud_usuarios')


@operador_required
def crud_categorias(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre de la categoría es obligatorio.')
        else:
            Categoria.objects.create(nombre=nombre, fk_user=request.user)
            messages.success(request, 'Categoría agregada correctamente.')
            return redirect('home:crud_categorias')

    categorias = Categoria.objects.order_by('-createdat')
    return render(request, 'home/crud_categorias.html', {'categorias': categorias})


@operador_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre de la categoría es obligatorio.')
        else:
            categoria.nombre = nombre
            categoria.save()
            messages.success(request, 'Categoría actualizada correctamente.')
            return redirect('home:crud_categorias')

    return render(request, 'home/editar_categoria.html', {'categoria': categoria})


@operador_required
@require_POST
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.delete()
    messages.success(request, 'Categoría eliminada correctamente.')
    return redirect('home:crud_categorias')


@operador_required
def crud_noticias(request):
    publicaciones = Publicacion.objects.select_related(
        'categoria', 'autor'
    ).order_by('-createdat')
    return render(
        request,
        'home/crud_noticias.html',
        {'publicaciones': publicaciones},
    )


def guardar_archivo(upload, user):
    return Archivo.objects.create(
        nombre=upload.name,
        nombre_temporal=upload.name,
        ruta=upload,
        tipo=getattr(upload, 'content_type', '') or '',
        tamano=upload.size,
        fk_user=user,
    )


def datos_publicacion_validos(request):
    titulo = request.POST.get('titulo', '').strip()
    resumen = request.POST.get('resumen', '').strip()
    contenido = request.POST.get('contenido', '').strip()
    estado = request.POST.get('estado') or Publicacion.ESTADO_BORRADOR
    categoria_id = request.POST.get('categoria') or None

    if not titulo or not resumen or not contenido:
        messages.error(request, 'Completa el título, resumen y contenido.')
        return None
    if estado not in dict(Publicacion.ESTADOS):
        messages.error(request, 'Selecciona un estado válido.')
        return None
    categoria = None
    if categoria_id:
        categoria = Categoria.objects.filter(pk=categoria_id).first()
        if categoria is None:
            messages.error(request, 'La categoría seleccionada no existe.')
            return None

    return {
        'titulo': titulo,
        'resumen': resumen,
        'contenido': contenido,
        'estado': estado,
        'categoria': categoria,
    }


def guardar_imagenes_publicacion(request, publicacion):
    portada = request.FILES.get('imagen_portada')
    if portada:
        publicacion.imagen_portada = guardar_archivo(portada, request.user)
        publicacion.save(update_fields=['imagen_portada', 'updatedat'])

    for imagen in request.FILES.getlist('galeria'):
        archivo = guardar_archivo(imagen, request.user)
        GaleriaPublicacion.objects.create(
            publicacion=publicacion,
            archivo=archivo,
        )


@operador_required
def crear_publicacion(request):
    categorias = Categoria.objects.order_by('nombre')
    if request.method == 'POST':
        datos = datos_publicacion_validos(request)
        if datos:
            with transaction.atomic():
                publicacion = Publicacion.objects.create(
                    **datos,
                    autor=request.user,
                )
                guardar_imagenes_publicacion(request, publicacion)
            messages.success(request, 'Publicación creada correctamente.')
            return redirect('home:crud_noticias')

    return render(
        request,
        'home/crear_publicacion.html',
        {'categorias': categorias},
    )


@operador_required
def editar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    categorias = Categoria.objects.order_by('nombre')
    if request.method == 'POST':
        datos = datos_publicacion_validos(request)
        if datos:
            with transaction.atomic():
                for field, value in datos.items():
                    setattr(publicacion, field, value)
                publicacion.save()
                guardar_imagenes_publicacion(request, publicacion)
            messages.success(request, 'Publicación actualizada correctamente.')
            return redirect('home:crud_noticias')

    return render(
        request,
        'home/crear_publicacion.html',
        {'categorias': categorias, 'publicacion': publicacion},
    )


@operador_required
@require_POST
def publicar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    if publicacion.estado == Publicacion.ESTADO_PUBLICADO:
        publicacion.estado = Publicacion.ESTADO_BORRADOR
        mensaje = 'La publicación se guardó como borrador.'
    else:
        publicacion.estado = Publicacion.ESTADO_PUBLICADO
        mensaje = 'La publicación se publicó correctamente.'
    publicacion.save(update_fields=['estado', 'updatedat'])
    messages.success(request, mensaje)
    return redirect('home:crud_noticias')


@operador_required
@require_POST
def eliminar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    publicacion.delete()
    messages.success(request, 'Publicación eliminada correctamente.')
    return redirect('home:crud_noticias')


def noticia(request, pk=None):
    publicaciones = Publicacion.objects.select_related(
        'categoria', 'autor', 'imagen_portada'
    )
    if pk:
        if es_operador(request.user):
            publicacion = get_object_or_404(publicaciones, pk=pk)
        else:
            publicacion = get_object_or_404(
                publicaciones.filter(estado=Publicacion.ESTADO_PUBLICADO),
                pk=pk,
            )
    else:
        publicacion = publicaciones.filter(
            estado=Publicacion.ESTADO_PUBLICADO
        ).order_by('-createdat').first()
        if publicacion is None:
            messages.info(request, 'Todavía no hay noticias publicadas.')
            return redirect('home:index')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('home:login')
        contenido = request.POST.get('contenido', '').strip()
        if contenido:
            Comentario.objects.create(
                publicacion=publicacion,
                user=request.user,
                contenido=contenido,
            )
            messages.success(
                request,
                'Comentario enviado. Será visible cuando lo apruebe un administrador.',
            )
        else:
            messages.error(request, 'El comentario no puede estar vacío.')
        return redirect('home:noticia_detalle', pk=publicacion.pk)

    Publicacion.objects.filter(pk=publicacion.pk).update(visitas=F('visitas') + 1)
    publicacion.refresh_from_db()
    recientes = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).exclude(pk=publicacion.pk).order_by('-createdat')[:4]
    comentarios = publicacion.comentarios.filter(
        estado=Comentario.ESTADO_APROBADO,
    ).select_related('user').order_by('-createdat')
    categorias = Categoria.objects.order_by('nombre')
    return render(
        request,
        'home/noticia.html',
        {
            'publicacion': publicacion,
            'recientes': recientes,
            'comentarios': comentarios,
            'categorias': categorias,
        },
    )


def categoria(request, pk=None):
    categorias = Categoria.objects.all().order_by('nombre')
    categoria_seleccionada = None
    categoria_id = pk or request.GET.get('categoria')
    publicaciones = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO
    )

    if categoria_id:
        categoria_seleccionada = get_object_or_404(Categoria, pk=categoria_id)
        publicaciones = publicaciones.filter(categoria=categoria_seleccionada)

    return render(
        request,
        'home/categoria.html',
        {
            'categorias': categorias,
            'categoria_seleccionada': categoria_seleccionada,
            'publicaciones': publicaciones.select_related(
                'categoria', 'imagen_portada'
            ).order_by('-createdat'),
        },
    )


@operador_required
def crud_comentarios(request):
    comentarios = Comentario.objects.select_related(
        'publicacion', 'user'
    ).order_by('-createdat')
    return render(
        request,
        'home/crud_comentarios.html',
        {'comentarios': comentarios},
    )


@operador_required
@require_POST
def aprobar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    comentario.estado = Comentario.ESTADO_APROBADO
    comentario.save(update_fields=['estado', 'updatedat'])
    messages.success(request, 'Comentario aprobado.')
    return redirect('home:crud_comentarios')


@operador_required
@require_POST
def bloquear_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    comentario.estado = Comentario.ESTADO_BLOQUEADO
    comentario.save(update_fields=['estado', 'updatedat'])
    messages.success(request, 'Comentario bloqueado.')
    return redirect('home:crud_comentarios')


@operador_required
@require_POST
def eliminar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    comentario.delete()
    messages.success(request, 'Comentario eliminado.')
    return redirect('home:crud_comentarios')


@login_required(login_url="home:login")
def contactanos(request):
    return render(request, 'home/contactanos.html')

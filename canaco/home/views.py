from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import Archivo, Perfil

User = get_user_model()


def index(request):
    return render(request, 'home/index.html')


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


@login_required(login_url="home:login")
def crud_usuarios(request):
    usuarios = User.objects.select_related('perfil').order_by('date_joined')
    return render(request, 'home/crud_usuarios.html', {'usuarios': usuarios})


@login_required(login_url="home:login")
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


@login_required(login_url="home:login")
def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
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


@login_required(login_url="home:login")
def bloquear_usuario(request, user_id):
    if request.method != 'POST':
        return redirect('home:crud_usuarios')

    usuario = get_object_or_404(User, pk=user_id)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes bloquear tu propia cuenta.')
    else:
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        estado = 'desbloqueó' if usuario.is_active else 'bloqueó'
        messages.success(request, f'Se {estado} la cuenta de {usuario.username}.')
    return redirect('home:crud_usuarios')


@login_required(login_url="home:login")
def eliminar_usuario(request, user_id):
    if request.method != 'POST':
        return redirect('home:crud_usuarios')

    usuario = get_object_or_404(User, pk=user_id)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
    else:
        username = usuario.username
        usuario.delete()
        messages.success(request, f'Se eliminó la cuenta de {username}.')
    return redirect('home:crud_usuarios')


@login_required(login_url="home:login")
def crud_categorias(request):
    return render(request, 'home/crud_categorias.html')


@login_required(login_url="home:login")
def editar_categoria(request):
    return render(request, 'home/editar_categoria.html')


@login_required(login_url="home:login")
def crud_noticias(request):
    return render(request, 'home/crud_noticias.html')


@login_required(login_url="home:login")
def crear_publicacion(request):
    return render(request, 'home/crear_publicacion.html')


@login_required(login_url="home:login")
def noticia(request):
    return render(request, 'home/noticia.html')


@login_required(login_url="home:login")
def categoria(request):
    return render(request, 'home/categoria.html')


@login_required(login_url="home:login")
def crud_comentarios(request):
    return render(request, 'home/crud_comentarios.html')


@login_required(login_url="home:login")
def contactanos(request):
    return render(request, 'home/contactanos.html')

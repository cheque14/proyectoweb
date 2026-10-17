from contextlib import nullcontext
from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

from . import views


class LoginRequiredViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_user_management_routes_exist(self):
        routes = {
            'home:crear_usuario': '/crear-usuario/',
            'home:editar_usuario': '/crud/usuarios/1/editar/',
            'home:bloquear_usuario': '/crud/usuarios/1/estado/',
            'home:eliminar_usuario': '/crud/usuarios/1/eliminar/',
        }

        for route_name, expected_path in routes.items():
            with self.subTest(route=route_name):
                args = (1,) if route_name != 'home:crear_usuario' else ()
                self.assertEqual(reverse(route_name, args=args), expected_path)

    def test_private_views_redirect_anonymous_users_to_login(self):
        protected_views = (
            ("/perfil/", "perfil"),
            ("/noticia/", "noticia"),
            ("/categoria/", "categoria"),
            ("/contactanos/", "contactanos"),
            ("/crear-publicacion/", "crear_publicacion"),
            ("/crear-usuario/", "crear_usuario"),
            ("/crud/cambiar-contrasena/", "crud_cambiar_contrasena"),
            ("/crud/categorias/", "crud_categorias"),
            ("/crud/comentarios/", "crud_comentarios"),
            ("/crud/noticias/", "crud_noticias"),
            ("/crud/perfil/", "crud_perfil"),
            ("/crud/usuarios/", "crud_usuarios"),
            ("/editar-categoria/", "editar_categoria"),
        )

        for path, view_name in protected_views:
            with self.subTest(view=view_name):
                request = self.factory.get(path)
                request.user = AnonymousUser()

                response = resolve(path).func(request)

                self.assertRedirects(
                    response,
                    f"{reverse('home:login')}?next={path}",
                    fetch_redirect_response=False,
                )


class SignupViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def make_post_request(self, password1, password2):
        request = self.factory.post(
            reverse('home:sign_up'),
            {
                'username': 'new-user',
                'email': 'new-user@example.com',
                'first_name': 'New',
                'apellido_paterno': 'User',
                'apellido_materno': '',
                'password1': password1,
                'password2': password2,
            },
        )
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    @patch('home.views.transaction.atomic', return_value=nullcontext())
    @patch('home.views.Perfil.objects.get_or_create')
    @patch('home.views.User.objects.create_user')
    @patch('home.views.User.objects.filter')
    def test_valid_signup_creates_account_and_profile(
        self, filter_users, create_user, get_or_create_profile, _atomic
    ):
        filter_users.return_value.exists.return_value = False
        user = Mock()
        profile = Mock()
        create_user.return_value = user
        get_or_create_profile.return_value = (profile, True)
        request = self.make_post_request(
            'L0ng!Passphrase_987', 'L0ng!Passphrase_987'
        )

        response = views.sign_up(request)

        self.assertRedirects(
            response,
            reverse('home:login'),
            fetch_redirect_response=False,
        )
        create_user.assert_called_once_with(
            username='new-user',
            email='new-user@example.com',
            password='L0ng!Passphrase_987',
            first_name='New',
            last_name='User',
        )
        get_or_create_profile.assert_called_once_with(user=user)
        self.assertEqual(profile.apellido_paterno, 'User')
        profile.save.assert_called_once_with()

    @patch('home.views.User.objects.filter')
    @patch('home.views.User.objects.create_user')
    def test_signup_rejects_mismatched_passwords(self, create_user, filter_users):
        filter_users.return_value.exists.return_value = False
        request = self.make_post_request('FirstPassword_987!', 'OtherPassword_987!')

        response = views.sign_up(request)

        self.assertEqual(response.status_code, 200)
        create_user.assert_not_called()
        self.assertIn(
            'Las contraseñas no coinciden.',
            [str(message) for message in request._messages],
        )

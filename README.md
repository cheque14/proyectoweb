# Canaco

Aplicación web Django para administrar categorías, publicaciones, usuarios y comentarios.

## Despliegue en una VM Linux con Docker Compose

El despliegue usa Gunicorn para ejecutar Django y Nginx como proxy HTTPS. MySQL solo está disponible dentro de la red privada de Compose.

### Preparación inicial de la VM

1. Instala Docker Engine y el plugin Docker Compose.
2. Clona el proyecto en la VM y entra a la carpeta que contiene `docker-compose.yml`.
3. Copia `.env.example` como `.env` y establece una `SECRET_KEY` de Django y contraseñas largas y únicas para MySQL. No subas `.env` al repositorio.
4. En el firewall de Azure y el de Linux, permite TCP `80` y `443`. No abras `3306` ni `8000` a Internet.
5. En Namecheap, configura los registros A de `@` y `www` con la IP pública estática de la VM y espera a que se propaguen.

### Certificado y primer arranque

Con el DNS apuntando a la VM y el puerto 80 accesible, solicita el certificado antes de iniciar Nginx:

```bash
docker compose run --rm --service-ports certbot certonly --standalone \
  --preferred-challenges http -d canacoweb.me -d www.canacoweb.me \
  --email TU_CORREO --agree-tos --no-eff-email
```

Reemplaza `TU_CORREO` por tu correo electrónico. Después inicia la aplicación:

```bash
docker compose up -d --build
docker compose logs -f web nginx
```

Compose aplica las migraciones, recopila los archivos estáticos y arranca Gunicorn. Nginx sirve estáticos y multimedia y reenvía las demás peticiones a Django. Los datos de MySQL, los archivos multimedia y los estáticos viven en volúmenes de Docker.

Para crear la cuenta administradora:

```bash
docker compose exec web python manage.py createsuperuser
```

### Renovación del certificado

Let's Encrypt emite certificados de corta duración. Antes de que caduque, detén Nginx, renueva con el modo standalone y vuelve a iniciarlo:

```bash
docker compose stop nginx
docker compose run --rm --service-ports certbot renew
docker compose start nginx
```

Configura estos comandos en una tarea programada de la VM y respalda los volúmenes de datos.

### Desarrollo local en Windows

El modo directo requiere MySQL en `localhost:3306` y las dependencias de `requirements.txt` instaladas en el entorno virtual:

```powershell
.\canaco_env\Scripts\Activate.ps1
$env:SECRET_KEY = "clave-local-temporal"
$env:DEBUG = "True"
$env:SECURE_SSL_REDIRECT = "False"
python .\canaco\manage.py migrate
python .\canaco\manage.py runserver
```

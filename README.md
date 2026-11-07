# Canaco

Aplicación web Django para administrar categorías, publicaciones, usuarios y comentarios.

## Ejecutar con Docker

1. Inicia Docker Desktop.
2. Desde la carpeta del proyecto, ejecuta:

   ```powershell
   docker compose up --build
   ```

   Compose inicia MySQL, espera a que acepte conexiones, aplica las migraciones y
   arranca Django.
3. Abre <http://localhost:8000/>.

Para crear la cuenta inicial con permisos de administración, abre otra terminal
en la carpeta del proyecto y ejecuta:

```powershell
docker compose exec web python canaco/manage.py createsuperuser
```

La configuración local usa `canaco` como base y usuario MySQL. Puedes cambiar
`MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` y `MYSQL_ROOT_PASSWORD` en un
archivo `.env`; Compose pasa los mismos valores a MySQL y Django. El servicio web
se conecta al servicio de base de datos usando `MYSQL_HOST=db`.

Para detener los contenedores, pulsa `Ctrl+C`. Para iniciarlos otra vez en segundo
plano, usa `docker compose up -d`. Los datos de MySQL se conservan en el volumen
`mysql_data`; no uses `docker compose down -v` si quieres conservarlos.

## Ejecutar Django directamente en Windows

Este modo requiere MySQL activo en `localhost:3306` y las dependencias de
`requirements.txt` instaladas en el entorno virtual:

```powershell
.\canaco_env\Scripts\Activate.ps1
python .\canaco\manage.py migrate
python .\canaco\manage.py runserver
```

La aplicación sirve archivos multimedia directamente durante el modo de
desarrollo (`DEBUG=True`).
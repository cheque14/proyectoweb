from .models import Categoria, Publicacion


def categorias_menu(request):
    categorias = Categoria.objects.order_by('nombre')
    noticias_recientes = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).select_related('imagen_portada').order_by('-createdat')[:3]

    return {
        'categorias_menu': categorias,
        'global_categorias': categorias,
        'global_recientes': noticias_recientes,
    }

from django.urls import path

from .views import (
    atendimento_export,
    atendimento_index,
    atendimento_list,
    atendimento_new,
    atendimento_view,
    flora_export,
    flora_index,
    flora_list,
    flora_new,
    flora_view,
    home,
    manejo_export,
    manejo_index,
    manejo_list,
    manejo_new,
    notifications_list,
    manejo_view,
)

app_name = 'sesmt'

urlpatterns = [
    path('', home, name='home'),
    path('notificacoes/', notifications_list, name='notifications_list'),
    path('atendimento/', atendimento_index, name='atendimento_index'),
    path('atendimento/lista/', atendimento_list, name='atendimento_list'),
    path('atendimento/novo/', atendimento_new, name='atendimento_new'),
    path('atendimento/exportar/', atendimento_export, name='atendimento_export'),
    path('atendimento/<int:pk>/', atendimento_view, name='atendimento_view'),
    path('manejo/', manejo_index, name='manejo_index'),
    path('manejo/lista/', manejo_list, name='manejo_list'),
    path('manejo/novo/', manejo_new, name='manejo_new'),
    path('manejo/exportar/', manejo_export, name='manejo_export'),
    path('manejo/<int:pk>/', manejo_view, name='manejo_view'),
    path('flora/', flora_index, name='flora_index'),
    path('flora/lista/', flora_list, name='flora_list'),
    path('flora/novo/', flora_new, name='flora_new'),
    path('flora/exportar/', flora_export, name='flora_export'),
    path('flora/<int:pk>/', flora_view, name='flora_view'),
]

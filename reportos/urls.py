from django.urls import path

from .views import atendimento_home, flora_home, home, manejo_home

app_name = "reportos"

urlpatterns = [
    path("", home, name="home"),
    path("atendimento/", atendimento_home, name="atendimento_home"),
    path("manejo/", manejo_home, name="manejo_home"),
    path("flora/", flora_home, name="flora_home"),
]

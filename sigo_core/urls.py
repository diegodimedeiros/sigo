from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('siop/', include('siop.urls')),
    path('sesmt/', include('sesmt.urls')),
    path('reportos/', include('reportos.urls')),
    path('', include('sigo.urls')),
]

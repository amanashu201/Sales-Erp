from django.contrib import admin
from django.urls import path
from core.views import user_login

urlpatterns = [
    path('', user_login, name='login'),  # Show login page at root
    path('admin/', admin.site.urls),
]

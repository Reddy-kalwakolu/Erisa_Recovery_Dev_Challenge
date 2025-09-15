# erisa_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Point the root URL to the claims app's urls.py file
    path('', include('claims.urls')),
]
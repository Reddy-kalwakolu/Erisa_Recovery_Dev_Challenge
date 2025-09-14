# erisa_project/urls.py
from django.contrib import admin
from django.urls import path, include
# No longer need RedirectView for the root path

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Point the root URL to the claims app's urls.py file
    path('', include('claims.urls')),
]
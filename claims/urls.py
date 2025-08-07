# claims/urls.py

from django.urls import path
from . import views # We will create views later
from django.contrib.auth import views as auth_views # Import Django's auth views

app_name = 'claims'

urlpatterns = [

    # App URLs
    path('', views.claim_list_view, name='claim-list'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Auth URLs
    path('login/', auth_views.LoginView.as_view(template_name='claims/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # HTMX Action URLs
    path('<int:pk>/details/', views.claim_detail_view, name='claim-detail'),
    path('<int:pk>/flag/', views.flag_claim_view, name='flag-claim'),
    path('<int:pk>/add_note/', views.add_note_view, name='add-note'),
    path('upload/', views.upload_claims_view, name='upload-claims'), # Add this line
]

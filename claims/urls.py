# path: claims/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'claims'

urlpatterns = [
    # Home Page URL
    path('', views.home_view, name='home'),

    path('claims/', views.claim_list_view, name='claim-list'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_claims_view, name='upload-claims'),
    
    # URL for downloading template files
    path('download_template/<str:file_type>/', views.download_template_view, name='download-template'),

    # Auth URLs
    path('login/', auth_views.LoginView.as_view(template_name='claims/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='claims:login'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),

    # HTMX & Action URLs
    path('claim/<int:pk>/details/', views.claim_detail_view, name='claim-detail'),
    path('claim/<int:pk>/flag/', views.flag_claim_view, name='flag-claim'),
    path('claim/<int:pk>/add_note/', views.add_note_view, name='add-note'),
    path('claim/<int:pk>/change_status/', views.change_claim_status_view, name='change-claim-status'),
    path('claim/<int:pk>/report/', views.generate_report_view, name='generate-report'),
    path('note/<int:pk>/delete/', views.delete_note_view, name='delete-note'),
    path('note/<int:pk>/edit/', views.edit_note_view, name='edit-note'),
]
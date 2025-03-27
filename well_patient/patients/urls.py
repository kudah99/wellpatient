from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('patients/', views.PatientListView.as_view(), name='patient_list'),
    path('patients/<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('broadcasts/', views.broadcast_list_view, name='broadcast_list'),
    path('broadcasts/create/', views.broadcast_message_view, name='create_broadcast'),
    path('broadcasts/<int:pk>/cancel/', views.cancel_broadcast, name='cancel_broadcast'),
    path('import-patients/', views.import_patients_view, name='import_patients'),
]

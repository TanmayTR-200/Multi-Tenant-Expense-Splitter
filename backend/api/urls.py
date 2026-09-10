from django.urls import path

from . import views

urlpatterns = [
    path('auth/register/', views.register),
    path('auth/login/', views.LoginView.as_view()),
    path('groups/', views.groups),
    path('groups/<int:group_id>/', views.group_detail),
    path('groups/<int:group_id>/members/', views.add_member),
    path('groups/<int:group_id>/settlement-data/', views.internal_group_data),
    path('internal/groups/<int:group_id>/', views.internal_group_data),
]

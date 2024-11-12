from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('', views.home, name='home'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home/', views.home, name='home'),  # Homepage
    path('profile/', views.profile, name='profile'),
]

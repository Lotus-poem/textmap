"""
URL configuration for myapp2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from textsmap.views import TextProcessView, CategoryAdjustView, ResultView

urlpatterns = [
    path('', TextProcessView.as_view(), name='text-process'),
    path('adjust-categories/', CategoryAdjustView.as_view(), name='adjust-categories'),
    path('result/', ResultView.as_view(), name='result'),
]

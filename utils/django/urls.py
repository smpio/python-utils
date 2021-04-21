from django.urls import path

from . import views


urlpatterns = [
    path('healthz', views.HealthzView.as_view()),
    path('metricz', views.MetriczView.as_view()),
    path('swagger.json', views.get_open_api_view()),
]

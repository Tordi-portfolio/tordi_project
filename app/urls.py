from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    path('', views.tordi, name='tordi'),
    path('index', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('parameter/', views.parameter, name='parameter'),
    path('view/<int:pk>/', views.view_las, name='view_las'),
    path('api/curve/<int:pk>/<str:curve_mnemonic>/', views.curve_api, name='curve_api'),

    path("analysis/", views.analysis_home, name="analysis_home"),

    path("permeability/", views.perm_view, name="perm"),
    path('perm_details', views.perm_details, name='perm_details'),
    path("permeability/clear/", views.clear_perm_history, name="perm_clear_history"),

    path('porosity/', views.porosity_view, name='porosity'),
    path('porosity/clear/', views.clear_porosity_history, name='porosity_clear_history'),
    path('porosity_details', views.porosity_details, name='porosity_details'),

    path("sw/", views.sw_view, name="sw"),
    path('sw_details', views.sw_details, name='sw_details'),
    path("sw/clear/", views.clear_sw_history, name="sw_clear_history"),
]


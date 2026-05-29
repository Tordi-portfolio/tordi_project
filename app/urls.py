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
    path("porosity/", views.porosity_view, name="porosity"),
    path("sw/", views.sw_view, name="sw"),
    path("permeability/", views.perm_view, name="perm"),

    path('porosity_details', views.porosity_details, name='porosity_details'),
    path('perm_details', views.perm_details, name='perm_details'),
    path('sw_details', views.sw_details, name='sw_details'),
]


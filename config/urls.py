"""
URL configuration for PharmaGest project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        '',
        RedirectView.as_view(pattern_name='rapports:tableau_de_bord', permanent=False),
        name='home',
    ),
    path(
        'connexion/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login',
    ),
    path(
        'deconnexion/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path(
        'mot-de-passe/modifier/',
        auth_views.PasswordChangeView.as_view(
            template_name='registration/password_form.html',
            success_url='/mot-de-passe/modifier/termine/',
        ),
        name='password_change',
    ),
    path(
        'mot-de-passe/modifier/termine/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_done.html'
        ),
        name='password_change_done',
    ),
    path(
        'mot-de-passe/reinitialiser/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/mot-de-passe/reinitialiser/envoye/',
        ),
        name='password_reset',
    ),
    path(
        'mot-de-passe/reinitialiser/envoye/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'mot-de-passe/reinitialiser/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_form.html',
            success_url='/mot-de-passe/reinitialiser/termine/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'mot-de-passe/reinitialiser/termine/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_done.html'
        ),
        name='password_reset_complete',
    ),
    path('achats/', include("achats.urls")),
    path('categories/', include("categories.urls")),
    path('clients/', include("clients.urls")),
    path('fournisseurs/', include("fournisseurs.urls")),
    path('medicaments/', include("medicaments.urls")),
    path('rapports/', include("rapports.urls")),
    path('stock/', include("stock.urls")),
    path('utilisateurs/', include("utilisateurs.urls")),
    path('ventes/', include("ventes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
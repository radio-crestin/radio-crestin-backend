from django.urls import path, include


def extend_superapp_urlpatterns(main_urlpatterns):
    main_urlpatterns += [
        path('accounts/', include('allauth.urls')),
    ]


def extend_superapp_admin_urlpatterns(main_admin_urlpatterns):
    pass

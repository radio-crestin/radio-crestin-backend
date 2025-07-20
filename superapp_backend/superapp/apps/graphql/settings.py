def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] += [
        'strawberry_django',
        'superapp.apps.graphql',
    ]
    main_settings['MIDDLEWARE'] += [
        'superapp.apps.graphql.middleware.GraphQlTokenAuthMiddleware',
    ]
    main_settings['DATA_UPLOAD_MAX_MEMORY_SIZE'] = 1024 * 1024 * 10  # 10MB
    main_settings['MIDDLEWARE'] = [
        middleware for middleware in main_settings['MIDDLEWARE']
        if middleware != 'debug_toolbar.middleware.DebugToolbarMiddleware'
    ] + [
        'strawberry_django.middlewares.debug_toolbar.DebugToolbarMiddleware',
    ]

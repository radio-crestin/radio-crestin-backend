def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] += [
        'strawberry_django',
        'superapp.apps.graphql',
    ]
    main_settings['MIDDLEWARE'] += [
        'superapp.apps.graphql.middleware.GraphQlSuperuserApiAuthMiddleware',
    ]
    main_settings['DATA_UPLOAD_MAX_MEMORY_SIZE'] = 1024 * 1024 * 10  # 10MB

    # Replace Django's debug toolbar with Strawberry's version (only in DEBUG mode)
    debug = main_settings.get('DEBUG', False)
    main_settings['MIDDLEWARE'] = [
        middleware for middleware in main_settings['MIDDLEWARE']
        if middleware != 'debug_toolbar.middleware.DebugToolbarMiddleware'
    ]
    if debug:
        main_settings['MIDDLEWARE'] += [
            'strawberry_django.middlewares.debug_toolbar.DebugToolbarMiddleware',
        ]

    # Add connection abort handler middleware early in the chain
    main_settings['MIDDLEWARE'].insert(0, 'superapp.apps.graphql.middleware.ConnectionAbortMiddleware')

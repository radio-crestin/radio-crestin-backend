import os

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def reverse_lazy_with_params(viewname, urlconf=None, args=None, kwargs=None, current_app=None, params=None):
    """
    Lazy version of reverse with query parameters.
    Both the URL and the parameters are evaluated lazily.
    """
    lazy_url = reverse_lazy(viewname, urlconf, args, kwargs, current_app)
    
    if params is None:
        return lazy_url
    
    def _add_params():
        url = lazy_url.__str__()
        param_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{url}?{param_string}" if param_string else url
    
    # Create a lazy object that will evaluate the URL with parameters when needed
    from django.utils.functional import lazy
    return lazy(_add_params, str)()


def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] = ['superapp.apps.authentication',] + main_settings['INSTALLED_APPS'] + [
        'guardian',
        "phonenumber_field",
        'django.contrib.humanize',
        'allauth',
        'allauth.account',
        'allauth.usersessions',
        'allauth.socialaccount',
        'allauth.socialaccount.providers.google',
        'allauth.socialaccount.providers.sms',
        "widget_tweaks",
        "slippers",
        "turnstile",
    ]
    main_settings['GUARDIAN_MONKEY_PATCH'] = False
    main_settings['AUTH_USER_MODEL'] = "authentication.User"
    main_settings['AUTHENTICATION_BACKENDS'] = [
        "superapp.apps.authentication.backend.EmailBackend",
        "django.contrib.auth.backends.ModelBackend",
        "guardian.backends.ObjectPermissionBackend",
        'allauth.account.auth_backends.AuthenticationBackend',
    ]
    main_settings['AUTH_PASSWORD_VALIDATORS'] = [
        {
            "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        },
    ]
    main_settings['MIDDLEWARE'] += [
        'superapp.apps.authentication.middleware.TokenAuthenticationMiddleware',
        "allauth.account.middleware.AccountMiddleware",
    ]
    # Define tabs for User model
    main_settings.setdefault('UNFOLD', {}).setdefault('TABS', []).append({
        "models": [
            "authentication.user",
        ],
        # List of tab items
        "items": [
            {
                "title": _("Authenticated Users"),
                "link": reverse_lazy_with_params("admin:authentication_user_changelist", params={"user_type": "authenticated"}),
            },
            {
                "title": _("Anonymous Users"),
                "link": reverse_lazy_with_params("admin:authentication_user_changelist", params={"user_type": "anonymous"}),
            },
        ],
    })
    
    main_settings['UNFOLD']['SIDEBAR']['navigation'] += [
        {
            "title": _("Users"),
            "icon": "person",
            "permission": lambda request: request.user.has_perm('authentication.view_user'),
            "items": [
                {
                    "title": _("Users"),
                    "icon": "person",  # Icons from https://fonts.google.com/icons
                    "link": reverse_lazy_with_params("admin:authentication_user_changelist", params={"user_type": "authenticated"}),  # add url pattern here
                    "permission": lambda request: request.user.has_perm('authentication.view_user'),
                },
                {
                    "title": _("Groups"),
                    "icon": "group",  # Icons from https://fonts.google.com/icons
                    "link": reverse_lazy("admin:auth_group_changelist"),  # add url pattern here
                    "permission": lambda request: request.user.has_perm('auth.view_group'),
                },
            ]
        }
    ]
    main_settings.update({
        'LOGIN_URL': "homepage_login",
    })
    main_settings['ALLAUTH_UI_THEME'] = 'dark'
    main_settings['ACCOUNT_USER_MODEL_USERNAME_FIELD'] = None
    main_settings['ACCOUNT_SIGNUP_FIELDS'] = ['email*', 'password1*', 'password2*']
    # main_settings['ACCOUNT_DEFAULT_HTTP_PROTOCOL'] = "https"
    main_settings['ACCOUNT_LOGIN_METHODS'] = {'email'}
    main_settings['ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION'] = True
    main_settings['ACCOUNT_LOGIN_ON_PASSWORD_RESET'] = True
    main_settings['ACCOUNT_EMAIL_VERIFICATION'] = 'optional'
    main_settings['ACCOUNT_LOGIN_BY_ACCOUNT_PASSWORD_VISIBLE'] = False
    main_settings['ACCOUNT_LOGIN_BY_ACCOUNT_PASSWORD_ENABLED'] = True
    main_settings['ACCOUNT_LOGIN_BY_CODE_ENABLED'] = True

    main_settings['ACCOUNT_FORMS'] = {
        'homepage_login': 'superapp.apps.authentication.forms.TurnstailSMSLoginForm',
        'request_login_code': 'superapp.apps.authentication.forms.TurnstailRequestLoginCodeForm',
        'confirm_login_code': 'superapp.apps.authentication.forms.TurnstailConfirmLoginCodeForm',
        'confirm_email_verification_code': 'superapp.apps.authentication.forms.TurnstailConfirmEmailVerificationCodeForm',
        'sms_login': 'superapp.apps.authentication.forms.TurnstailSMSLoginForm',
        'sms_verify': 'superapp.apps.authentication.forms.TurnstailSMSVerifyForm',
    }

    main_settings['ACCOUNT_SESSION_REMEMBER'] = True
    main_settings['SOCIALACCOUNT_EMAIL_REQUIRED'] = False
    main_settings['SOCIALACCOUNT_EMAIL_VERIFICATION'] = 'optional'
    main_settings['SOCIALACCOUNT_AUTO_SIGNUP'] = True
    main_settings['SOCIALACCOUNT_PROVIDERS'] = {
        'google': {
            'FETCH_USERINFO': True,
            'SCOPE': [
                # 'profile',
                'email',
            ],
            'AUTH_PARAMS': {
                'access_type': 'online',
            },
            # 'OAUTH_PKCE_ENABLED': True,
            'EMAIL_AUTHENTICATION': True,
            'EMAIL_AUTHENTICATION_AUTO_CONNECT': True,
            "APP": {
                'client_id': os.environ['AUTH_GOOGLE_ID'],
                'secret': os.environ['AUTH_GOOGLE_SECRET'],
                "key": "",
                "settings": {
                    # You can fine tune these settings per app:
                    "scope": [
                        "profile",
                        "email",
                    ],
                    "auth_params": {
                        "access_type": "online",
                    },
                    'FETCH_USERINFO' : True,
                    'OAUTH_PKCE_ENABLED': True,
                },
            },
        } if 'AUTH_GOOGLE_ID' in os.environ else {},
        'sms': {
            'SMS_VERIFICATION_HANDLER': 'superapp.apps.prelude_sms.authentication_handlers.PreludeSMSVerificationHandler',
            "LOGIN_FORM_CLASS": "superapp.apps.authentication.forms.TurnstailSMSLoginForm",
            "VERIFY_FORM_CLASS": "superapp.apps.authentication.forms.TurnstailSMSVerifyForm",
            "APP": {
               "settings": {
                   "hidden": True,
               },
            }
        }
    }
    main_settings['USERSESSIONS_TRACK_ACTIVITY'] = True
    main_settings['MIDDLEWARE'] += [
        'allauth.usersessions.middleware.UserSessionsMiddleware',
    ]
    if 'RESEND_API_KEY' in os.environ:
        main_settings['EMAIL_BACKEND'] = 'django.core.mail.backends.smtp.EmailBackend'
        main_settings['DEFAULT_FROM_EMAIL'] = os.environ['RESEND_FROM_EMAIL']
        main_settings['EMAIL_HOST'] = 'smtp.resend.com'
        main_settings['EMAIL_PORT'] = 465
        main_settings['EMAIL_USE_SSL'] = True
        main_settings['EMAIL_HOST_USER'] = 'resend'
        main_settings['EMAIL_HOST_PASSWORD'] = os.environ['RESEND_API_KEY']

    main_settings['PHONENUMBER_DEFAULT_REGION'] = 'RO'
    main_settings['PHONENUMBER_DEFAULT_FORMAT'] = 'NATIONAL'
    main_settings['PHONENUMBER_DB_FORMAT'] = 'E164'

    main_settings['TURNSTILE_SITEKEY'] = os.environ.get('TURNSTILE_SITEKEY')
    main_settings['TURNSTILE_SECRET'] = os.environ.get('TURNSTILE_SECRET')
    main_settings['TURNSTILE_DEFAULT_CONFIG'] = {
        # 'onload': 'name_of_js_function',
        # 'render': 'explicit',
        # 'theme': 'auto',  # do not use data- prefix
        # 'size': 'compact',  # do not use data- prefix
    }

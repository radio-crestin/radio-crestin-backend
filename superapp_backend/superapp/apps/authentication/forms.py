from allauth.account.forms import RequestLoginCodeForm, ConfirmLoginCodeForm, ConfirmEmailVerificationCodeForm
from allauth.socialaccount.providers.sms.forms import SMSLoginForm, SMSVerifyForm
from turnstile.fields import TurnstileField
from turnstile.widgets import TurnstileWidget


class HiddenLabelTurnstileWidget(TurnstileWidget):
    """Custom Turnstile widget that hides the label completely with CSS."""
    
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs = attrs or {}
        # Add a class that we can target with CSS
        css_class = self.attrs.get('class', '')
        self.attrs['class'] = f"{css_class} hidden-label-captcha".strip()
    
    def render(self, name, value, attrs=None, renderer=None):
        output = super().render(name, value, attrs, renderer)
        # Add inline style to hide the label
        style = '<style>label[for="id_captcha"] {display: none !important;}</style>'
        return style + output


class TurnstailSMSLoginForm(SMSLoginForm):
    captcha = TurnstileField(label='', widget=HiddenLabelTurnstileWidget())


class TurnstailSMSVerifyForm(SMSVerifyForm):
    captcha = TurnstileField(label='', widget=HiddenLabelTurnstileWidget())


class TurnstailRequestLoginCodeForm(RequestLoginCodeForm):
    captcha = TurnstileField(label='', widget=HiddenLabelTurnstileWidget())


class TurnstailConfirmLoginCodeForm(ConfirmLoginCodeForm):
    captcha = TurnstileField(label='', widget=HiddenLabelTurnstileWidget())

class TurnstailConfirmEmailVerificationCodeForm(ConfirmEmailVerificationCodeForm):
    captcha = TurnstileField(label='', widget=HiddenLabelTurnstileWidget())

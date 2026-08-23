from django.forms import ModelForm

from catalog.models import Thread


class ThreadModelForm(ModelForm):
    class Meta:
        model = Thread
        fields = ['name', 'discount', 'product']



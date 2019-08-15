#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import Asset, Project
from orgs.mixins import OrgModelForm
from orgs.utils import current_org


class ProjectCreateForm(OrgModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sa_users_field = self.fields.get('sa_users')
        dev_users_field = self.fields.get('dev_users')
        scrum_master_field = self.fields.get('scrum_master')
        if hasattr(dev_users_field, 'queryset'):
            dev_users_field.queryset = current_org.get_org_users()
        if hasattr(sa_users_field, 'queryset'):
            sa_users_field.queryset = current_org.get_org_users()
        if hasattr(scrum_master_field, 'queryset'):
            scrum_master_field.queryset = current_org.get_org_users()

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get("level")

        if int(level) > 4 or int(level) < 0:
            raise forms.ValidationError('level must in 0-4')

    class Meta:
        model = Project
        fields = [
            "name", "type", "domain_name", "git_address", "port", "dev_users", "sa_users", "scrum_master", "comment", "parent", "level"
        ]
        widgets = {
            'sa_users': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Sa Users')
            }),
            'dev_users': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Dev Users')
            }),
            'type': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Project Type')
            }),
            'parent': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Parent')
            }),
            'scrum_master': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Scrum Master')
            }),
            'port': forms.TextInput(),
        }

        help_texts = {
            'level': '0-4, 0 top level'
        }


class ProjectForm(forms.ModelForm):
    # See AdminUserForm comment same it
    assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.all(),
        label=_('Asset'),
        required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'select2', 'data-placeholder': _('Select assets')})
        )

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            initial = kwargs.get('initial', {})
            initial['assets'] = kwargs['instance'].assets.all()
        super(ProjectForm, self).__init__(*args, **kwargs)

    def _save_m2m(self):
        super(ProjectForm, self)._save_m2m()
        assets = self.cleaned_data['assets']
        self.instance.assets.clear()
        self.instance.assets.add(*tuple(assets))

    class Meta:
        model = Project
        fields = [
            "name", "type", "domain_name", "git_address", "port", "dev_users", "sa_users", "scrum_master", "comment", "level"
        ]
        help_texts = {
            'name': '* required',
            'type': '* required',
            'level': '0-4, 0 lower level'
        }

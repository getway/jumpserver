#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models
import logging
from django.utils.translation import ugettext_lazy as _
import uuid
from django.core.cache import cache

__all__ = ['Project', 'TYPE_CHOICES']
logger = logging.getLogger(__name__)

TYPE_CHOICES = (
        ('Java', 'java'),
        ('React', 'react'),
        ('Cpp', 'c++'),
        ('Python', 'python'),
        ('Middleware', 'Middleware'),
        ('Other', 'Other'),
    )


class Project(models.Model):
    TYPE_CHOICES =TYPE_CHOICES

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))

    parent = models.ForeignKey('self', null=True, blank=True, related_name="children", on_delete=models.SET_NULL)

    domain_name = models.CharField(max_length=64, blank=True, verbose_name=_('Domain Name'))
    git_address = models.CharField(max_length=128, blank=True, verbose_name=_('Git Address'))
    port = models.IntegerField(blank=True, null=True, verbose_name=_('Open port'))
    type = models.CharField(choices=TYPE_CHOICES, max_length=16, blank=True, null=True,
                            default='Java', verbose_name=_('Project type'), )
    dev_users = models.ManyToManyField(
        'users.User', related_name='users1',
        blank=True, verbose_name=_('Dev Users')
    )
    sa_users = models.ManyToManyField(
        'users.User', related_name='users2',
        blank=True, verbose_name=_('Sa Users')
    )
    scrum_master = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, verbose_name=_('Scrum Master'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    updated_by = models.CharField(max_length=32, blank=True, verbose_name=_('Updated by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('Date created'))
    date_updated = models.DateTimeField(auto_now=True, null=True, verbose_name=_('Date updated'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    level = models.IntegerField(default=0, verbose_name=_('Level'))

    def __unicode__(self):
        return self.name
    __str__ = __unicode__

    @property
    def all_sa_users(self):
        return [user.name for user in self.sa_users.all()]

    @property
    def all_dev_users(self):
        return [user.name for user in self.dev_users.all()]

    def get_related_assets(self):
        assets = self.assets.all()
        return assets

    def get_related_assets_ip(self):
        assets = self.assets.all()
        return [{'ip': asset.ip, 'environment': asset.environment} for asset in assets]

    @property
    def all_assets_ip(self):
        return self.get_related_assets_ip()

    class Meta:
        ordering = ['name']


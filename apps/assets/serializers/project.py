#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin
from rest_framework import serializers
from ..models import Project, Asset


class ProjectSerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'

    @staticmethod
    def get_asset_count(obj):
        return obj.assets.count()


class ProjectAssetsSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'name', 'port']
        model = Project

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend([
            'all_assets_ip'
        ])
        return fields


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """update the project, and add or delete the asset to the project"""
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Project
        fields = ['id', 'assets']


class AssetUpdateProjectSerializer(serializers.ModelSerializer):
    projects = serializers.PrimaryKeyRelatedField(many=True, queryset=Project.objects.all())

    class Meta:
        model = Asset
        fields = ['id', 'projects']


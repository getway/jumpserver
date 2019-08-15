#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rest_framework_bulk import BulkModelViewSet
from common.mixins import IDInFilterMixin
from common.utils import get_logger
from ..models import Project, Asset
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from .. import serializers
from rest_framework import generics, viewsets
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import get_object_or_404
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from rest_framework.response import Response

logger = get_logger(__file__)

__all__ = [
    'ProjectViewSet', 'AssetUpdateProjectApi', 'ProjectUpdateApi',
    'ProjectAssetsListView', 'ProjectAssetsViewSet',
]


class ProjectViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    project api set, for add,delete,update,list,retrieve resource
    """

    filter_fields = ("name", "type")
    search_fields = filter_fields
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    permission_classes = (IsOrgAdmin,)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = super().get_queryset().all()
        return queryset


class ProjectAssetsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    project assets api set, for add,delete,update,list,retrieve resource
    """
    filter_fields = ("id", "name")
    search_fields = filter_fields
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectAssetsSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = super().get_queryset().all()
        return queryset


class AssetUpdateProjectApi(generics.RetrieveUpdateAPIView):
    """Asset update it's project api"""
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetUpdateProjectSerializer
    permission_classes = (IsOrgAdmin,)

    def perform_update(self, serializer):
        # 新增操作项目主机日志详情
        projects_old = [project.name for project in serializer.instance.projects.all()]
        instance = serializer.save()
        projects_update = [project.name for project in instance.projects.all()]
        add_projects = ','.join(set(projects_update).difference(set(projects_old)))
        del_projects = ','.join(set(projects_old).difference(set(projects_update)))
        changed_data = ''
        if add_projects:
            changed_data = "Add:{}".format(add_projects)
        if del_projects:
            changed_data = "Del:{}".format(del_projects)
        if add_projects and del_projects:
            changed_data = "Add:{}; Del:{}".format(add_projects, del_projects)
        # signal_resource_changed.send(sender=instance, action='update_projects', resource=str(instance), changed=changed_data)


class ProjectUpdateApi(generics.RetrieveUpdateAPIView):
    """Project, update it's asset member"""
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectUpdateSerializer
    permission_classes = (IsOrgAdmin,)

    def perform_update(self, serializer):
        # 新增操作项目主机日志详情
        assets_old = [asset.ip for asset in serializer.instance.assets.all()]
        instance = serializer.save()
        assets_update = [asset.ip for asset in instance.assets.all()]
        add_assets = ','.join(set(assets_update).difference(set(assets_old)))
        del_assets = ','.join(set(assets_old).difference(set(assets_update)))
        changed_data = ''
        if add_assets:
            changed_data = "Add:{}".format(add_assets)
        if del_assets:
            changed_data = "Del:{}".format(del_assets)
        if add_assets and del_assets:
            changed_data = "Add:{}; Del:{}".format(add_assets, del_assets)
        # signal_resource_changed.send(sender=instance, action='update_assets', resource=str(instance), changed=changed_data)


class ProjectAssetsListView(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetSimpleSerializer
    pagination_class = LimitOffsetPagination
    filter_fields = ("hostname", "ip", "environment")
    http_method_names = ['get']
    search_fields = filter_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Project, pk=pk)

    def get_queryset(self):
        project = self.get_object()
        return project.get_related_assets()

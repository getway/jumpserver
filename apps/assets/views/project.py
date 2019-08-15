# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin

from common.const import create_success_msg, update_success_msg
from .. import forms
from ..models import Project, Asset
from common.permissions import AdminUserRequiredMixin
import json
import uuid
import csv
import codecs
import chardet
from io import StringIO
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views import View
from django.http import HttpResponse, JsonResponse
from common.mixins import JSONResponseMixin
from common.utils import get_logger, get_object_or_none, is_uuid, ssh_key_gen
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import (
    CreateView, UpdateView, FormView
)
from django.db import transaction


__all__ = [
    'ProjectCreateView', 'ProjectDetailView',
    'ProjectDeleteView', 'ProjectListView',
    'ProjectUpdateView', 'ProjectBulkImportView',
    'ProjectExportView', 'ProjectAssetsView',
    'ProjectVarsView'
]


class ProjectListView(AdminUserRequiredMixin, TemplateView):
    model = Project
    template_name = 'assets/project_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Project list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ProjectCreateView(AdminUserRequiredMixin,
                          SuccessMessageMixin,
                          CreateView):
    model = Project
    form_class = forms.ProjectCreateForm
    template_name = 'assets/project_create.html'
    success_url = reverse_lazy('assets:project-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create project')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ProjectUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Project
    form_class = forms.ProjectCreateForm
    template_name = 'assets/project_create.html'
    success_url = reverse_lazy('assets:project-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update project'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ProjectDetailView(AdminUserRequiredMixin, DetailView):
    model = Project
    template_name = 'assets/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        assets_remain = Asset.objects.exclude(id__in=self.object.assets.all())
        project_list = []
        project_list.reverse()
        context = {
            'app': _('Assets'),
            'action': _('Project detail'),
            'assets_remain': assets_remain,
            'assets': [asset for asset in Asset.objects.all()
                       if asset not in assets_remain],
            'project_list': project_list,
        }
        kwargs.update(context)
        return super(ProjectDetailView, self).get_context_data(**kwargs)


class ProjectDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Project
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:project-list')


@method_decorator(csrf_exempt, name='dispatch')
class ProjectExportView(View):
    def get(self, request):
        fields = [
            Project._meta.get_field(name)
            for name in [
                "id", "name", "type", "domain_name", "git_address", "port", "comment"
            ]
        ]
        spm = request.GET.get('spm', '')
        projects_id = cache.get(spm, [])
        filename = 'projects-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        projects = Project.objects.filter(id__in=projects_id)
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        # header.append(_('User groups'))
        writer.writerow(header)

        for project in projects:
            # groups = ','.join([group.name for group in project.groups.all()])
            data = [getattr(project, field.name) for field in fields]
            # data.append(groups)
            writer.writerow(data)

        return response

    def post(self, request):
        try:
            projects_id = json.loads(request.body).get('projects_id', [])
        except ValueError:
            return HttpResponse('Json object not valid', status=400)
        spm = uuid.uuid4().hex
        cache.set(spm, projects_id, 300)
        url = reverse('assets:project-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


class ProjectBulkImportView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = forms.FileForm

    def form_invalid(self, form):
        try:
            error = form.errors.values()[-1][-1]
        except Exception as e:
            error = _('Invalid file.')
        data = {
            'success': False,
            'msg': error
        }
        return self.render_json_response(data)

    # todo: need be patch, method to long
    def form_valid(self, form):
        f = form.cleaned_data['file']
        det_result = chardet.detect(f.read())
        f.seek(0)  # reset file seek index
        data = f.read().decode(det_result['encoding']).strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        header_ = csv_data[0]
        fields = [
            Project._meta.get_field(name)
            for name in [
                "id", "name", "type", "domain_name", "git_address", "port", "comment"
            ]
        ]
        mapping_reverse = {field.verbose_name: field.name for field in fields}
        # mapping_reverse[_('User groups')] = 'groups'
        attr = [mapping_reverse.get(n, None) for n in header_]
        if None in attr:
            data = {'valid': False,
                    'msg': 'Must be same format as '
                           'template or export file'}
            return self.render_json_response(data)

        created, updated, failed = [], [], []
        for row in csv_data[1:]:
            if set(row) == {''}:
                continue
            project_dict = dict(zip(attr, row))
            id_ = project_dict.pop('id')
            for k, v in project_dict.items():
                # if k in ['is_active']:
                #     if v.lower() == 'false':
                #         v = False
                #     else:
                #         v = bool(v)
                # elif k == 'groups':
                #     groups_name = v.split(',')
                #     v = UserGroup.objects.filter(name__in=groups_name)
                # else:
                #     continue
                project_dict[k] = v
            project = get_object_or_none(Project, id=id_) if id_ and is_uuid(id_) else None
            if not project:
                try:
                    with transaction.atomic():
                        # groups = project_dict.pop('groups')
                        project = Project.objects.create(**project_dict)
                        # user.groups.set(groups)
                        created.append(project_dict['name'])
                        # post_user_create.send(self.__class__, user=user)
                except Exception as e:
                    failed.append('%s: %s' % (project_dict['name'], str(e)))
            else:
                for k, v in project_dict.items():
                    # if k == 'groups':
                    #     user.groups.set(v)
                    #     continue
                    if v:
                        setattr(project, k, v)
                try:
                    project.save()
                    updated.append(project_dict['name'])
                except Exception as e:
                    failed.append('%s: %s' % (project_dict['name'], str(e)))

        data = {
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'updated': updated,
            'updated_info': 'Updated {}'.format(len(updated)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'valid': True,
            'msg': 'Created: {}. Updated: {}, Error: {}'.format(
                len(created), len(updated), len(failed))
        }
        return self.render_json_response(data)


class ProjectAssetsView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    template_name = 'assets/project_assets.html'
    context_object_name = 'project'
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Project.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        self.queryset = self.object.assets.all()
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Project detail'),
            "total_amount": len(self.queryset),
            'unreachable_amount': len([asset for asset in self.queryset if asset.connectivity is False])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ProjectVarsView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    template_name = 'assets/project_values.html'
    context_object_name = 'project'
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Project.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        self.queryset = self.object.assets.all()
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Project detail'),
            "total_amount": len(self.queryset),
            'unreachable_amount': len([asset for asset in self.queryset if asset.connectivity is False]),
            'env_list': [str(env[0]).lower() for env in Asset.ENV_CHOICES]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
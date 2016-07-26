from django.conf.urls import *
from django.contrib import admin
from django.views.generic import TemplateView
from django.contrib import admin

handler500 = 'djangotoolbox.errorviews.server_error'

admin.site.site_title = 'My Server'
admin.site.site_header = 'My Server Administration'
admin.site.index_title = 'My Server Administration'

admin.autodiscover()

urlpatterns = patterns('',
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),
    (r'^admin/', include(admin.site.urls)),
    url(r'^Client/', include('openplaykit.urls')),
    (r'^$', TemplateView.as_view(template_name="home.html")),
)

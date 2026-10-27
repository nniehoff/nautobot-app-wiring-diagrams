"""Django urlpatterns declaration for nautobot_wiring_diagrams app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_wiring_diagrams import views

app_name = "nautobot_wiring_diagrams"
router = NautobotUIViewSetRouter()


urlpatterns = [
    path("", views.WiringDiagramView.as_view(), name="wiring_diagram"),
    path("export/<str:scope>/<uuid:pk>/", views.WiringDiagramExportView.as_view(), name="export"),
    path("locations/<uuid:pk>/", views.LocationWiringDiagramView.as_view(), name="location_wiring_diagram_tab"),
    path("racks/<uuid:pk>/", views.RackWiringDiagramView.as_view(), name="rack_wiring_diagram_tab"),
    path("devices/<uuid:pk>/", views.DeviceWiringDiagramView.as_view(), name="device_wiring_diagram_tab"),
    path("docs/", RedirectView.as_view(url=static("nautobot_wiring_diagrams/docs/index.html")), name="docs"),
]

urlpatterns += router.urls

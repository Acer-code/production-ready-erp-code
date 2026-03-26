from dal import autocomplete
from .models import SparePart

class SparePartAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):

        qs = SparePart.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
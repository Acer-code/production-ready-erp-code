from django.core.paginator import Paginator

def paginate_queryset(request, queryset, per_page=10):
    page_number = request.GET.get('page')
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page_number)
    return page_obj

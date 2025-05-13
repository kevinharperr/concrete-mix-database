# concrete_mix_app/templatetags/url_params.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def get_current_url_params(context, exclude=None):
    """
    Returns the current request's GET parameters as a URL-encoded string,
    optionally excluding specified parameters.
    exclude: A comma-separated string of parameter names to exclude.
    """
    request = context['request']
    params = request.GET.copy()
    if exclude:
        exclude_list = [e.strip() for e in exclude.split(',')]
        for param_to_exclude in exclude_list:
            if param_to_exclude in params:
                del params[param_to_exclude]
    # Ensure 'page' is always excluded for pagination links unless explicitly included
    # in the exclude list by the caller (which is unlikely for pagination).
    # However, the logic in the template handles 'page' separately now, so this might be redundant.
    # Keeping the explicit exclude list as the primary mechanism.
    # if 'page' in params and ('page' not in exclude_list if exclude else True):
    #      del params['page']
    return params.urlencode()

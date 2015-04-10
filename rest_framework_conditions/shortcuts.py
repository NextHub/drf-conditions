# TODO: This is a temporary hack used by NextHub because we are bad people
def is_nested_url_for_current_user(request, view):
    """
    Checks whether or not this URL is owned by the current user.
    """
    kwargs = view.kwargs
    user = request.user

    lookup_kwarg = getattr(
        view, 'parent_lookup_url_kwarg', 'parent_lookup_user'
    )

    if not user.is_authenticated():
        return False

    if lookup_kwarg not in kwargs:
        return False

    lookup = kwargs[lookup_kwarg]
    return user.id == int(lookup)


def is_url_for_list_view(request, view):
    """
    Makes an educated guess about if this URL is for a list view.
    """
    if hasattr(view, 'lookup_url_kwarg'):
        kwarg_name = view.lookup_url_kwarg or view.lookup_field
    else:  # TODO: remove in DRF 3
        kwarg_name = view.pk_url_kwarg or view.slug_url_kwarg
    return not (kwarg_name and kwarg_name in view.kwargs)

from django.utils import six

from rest_framework.permissions import BasePermission, SAFE_METHODS

from rest_framework_conditions.shortcuts import is_url_for_list_view, \
    is_nested_url_for_current_user


class ConditionPermission(BasePermission):
    """
    Permission for evaluating a condition class.
    """

    def get_condition(self, view):
        condition_class = getattr(view, 'condition_class', None)

        if condition_class is None:
            return TrueCondition()

        return condition_class()

    def has_permission(self, request, view):
        condition = self.get_condition(view)
        return condition.has_permission(request, view) is True

    def has_object_permission(self, request, view, obj):
        condition = self.get_condition(view)
        return condition.has_object_permission(request, view, obj) is True


class BaseConditionMeta(type):
    """
    Allows combining conditions using bitwise operands.
    """

    def operator_and(cls, operands, method, *args, **kwargs):
        """
        Condition operator method for performing an `or` operation.
        """
        # Extract the operand classes.
        ca, cb = operands

        # Evaluate the left operand class.
        va = getattr(ca(), method)(*args, **kwargs)

        # The statement is False if the left value is False.
        if va is False:
            return False

        # Evaluate the right operand class.
        vb = getattr(cb(), method)(*args, **kwargs)

        # Return the right value if the left one should be ignored.
        if va is None:
            return vb

        # Return the left value if the right one should be ignored.
        if vb is None:
            return va

        # The statement is True if the right value is True.
        return vb is True

    operator_and.subclass_name = '({} & {})'

    def operator_invert(cls, operands, method, *args, **kwargs):
        """
        Condition operator method for performing an `invert` operation.
        """
        # Extract the operand class.
        ca = operands[0]

        # Evaluate the operand class.
        va = getattr(ca(), method)(*args, **kwargs)

        # Do nothing if the value should be ignored.
        if va is None:
            return None

        # Invert the value.
        return va is False

    operator_invert.subclass_name = '(~{})'

    def operator_or(cls, operands, method, *args, **kwargs):
        """
        Condition operator method for performing an `or` operation.
        """
        # Extract the operand classes.
        ca, cb = operands

        # Evaluate the left operand class.
        va = getattr(ca(), method)(*args, **kwargs)

        # The statement is True if the left value is True.
        if va is True:
            return True

        # Evaluate the right operand class.
        vb = getattr(cb(), method)(*args, **kwargs)

        # Return the right value if the left one should be ignored.
        if va is None:
            return vb

        # Return the left value if the right one should be ignored.
        if vb is None:
            return va

        # The statement is True if the right value is True.
        return vb is True

    operator_or.subclass_name = '({} | {})'

    def create_operation_subclass(cls, operator, operands):
        """
        Creates a new operation condition subclass.
        """
        try:
            names = (operand.__name__ for operand in operands)
            name = operator.subclass_name.format(*names)
        except (AttributeError, KeyError):
            name = 'AnonymousConditionOperation'

        attributes = {
            'operator': operator,
            'operands': operands,
        }

        return type(name, (OperationCondition,), attributes)

    def __and__(cls, other):
        return cls.create_operation_subclass(cls.operator_and, (cls, other))

    def __or__(cls, other):
        return cls.create_operation_subclass(cls.operator_or, (cls, other))

    def __iand__(cls, other):
        return cls.create_operation_subclass(cls.operator_and, (cls, other))

    def __ior__(cls, other):
        return cls.create_operation_subclass(cls.operator_or, (cls, other))

    def __invert__(cls):
        return cls.create_operation_subclass(cls.operator_invert, (cls,))

    def __repr__(cls):
        name = getattr(cls, '__name__', 'Unknown')
        return '<class \'{}\'>'.format(name)


@six.add_metaclass(BaseConditionMeta)
class BaseCondition(object):
    """
    The base class for conditions.
    """

    def has_permission(self, request, view):
        return None

    def has_object_permission(self, request, view, obj):
        return None


# noinspection PyUnresolvedReferences
class OperationCondition(BaseCondition):
    """
    Performs an operation on one or more conditions.
    """

    def __init__(self):
        assert self.operator is not None
        assert self.operands is not None

    def has_permission(self, view, request):
        return self.operator(self.operands, 'has_permission', view, request)

    def has_object_permission(self, view, request, obj):
        return self.operator(
            self.operands, 'has_object_permission', view, request, obj
        )


class TrueCondition(BaseCondition):
    """
    Condition which allows anything.
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return True


class FalseCondition(BaseCondition):
    """
    Condition which denies everything.
    """

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class ObjectCondition(BaseCondition):
    """
    Condition which is false for "has permission" and true for
    "has object permission".
    """

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return True


class ReadCondition(BaseCondition):
    """
    Condition which allows reading.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS


class AuthenticatedCondition(BaseCondition):
    """
    Condition which requires user to be authenticated.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated()

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated()


class StaffCondition(BaseCondition):
    """
    Condition which requires user to be staff.
    """

    def has_permission(self, request, view):
        return request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff


class SuperuserCondition(BaseCondition):
    """
    Condition which requires user to be superuser.
    """

    def has_permission(self, request, view):
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser


class NestedResourceOwnerCondition(BaseCondition):
    """
    Condition which requires the URL to belong to the current user.
    """

    def has_permission(self, request, view):
        return is_nested_url_for_current_user(request, view)

    def has_object_permission(self, request, view, obj):
        return is_nested_url_for_current_user(request, view)


class RequestMethodCondition(BaseCondition):
    """
    Condition which allows a specific request method.
    """
    request_method = None

    def __init__(self):
        assert self.request_method is not None

    def has_permission(self, request, view):
        return request.method == self.request_method

    def has_object_permission(self, request, view, obj):
        return request.method == self.request_method


class GetCondition(RequestMethodCondition):
    """
    Condition which allows GET requests.
    """
    request_method = 'GET'


class PostCondition(RequestMethodCondition):
    """
    Condition which allows POST requests.
    """
    request_method = 'POST'


class PutCondition(RequestMethodCondition):
    """
    Condition which allows PUT requests.
    """
    request_method = 'PUT'


class PatchCondition(RequestMethodCondition):
    """
    Condition which allows PATCH requests.
    """
    request_method = 'PATCH'


class DeleteCondition(RequestMethodCondition):
    """
    Condition which allows DELETE requests.
    """
    request_method = 'DELETE'


class ManyCondition(BaseCondition):
    """
    Condition which requires the request to be for many instances.
    """

    def has_permission(self, request, view):
        return is_url_for_list_view(request, view)

    def has_object_permission(self, request, view, obj):
        return is_url_for_list_view(request, view)


class ListCondition(BaseCondition):
    """
    Condition which requires the request to be for listing instances.
    """

    def has_permission(self, request, view):
        return request.method == 'GET' and is_url_for_list_view(request, view)

    def has_object_permission(self, request, view, obj):
        return request.method == 'GET' and is_url_for_list_view(request, view)


class CreateCondition(BaseCondition):
    """
    Condition which requires the request to be for creating instances.
    """

    def has_permission(self, request, view):
        return request.method == 'POST' and is_url_for_list_view(request, view)

    def has_object_permission(self, request, view, obj):
        return request.method == 'POST' and is_url_for_list_view(request, view)


class RetrieveCondition(BaseCondition):
    """
    Condition which requires the request to be for retrieving an instance.
    """

    def has_permission(self, request, view):
        return request.method == 'GET' \
            and not is_url_for_list_view(request, view)

    def has_object_permission(self, request, view, obj):
        return request.method == 'GET' \
            and not is_url_for_list_view(request, view)


class UpdateCondition(BaseCondition):
    """
    Condition which requires the request to be for updating an instance.
    """

    def has_permission(self, request, view):
        return request.method in ('PUT', 'PATCH') \
            and not is_url_for_list_view(request, view)

    def has_object_permission(self, request, view, obj):
        return request.method in ('PUT', 'PATCH') \
            and not is_url_for_list_view(request, view)


class DestroyCondition(BaseCondition):
    """
    Condition which requires the request to be for destroying an instance.
    """

    def has_permission(self, request, view):
        return request.method == 'DELETE' \
            and not is_url_for_list_view(request, view)

    def has_object_permission(self, request, view, obj):
        return request.method == 'DELETE' \
            and not is_url_for_list_view(request, view)

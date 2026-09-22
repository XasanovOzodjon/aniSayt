from rest_framework.views import exception_handler


def safe_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and 'detail' in data:
        detail = data.get('detail')
        text = str(detail)
        if 'django' in text.lower() or 'traceback' in text.lower():
            response.data = {'message': 'So‘rov bajarilmadi'}
    return response

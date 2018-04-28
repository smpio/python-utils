from django.http import HttpResponse


NULL_RESPONSE = HttpResponse(b'null', content_type='application/json')

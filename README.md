# python-utils

## Django Settings

* `DEV_ENV`
  * `True` - by default (expected on development/local)
  * `False` - default in docker (expected on production/staging/deployed)
* `CONTAINER_ENV`
  * `False` - by default (expected on IDE)
  * `True` - default in docker
* `DJANGO_DEBUG` sets django `DEBUG`, defaults to value of `DEV_ENV`

Many settings can be set using env vars. There are "super" vars that modify defautls:

* `DEV_ENV == False`
  * `SECRET_KEY` no default
  * `DJANGO_DEBUG = False`
  * `DATABASE_URL = 'postgres://postgres@postgres/postgres'`
  * `CACHE_URL = 'redis://redis/0'`
  * `CELERY_BROKER_URL = 'redis://redis/1'`
  * `CELERY_RESULT_BACKEND_URL = 'redis://redis/2'`
  * `SMP_BASE_URL = 'https://api.smp.io/'`
  * `SMP_MQ_URL = 'amqps://mq.smp.io:5671/'`
* `DEV_ENV == True`
  * `SECRET_KEY = 'dev'`
  * `DJANGO_DEBUG = False`
  * `CELERY_DEFAULT_QUEUE = PROJECT_NAME`
  * `SMP_BASE_URL = 'http://localhost:7000/'`
  * `SMP_MQ_URL = 'amqp://localhost/'`
  * `CONTAINER_ENV == True`
    * ...
  * `CONTAINER_ENV == False`
    * ...

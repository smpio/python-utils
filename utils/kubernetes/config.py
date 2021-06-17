import kubernetes


def configure(api_url=None, in_cluster=False):
    if api_url is not None:
        configuration = kubernetes.client.Configuration()
        configuration.host = api_url
        kubernetes.client.Configuration.set_default(configuration)
    elif in_cluster:
        kubernetes.config.load_incluster_config()
    else:
        kubernetes.config.load_kube_config()

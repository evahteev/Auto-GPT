

class BaseOpenAIPlugin:
    def __init__(self, manifest: dict, openapi_spec: dict):
        self.manifest = manifest
        self.openapi_spec = openapi_spec

    def on_response(self, response: str, *args, **kwargs) -> str:
        """This method is called when a response is received from the model."""
        return response
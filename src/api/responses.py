from fastapi.responses import JSONResponse
import orjson

class ORJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return orjson.dumps(content, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_UUID)

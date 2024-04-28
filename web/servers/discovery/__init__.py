from fastapi import FastAPI, Response, Request
from fastapi.responses import PlainTextResponse

from web.models import DiscoveryResultModel, DiscoveryResultModelEndpoint, MiiverseResultResponse, \
    DiscoveryResultErrorModel

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    print(response.headers)
    del response.headers["Server"]
    return response


@app.get("/", response_class=PlainTextResponse)
async def get_root():
    return "hello from fediiverse discovery / route :3"


@app.get("/v1/endpoint")
async def get_discover(request: Request):
    return MiiverseResultResponse(
        DiscoveryResultModel(
            has_error=False,
            version=1,
            endpoint=DiscoveryResultModelEndpoint(
                host="api.fediiverse.local",  # not used
                api_host="api.fediiverse.local",  # not used (needed for applet later on)
                portal_host="3ds.fediiverse.local",  # not used (wii u)
                n3ds_host="3ds.fediiverse.local",
            )
        )
    )
    """
    return MiiverseResultResponse(
        DiscoveryResultErrorModel(
            has_error=True,
            version=1,
            code=400,
            error_code=4,
            message="SERVICE_CLOSED"
        ),

        status_code=400
    )
    """

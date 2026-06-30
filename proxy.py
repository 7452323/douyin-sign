import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from sign import sign_mobile_request, sign_web_request, Device

app = FastAPI(title="Douyin Sign Proxy")

device = None

@app.on_event("startup")
async def startup():
    global device
    try:
        with open("/opt/douyin-sign/device.json") as f:
            d = json.load(f)
            device = Device.from_dict(d)
            print(f"[proxy] loaded device: {device.device_id}")
    except Exception as e:
        print(f"[proxy] no device.json: {e}")

async def _get_device():
    global device
    if device is not None:
        return device
    from sign import register_device
    device = await register_device()
    with open("/opt/douyin-sign/device.json", "w") as f:
        json.dump(device.to_dict(), f)
    print(f"[proxy] registered device: {device.device_id}")
    return device

@app.get("/api/douyin/mobile/{path:path}")
async def mobile_api(path: str, request: Request):
    try:
        params = dict(request.query_params)
        method = params.pop("method", "GET")
        d = await _get_device()
        result = await sign_mobile_request(
            method=method,
            path="/" + path,
            params=params,
            device=d,
        )
        return result
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            {"error": type(e).__name__, "message": str(e), "hint": "api.douyin.com may be unreachable from this server"},
            status_code=502,
        )

@app.get("/api/douyin/web/{path:path}")
async def web_api(path: str, request: Request):
    params = dict(request.query_params)
    result = sign_web_request(
        path="/" + path,
        params=params,
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8800)

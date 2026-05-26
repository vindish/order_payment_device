from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.payment import PaymentCallbackIn
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/callback")
def payment_callback(
    data: PaymentCallbackIn,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Internal/manual HMAC-signed callback. Useful for tooling and tests."""
    return PaymentService(db).handle_callback(
        order_id=data.order_id,
        provider=data.provider,
        trade_no=data.trade_no,
        token=data.token,
        status=data.status,
        signature=data.signature,
        idempotency_key=idempotency_key,
    )


@router.post("/callback/wechat")
async def wechat_callback(
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    timestamp: str = Header(..., alias="Wechatpay-Timestamp"),
    nonce: str = Header(..., alias="Wechatpay-Nonce"),
    signature: str = Header(..., alias="Wechatpay-Signature"),
):
    """WeChat Pay APIv3 asynchronous notification."""
    raw = (await request.body()).decode("utf-8")
    result = PaymentService(db).handle_wechat_callback(
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
        body=raw,
        idempotency_key=idempotency_key,
    )
    # WeChat treats any non-200 or non-SUCCESS body as a retryable failure.
    return JSONResponse(status_code=200, content=result)


@router.post("/callback/alipay")
async def alipay_callback(
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Alipay asynchronous notification (form-encoded body)."""
    raw = (await request.body()).decode("utf-8")
    # Alipay sends application/x-www-form-urlencoded; fall back to query if needed.
    pairs = parse_qsl(raw, keep_blank_values=True) if raw else list(request.query_params.multi_items())
    params = {key: value for key, value in pairs}
    body = PaymentService(db).handle_alipay_callback(params, idempotency_key=idempotency_key)
    return PlainTextResponse(content=body, status_code=200)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from decimal import Decimal, ROUND_HALF_UP
import uuid

app = FastAPI()

# In-memory store for tips and balances
# In a production environment, this would be a database
store = {
    "tips": [],
    "balances": {}
}

PLATFORM_FEE = Decimal("0.10")  # 10% platform fee

class TipRequest(BaseModel):
    creator_id: str
    gross_amount: Decimal

class BalanceResponse(BaseModel):
    creator_id: str
    balance: Decimal

@app.post("/tips")
def record_tip(tip: TipRequest):
    if tip.gross_amount <= 0:
        raise HTTPException(status_code=400, detail="Gross amount must be positive")
    
    # Calculate creator's share
    creator_share = (tip.gross_amount * (1 - PLATFORM_FEE)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Record the tip
    tip_record = {
        "id": str(uuid.uuid4()),
        "creator_id": tip.creator_id,
        "gross_amount": tip.gross_amount,
        "creator_share": creator_share,
        "platform_fee": tip.gross_amount - creator_share
    }
    store["tips"].append(tip_record)
    
    # Update balance
    if tip.creator_id not in store["balances"]:
        store["balances"][tip.creator_id] = Decimal("0.00")
    store["balances"][tip.creator_id] += creator_share
    
    return tip_record

@app.get("/me/balance", response_model=BalanceResponse)
def get_balance(creator_id: str):
    if creator_id not in store["balances"]:
        return BalanceResponse(creator_id=creator_id, balance=Decimal("0.00"))
    return BalanceResponse(creator_id=creator_id, balance=store["balances"][creator_id])

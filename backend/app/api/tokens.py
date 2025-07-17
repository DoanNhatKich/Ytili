"""
Token API endpoints for Ytili platform
Handles YTILI token operations and rewards
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from ..core.blockchain import blockchain_service
from ..core.supabase import get_supabase_service, Tables
from ..api.supabase_deps import get_current_user_supabase

router = APIRouter()


class TokenRedemptionRequest(BaseModel):
    """Token redemption request schema"""
    option_id: str
    amount: int


class RedemptionOption(BaseModel):
    """Redemption option schema"""
    id: str
    name: str
    description: str
    cost: int
    category: str
    available: bool


@router.get("/balance")
async def get_token_balance(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Get user's token balance and information"""
    
    try:
        supabase = get_supabase_service()
        
        # Get user points from Supabase
        points_result = supabase.table(Tables.USER_POINTS).select("*").eq(
            "user_id", current_user["id"]
        ).execute()
        
        if not points_result.data:
            # Create initial points record
            initial_points = {
                "user_id": current_user["id"],
                "total_points": 0,
                "available_points": 0,
                "lifetime_earned": 0,
                "lifetime_spent": 0,
                "tier_level": "Bronze"
            }
            
            supabase.table(Tables.USER_POINTS).insert(initial_points).execute()
            points_data = initial_points
        else:
            points_data = points_result.data[0]
        
        # Get blockchain token balance if user has wallet
        blockchain_balance = 0
        if current_user.get("wallet_address"):
            blockchain_balance = await blockchain_service.get_user_token_balance(
                current_user["wallet_address"]
            ) or 0
            # Convert from wei to tokens
            blockchain_balance = blockchain_balance / (10**18)
        
        # Get recent transactions (simplified)
        recent_transactions = [
            {
                "id": "tx1",
                "type": "earned",
                "amount": 100,
                "reason": "Donation reward",
                "timestamp": "2024-01-15T10:00:00Z",
                "txHash": "0x123..."
            },
            {
                "id": "tx2", 
                "type": "redeemed",
                "amount": 50,
                "reason": "Medication discount",
                "timestamp": "2024-01-14T15:30:00Z"
            }
        ]
        
        return {
            "balance": points_data["available_points"] + blockchain_balance,
            "earned": points_data["lifetime_earned"],
            "redeemed": points_data["lifetime_spent"],
            "votingPower": blockchain_balance,  # Only blockchain tokens have voting power
            "tier": points_data["tier_level"],
            "recentTransactions": recent_transactions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token balance: {str(e)}"
        )


@router.get("/redemption-options")
async def get_redemption_options() -> List[RedemptionOption]:
    """Get available token redemption options"""
    
    return [
        RedemptionOption(
            id="medication_discount_10",
            name="10% Medication Discount",
            description="Get 10% discount on medication purchases",
            cost=50,
            category="Healthcare",
            available=True
        ),
        RedemptionOption(
            id="medication_discount_20",
            name="20% Medication Discount", 
            description="Get 20% discount on medication purchases",
            cost=100,
            category="Healthcare",
            available=True
        ),
        RedemptionOption(
            id="free_consultation",
            name="Free Medical Consultation",
            description="Get one free consultation with partner doctors",
            cost=200,
            category="Healthcare",
            available=True
        ),
        RedemptionOption(
            id="priority_support",
            name="Priority Customer Support",
            description="Get priority support for 30 days",
            cost=150,
            category="Service",
            available=True
        ),
        RedemptionOption(
            id="premium_features",
            name="Premium Features Access",
            description="Access premium platform features for 30 days",
            cost=300,
            category="Service",
            available=True
        ),
        RedemptionOption(
            id="donation_match",
            name="Donation Matching",
            description="Platform will match your next donation up to 1M VND",
            cost=500,
            category="Donation",
            available=True
        )
    ]


@router.post("/redeem")
async def redeem_tokens(
    redemption_request: TokenRedemptionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Redeem tokens for benefits"""
    
    try:
        # Get redemption options
        options = await get_redemption_options()
        option = next((opt for opt in options if opt.id == redemption_request.option_id), None)
        
        if not option:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Redemption option not found"
            )
        
        if not option.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redemption option not available"
            )
        
        # Check user balance
        balance_data = await get_token_balance(current_user)
        if balance_data["balance"] < option.cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient token balance"
            )
        
        # Update user points
        supabase = get_supabase_service()
        points_result = supabase.table(Tables.USER_POINTS).select("*").eq(
            "user_id", current_user["id"]
        ).execute()
        
        if points_result.data:
            current_points = points_result.data[0]
            new_available = current_points["available_points"] - option.cost
            new_spent = current_points["lifetime_spent"] + option.cost
            
            supabase.table(Tables.USER_POINTS).update({
                "available_points": new_available,
                "lifetime_spent": new_spent
            }).eq("user_id", current_user["id"]).execute()
        
        # If user has wallet address, also redeem from blockchain
        if current_user.get("wallet_address"):
            try:
                await blockchain_service.ytili_token.functions.redeemTokens(
                    current_user["wallet_address"],
                    current_user["id"],
                    option.cost * (10**18),  # Convert to wei
                    redemption_request.option_id
                ).call()
            except Exception as blockchain_error:
                print(f"Blockchain redemption failed: {blockchain_error}")
                # Continue with database redemption only
        
        # Record redemption (simplified)
        # In a real implementation, you would integrate with actual services
        
        return {
            "success": True,
            "message": f"Successfully redeemed {option.name}",
            "redeemed_item": option.name,
            "cost": option.cost,
            "remaining_balance": balance_data["balance"] - option.cost
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token redemption failed: {str(e)}"
        )


@router.post("/mint-reward")
async def mint_reward_tokens(
    user_id: str,
    amount: int,
    reason: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Mint reward tokens (internal use)"""
    
    # This endpoint would typically be called by the system, not directly by users
    # For demo purposes, we'll allow it but in production it should be restricted
    
    try:
        supabase = get_supabase_service()
        
        # Update user points in database
        points_result = supabase.table(Tables.USER_POINTS).select("*").eq(
            "user_id", user_id
        ).execute()
        
        if points_result.data:
            current_points = points_result.data[0]
            new_total = current_points["total_points"] + amount
            new_available = current_points["available_points"] + amount
            new_earned = current_points["lifetime_earned"] + amount
            
            supabase.table(Tables.USER_POINTS).update({
                "total_points": new_total,
                "available_points": new_available,
                "lifetime_earned": new_earned
            }).eq("user_id", user_id).execute()
        
        # Get user wallet address for blockchain minting
        user_result = supabase.table(Tables.USERS).select("wallet_address").eq(
            "id", user_id
        ).execute()
        
        blockchain_tx = None
        if user_result.data and user_result.data[0].get("wallet_address"):
            wallet_address = user_result.data[0]["wallet_address"]
            blockchain_tx = await blockchain_service.mint_reward_tokens(
                user_address=wallet_address,
                user_id=user_id,
                amount=amount * (10**18),  # Convert to wei
                reason=reason
            )
        
        return {
            "success": True,
            "message": "Reward tokens minted successfully",
            "amount": amount,
            "reason": reason,
            "blockchain_tx": blockchain_tx
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mint reward tokens: {str(e)}"
        )


@router.get("/user/history")
async def get_token_history(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """Get user's token transaction history"""
    
    try:
        # In a real implementation, you would fetch from a transactions table
        # For now, return mock data
        
        transactions = [
            {
                "id": "tx1",
                "type": "earned",
                "amount": 100,
                "reason": "Donation reward",
                "timestamp": "2024-01-15T10:00:00Z",
                "txHash": "0x123...",
                "status": "confirmed"
            },
            {
                "id": "tx2",
                "type": "redeemed", 
                "amount": 50,
                "reason": "Medication discount",
                "timestamp": "2024-01-14T15:30:00Z",
                "status": "completed"
            },
            {
                "id": "tx3",
                "type": "earned",
                "amount": 25,
                "reason": "Referral bonus",
                "timestamp": "2024-01-13T09:15:00Z",
                "txHash": "0x456...",
                "status": "confirmed"
            }
        ]
        
        # Apply pagination
        paginated_transactions = transactions[offset:offset + limit]
        
        return {
            "success": True,
            "data": paginated_transactions,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(transactions)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token history: {str(e)}"
        )


@router.get("/contract/info")
async def get_token_contract_info() -> Dict[str, Any]:
    """Get YTILI token contract information"""
    
    return {
        "contract": {
            "address": "0x66C06efE9B8B44940379F5c53328a35a3Abc3Fe7",
            "name": "YtiliToken",
            "symbol": "YTILI",
            "decimals": 18,
            "total_supply": "1000000000000000000000000000",  # 1 billion tokens in wei
            "network": "Saga Blockchain"
        },
        "features": [
            "ERC-20 compatible",
            "Mintable rewards",
            "Redeemable for benefits",
            "Governance voting",
            "Burn mechanism"
        ],
        "reward_rates": {
            "donation": 100,
            "verification": 50,
            "referral": 25
        },
        "redemption_categories": [
            "Healthcare discounts",
            "Premium services",
            "Donation matching",
            "Priority support"
        ]
    }

"""
Governance API endpoints for Ytili platform
Handles proposal creation, voting, and governance operations
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from ..core.blockchain import blockchain_service
from ..core.supabase import get_supabase_service, Tables
from ..api.supabase_deps import get_current_user_supabase
from ..services.notification_service import notification_service
import structlog

logger = structlog.get_logger()
router = APIRouter()


class ProposalCreateRequest(BaseModel):
    """Schema for creating a new proposal"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str = Field(..., pattern="^(platform|donation|token|emergency)$")


class VoteRequest(BaseModel):
    """Schema for casting a vote"""
    proposal_id: int = Field(..., gt=0)
    vote_type: int = Field(..., ge=0, le=2)  # 0=For, 1=Against, 2=Abstain


class ProposalResponse(BaseModel):
    """Schema for proposal response"""
    id: int
    proposer: str
    title: str
    description: str
    category: str
    start_time: datetime
    end_time: datetime
    votes_for: str
    votes_against: str
    votes_abstain: str
    total_votes: str
    executed: bool
    cancelled: bool
    status: int
    blockchain_hash: Optional[str] = None


@router.post("/proposals")
async def create_proposal(
    proposal: ProposalCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Create a new governance proposal"""
    
    try:
        user_id = current_user.get("id")
        
        # Check if user has enough YTILI tokens
        user_balance = await blockchain_service.get_ytili_balance(user_id)
        min_threshold = 1000 * 10**18  # 1000 YTILI tokens
        
        if user_balance < min_threshold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient YTILI tokens. Need at least 1000 YTILI to create proposals."
            )
        
        # Create proposal on blockchain
        blockchain_tx = await blockchain_service.create_governance_proposal(
            proposer=user_id,
            title=proposal.title,
            description=proposal.description,
            category=proposal.category
        )
        
        if not blockchain_tx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create proposal on blockchain"
            )
        
        # Store proposal in database
        supabase = get_supabase_service()
        
        proposal_data = {
            "proposer_id": user_id,
            "title": proposal.title,
            "description": proposal.description,
            "category": proposal.category,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "blockchain_hash": blockchain_tx,
            "status": "active",
            "votes_for": "0",
            "votes_against": "0",
            "votes_abstain": "0",
            "total_votes": "0"
        }
        
        result = supabase.table(Tables.GOVERNANCE_PROPOSALS).insert(proposal_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store proposal in database"
            )
        
        proposal_record = result.data[0]
        
        # Send notification to community
        await notification_service.notify_system_message(
            message=f"New governance proposal: {proposal.title}",
            notification_type="info"
        )
        
        logger.info(
            "Governance proposal created",
            proposal_id=proposal_record["id"],
            proposer=user_id,
            title=proposal.title
        )
        
        return {
            "success": True,
            "proposal_id": proposal_record["id"],
            "blockchain_hash": blockchain_tx,
            "message": "Proposal created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create governance proposal", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create proposal: {str(e)}"
        )


@router.get("/proposals")
async def get_proposals(
    category: Optional[str] = Query(None, pattern="^(platform|donation|token|emergency)$"),
    status: Optional[str] = Query(None, pattern="^(active|succeeded|failed|cancelled|executed)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get governance proposals with filtering"""
    
    try:
        supabase = get_supabase_service()
        
        # Build query
        query = supabase.table(Tables.GOVERNANCE_PROPOSALS).select(
            "*, proposer:users(id, full_name, email)"
        )
        
        if category:
            query = query.eq("category", category)
        
        if status:
            query = query.eq("status", status)
        
        # Execute query with pagination
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        proposals = []
        for proposal in result.data or []:
            # Get additional blockchain data if needed
            blockchain_data = None
            if proposal.get("blockchain_hash"):
                blockchain_data = await blockchain_service.get_proposal_from_blockchain(
                    proposal["id"]
                )
            
            proposal_response = {
                "id": proposal["id"],
                "proposer": proposal.get("proposer", {}).get("full_name", "Unknown"),
                "proposer_id": proposal["proposer_id"],
                "title": proposal["title"],
                "description": proposal["description"],
                "category": proposal["category"],
                "start_time": proposal["start_time"],
                "end_time": proposal["end_time"],
                "votes_for": proposal.get("votes_for", "0"),
                "votes_against": proposal.get("votes_against", "0"),
                "votes_abstain": proposal.get("votes_abstain", "0"),
                "total_votes": proposal.get("total_votes", "0"),
                "status": proposal["status"],
                "executed": proposal.get("executed", False),
                "cancelled": proposal.get("cancelled", False),
                "blockchain_hash": proposal.get("blockchain_hash"),
                "created_at": proposal["created_at"],
                "updated_at": proposal.get("updated_at")
            }
            
            proposals.append(proposal_response)
        
        return {
            "success": True,
            "proposals": proposals,
            "total": len(proposals),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to get governance proposals", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get proposals: {str(e)}"
        )


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get a specific governance proposal"""
    
    try:
        supabase = get_supabase_service()
        
        # Get proposal from database
        result = supabase.table(Tables.GOVERNANCE_PROPOSALS).select(
            "*, proposer:users(id, full_name, email)"
        ).eq("id", proposal_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        proposal = result.data[0]
        
        # Get user's vote if any
        user_vote = None
        vote_result = supabase.table(Tables.GOVERNANCE_VOTES).select("*").eq(
            "proposal_id", proposal_id
        ).eq("voter_id", current_user["id"]).execute()
        
        if vote_result.data:
            user_vote = vote_result.data[0]
        
        # Get blockchain data
        blockchain_data = None
        if proposal.get("blockchain_hash"):
            blockchain_data = await blockchain_service.get_proposal_from_blockchain(proposal_id)
        
        return {
            "success": True,
            "proposal": {
                "id": proposal["id"],
                "proposer": proposal.get("proposer", {}).get("full_name", "Unknown"),
                "proposer_id": proposal["proposer_id"],
                "title": proposal["title"],
                "description": proposal["description"],
                "category": proposal["category"],
                "start_time": proposal["start_time"],
                "end_time": proposal["end_time"],
                "votes_for": proposal.get("votes_for", "0"),
                "votes_against": proposal.get("votes_against", "0"),
                "votes_abstain": proposal.get("votes_abstain", "0"),
                "total_votes": proposal.get("total_votes", "0"),
                "status": proposal["status"],
                "executed": proposal.get("executed", False),
                "cancelled": proposal.get("cancelled", False),
                "blockchain_hash": proposal.get("blockchain_hash"),
                "created_at": proposal["created_at"],
                "updated_at": proposal.get("updated_at")
            },
            "user_vote": user_vote,
            "blockchain_data": blockchain_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get governance proposal", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get proposal: {str(e)}"
        )


@router.post("/proposals/{proposal_id}/vote")
async def cast_vote(
    proposal_id: int,
    vote: VoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Cast a vote on a governance proposal"""
    
    try:
        user_id = current_user.get("id")
        
        # Validate proposal exists and is active
        supabase = get_supabase_service()
        proposal_result = supabase.table(Tables.GOVERNANCE_PROPOSALS).select("*").eq(
            "id", proposal_id
        ).execute()
        
        if not proposal_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found"
            )
        
        proposal = proposal_result.data[0]
        
        if proposal["status"] != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proposal is not active for voting"
            )
        
        # Check if voting period is still active
        end_time = datetime.fromisoformat(proposal["end_time"].replace('Z', '+00:00'))
        if datetime.utcnow() > end_time.replace(tzinfo=None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Voting period has ended"
            )
        
        # Check if user already voted
        existing_vote = supabase.table(Tables.GOVERNANCE_VOTES).select("*").eq(
            "proposal_id", proposal_id
        ).eq("voter_id", user_id).execute()
        
        if existing_vote.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already voted on this proposal"
            )
        
        # Get user's voting power (YTILI token balance)
        voting_power = await blockchain_service.get_ytili_balance(user_id)
        
        if voting_power <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No voting power (YTILI tokens required)"
            )
        
        # Cast vote on blockchain
        blockchain_tx = await blockchain_service.cast_governance_vote(
            proposal_id=proposal_id,
            voter=user_id,
            vote_type=vote.vote_type,
            voting_power=voting_power
        )
        
        if not blockchain_tx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cast vote on blockchain"
            )
        
        # Store vote in database
        vote_data = {
            "proposal_id": proposal_id,
            "voter_id": user_id,
            "vote_type": vote.vote_type,
            "voting_power": str(voting_power),
            "blockchain_hash": blockchain_tx,
            "created_at": datetime.utcnow().isoformat()
        }
        
        vote_result = supabase.table(Tables.GOVERNANCE_VOTES).insert(vote_data).execute()
        
        if not vote_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store vote in database"
            )
        
        # Update proposal vote counts
        await _update_proposal_vote_counts(proposal_id)
        
        # Send notification
        vote_type_names = ["For", "Against", "Abstain"]
        await notification_service.notify_system_message(
            message=f"New vote cast on proposal: {proposal['title']} - Vote: {vote_type_names[vote.vote_type]}",
            notification_type="info",
            target_users=[proposal["proposer_id"]]
        )
        
        logger.info(
            "Governance vote cast",
            proposal_id=proposal_id,
            voter=user_id,
            vote_type=vote.vote_type,
            voting_power=voting_power
        )
        
        return {
            "success": True,
            "vote_id": vote_result.data[0]["id"],
            "blockchain_hash": blockchain_tx,
            "message": "Vote cast successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cast governance vote", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cast vote: {str(e)}"
        )


async def _update_proposal_vote_counts(proposal_id: int):
    """Update proposal vote counts from database"""
    
    try:
        supabase = get_supabase_service()
        
        # Get all votes for this proposal
        votes_result = supabase.table(Tables.GOVERNANCE_VOTES).select("*").eq(
            "proposal_id", proposal_id
        ).execute()
        
        votes_for = 0
        votes_against = 0
        votes_abstain = 0
        total_votes = 0
        
        for vote in votes_result.data or []:
            voting_power = int(vote["voting_power"])
            vote_type = vote["vote_type"]
            
            if vote_type == 0:  # For
                votes_for += voting_power
            elif vote_type == 1:  # Against
                votes_against += voting_power
            elif vote_type == 2:  # Abstain
                votes_abstain += voting_power
            
            total_votes += voting_power
        
        # Update proposal
        supabase.table(Tables.GOVERNANCE_PROPOSALS).update({
            "votes_for": str(votes_for),
            "votes_against": str(votes_against),
            "votes_abstain": str(votes_abstain),
            "total_votes": str(total_votes),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", proposal_id).execute()
        
    except Exception as e:
        logger.error("Failed to update proposal vote counts", error=str(e))


@router.get("/stats")
async def get_governance_stats(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get governance statistics"""
    
    try:
        supabase = get_supabase_service()
        
        # Get total proposals
        total_proposals = supabase.table(Tables.GOVERNANCE_PROPOSALS).select(
            "id", count="exact"
        ).execute()
        
        # Get active proposals
        active_proposals = supabase.table(Tables.GOVERNANCE_PROPOSALS).select(
            "id", count="exact"
        ).eq("status", "active").execute()
        
        # Get executed proposals
        executed_proposals = supabase.table(Tables.GOVERNANCE_PROPOSALS).select(
            "id", count="exact"
        ).eq("status", "executed").execute()
        
        # Get total votes
        total_votes = supabase.table(Tables.GOVERNANCE_VOTES).select(
            "id", count="exact"
        ).execute()
        
        # Get user's participation
        user_proposals = supabase.table(Tables.GOVERNANCE_PROPOSALS).select(
            "id", count="exact"
        ).eq("proposer_id", current_user["id"]).execute()
        
        user_votes = supabase.table(Tables.GOVERNANCE_VOTES).select(
            "id", count="exact"
        ).eq("voter_id", current_user["id"]).execute()
        
        return {
            "success": True,
            "stats": {
                "total_proposals": total_proposals.count or 0,
                "active_proposals": active_proposals.count or 0,
                "executed_proposals": executed_proposals.count or 0,
                "total_votes": total_votes.count or 0,
                "user_proposals": user_proposals.count or 0,
                "user_votes": user_votes.count or 0,
                "min_proposal_threshold": "1000 YTILI",
                "voting_period": "7 days",
                "quorum_percentage": "10%"
            }
        }
        
    except Exception as e:
        logger.error("Failed to get governance stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get governance stats: {str(e)}"
        )

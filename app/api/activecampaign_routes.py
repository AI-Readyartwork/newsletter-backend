"""
ActiveCampaign API Routes

Endpoints for integrating with ActiveCampaign:
- GET /activecampaign/lists - Fetch subscriber lists
- GET /activecampaign/addresses - Fetch mailing addresses
- POST /activecampaign/push - Create campaign (draft, scheduled, or immediate)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from app.services.activecampaign_service import get_activecampaign_service

router = APIRouter()


class PushCampaignRequest(BaseModel):
    """Request body for pushing a newsletter to ActiveCampaign."""
    listId: str
    campaignName: str
    subject: str
    htmlContent: str
    campaignStatus: Literal["draft", "scheduled", "immediate"] = "draft"
    addressId: Optional[str] = None  # Mailing address ID
    scheduledDate: Optional[str] = None  # ISO format: "2026-01-20T10:00:00"
    senderName: Optional[str] = None
    senderEmail: Optional[str] = None


class PushCampaignResponse(BaseModel):
    """Response from push campaign endpoint."""
    success: bool
    campaignId: str
    status: str
    message: str


class ListItem(BaseModel):
    """A single subscriber list."""
    id: str
    name: str


class ListsResponse(BaseModel):
    """Response containing all subscriber lists."""
    lists: list[ListItem]


class AddressItem(BaseModel):
    """A single mailing address."""
    id: str
    companyName: str
    display: str


class AddressesResponse(BaseModel):
    """Response containing all mailing addresses."""
    addresses: list[AddressItem]


@router.get("/lists", response_model=ListsResponse)
async def get_lists():
    """
    Fetch all subscriber lists from ActiveCampaign.
    
    Returns:
        List of subscriber lists with id and name
    """
    try:
        service = get_activecampaign_service()
        lists = await service.get_lists()
        return {"lists": lists}
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"ActiveCampaign not configured: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch lists: {str(e)}"
        )


@router.get("/addresses", response_model=AddressesResponse)
async def get_addresses():
    """
    Fetch all mailing addresses from ActiveCampaign.
    
    Returns:
        List of mailing addresses with id, companyName, and display string
    """
    try:
        service = get_activecampaign_service()
        addresses = await service.get_addresses()
        return {"addresses": addresses}
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"ActiveCampaign not configured: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch addresses: {str(e)}"
        )


@router.post("/push", response_model=PushCampaignResponse)
async def push_campaign(request: PushCampaignRequest):
    """
    Create a campaign in ActiveCampaign.
    
    Supports three modes:
    - draft: Creates campaign as draft (not sent)
    - scheduled: Schedules campaign for future send (requires scheduledDate)
    - immediate: Sends campaign immediately
    
    Args:
        request: Campaign details including list ID, name, subject, HTML content, and status
        
    Returns:
        Success status with campaign ID and status
    """
    try:
        service = get_activecampaign_service()
        result = await service.push_newsletter(
            list_id=request.listId,
            campaign_name=request.campaignName,
            subject=request.subject,
            html_content=request.htmlContent,
            campaign_status=request.campaignStatus,
            address_id=request.addressId,
            scheduled_date=request.scheduledDate,
            sender_name=request.senderName,
            sender_email=request.senderEmail
        )
        
        # Generate appropriate message based on status
        status_messages = {
            "draft": "Campaign draft created successfully",
            "scheduled": f"Campaign scheduled for {request.scheduledDate}",
            "immediate": "Campaign sent successfully"
        }
        
        return {
            "success": True,
            "campaignId": result["campaign_id"],
            "status": result["status"],
            "message": status_messages.get(result["status"], "Campaign created")
        }
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"ActiveCampaign not configured: {str(e)}"
        )
    except Exception as e:
        error_msg = str(e)
        # Try to extract more details from HTTP errors
        if hasattr(e, 'response'):
            try:
                error_data = e.response.json()
                if 'message' in error_data:
                    error_msg = error_data['message']
                elif 'errors' in error_data:
                    error_msg = str(error_data['errors'])
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to push campaign: {error_msg}"
        )

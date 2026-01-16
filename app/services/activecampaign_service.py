"""
ActiveCampaign API Service

Handles all interactions with the ActiveCampaign API:
- v3 API for fetching lists and creating messages
- v1 API for campaign creation (v3 has limitations for campaign-message linking)

Supports campaign status:
- Draft (status=0)
- Scheduled (status=1 with sdate)
- Send Immediately (status=1 without sdate)
"""

import httpx
from typing import Optional
from datetime import datetime
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ActiveCampaignService:
    """Service class for ActiveCampaign API interactions."""
    
    def __init__(self):
        self.base_url = settings.ACTIVECAMPAIGN_URL
        self.api_key = settings.ACTIVECAMPAIGN_API_KEY
        self.sender_name = settings.ACTIVECAMPAIGN_SENDER_NAME
        self.sender_email = settings.ACTIVECAMPAIGN_SENDER_EMAIL
        
        if not self.base_url or not self.api_key:
            raise ValueError("ActiveCampaign URL and API Key must be configured")
        
        # Ensure base URL doesn't have trailing slash
        self.base_url = self.base_url.rstrip('/')
        
        # Headers for v3 API
        self.headers_v3 = {
            "Api-Token": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _handle_response_v3(self, response, operation_name: str) -> dict:
        """Handle v3 API response and raise descriptive errors."""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    error_msg = str(error_data['errors'])
                elif 'message' in error_data:
                    error_msg = error_data['message']
                else:
                    error_msg = str(error_data)
            except:
                error_msg = response.text or f"HTTP {response.status_code}"
            
            raise Exception(f"{operation_name} failed: {error_msg} (HTTP {response.status_code})")
        
        return response.json()
    
    def _handle_response_v1(self, response, operation_name: str) -> dict:
        """Handle v1 API response and raise descriptive errors."""
        try:
            data = response.json()
        except:
            raise Exception(f"{operation_name} failed: {response.text}")
        
        # v1 API returns result_code: 1 for success, 0 for failure
        if data.get('result_code') == 0:
            error_msg = data.get('result_message', 'Unknown error')
            raise Exception(f"{operation_name} failed: {error_msg}")
        
        return data
    
    async def get_lists(self) -> list[dict]:
        """
        Fetch all subscriber lists from ActiveCampaign using v3 API.
        
        Returns:
            List of dicts with 'id' and 'name' for each list
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/3/lists",
                headers=self.headers_v3,
                timeout=30.0
            )
            data = self._handle_response_v3(response, "Get lists")
            
            return [
                {"id": lst["id"], "name": lst["name"]}
                for lst in data.get("lists", [])
            ]
    
    async def get_addresses(self) -> list[dict]:
        """
        Fetch all mailing addresses from ActiveCampaign using v3 API.
        
        Returns:
            List of dicts with 'id', 'companyName', and formatted address
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/3/addresses",
                headers=self.headers_v3,
                timeout=30.0
            )
            data = self._handle_response_v3(response, "Get addresses")
            
            addresses = []
            for addr in data.get("addresses", []):
                # Build display string
                parts = [addr.get("companyName", "")]
                if addr.get("address1"):
                    parts.append(addr.get("address1"))
                if addr.get("city"):
                    city_state = addr.get("city", "")
                    if addr.get("state"):
                        city_state += f", {addr.get('state')}"
                    parts.append(city_state)
                
                display = " - ".join([p for p in parts if p])
                
                addresses.append({
                    "id": addr["id"],
                    "companyName": addr.get("companyName", ""),
                    "display": display or f"Address #{addr['id']}"
                })
            
            return addresses
    
    async def create_message_v3(
        self,
        subject: str,
        html_content: str,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> str:
        """
        Create an email message using v3 API.
        
        Returns:
            Message ID
        """
        payload = {
            "message": {
                "fromname": sender_name or self.sender_name,
                "fromemail": sender_email or self.sender_email,
                "reply2": sender_email or self.sender_email,
                "subject": subject,
                "html": html_content,
                "text": "Please view this email in an HTML-compatible email client."
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/3/messages",
                headers=self.headers_v3,
                json=payload,
                timeout=60.0
            )
            data = self._handle_response_v3(response, "Create message (v3)")
            
            return data["message"]["id"]
    
    async def create_campaign_v1(
        self,
        list_id: str,
        message_id: str,
        campaign_name: str,
        subject: str,
        campaign_status: str = "draft",  # "draft", "scheduled", "immediate"
        scheduled_date: Optional[str] = None,  # ISO format: "2026-01-20T10:00:00"
        address_id: Optional[str] = None,  # Mailing address ID
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> str:
        """
        Create a campaign using v1 API.
        
        Args:
            list_id: Target subscriber list ID
            message_id: Message ID to use
            campaign_name: Campaign name
            subject: Email subject
            campaign_status: "draft", "scheduled", or "immediate"
            scheduled_date: ISO date string for scheduled campaigns
            address_id: Mailing address ID (0 for default)
            sender_name: Optional sender name override
            sender_email: Optional sender email override
            
        Returns:
            Campaign ID
        """
        params = {
            "api_key": self.api_key,
            "api_action": "campaign_create",
            "api_output": "json"
        }
        
        # Determine status and schedule date
        if campaign_status == "draft":
            status = 0
            sdate = ""
        elif campaign_status == "scheduled":
            status = 1
            # Convert ISO date to ActiveCampaign format: YYYY-MM-DD HH:MM:SS
            if scheduled_date:
                try:
                    dt = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                    sdate = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    sdate = scheduled_date
            else:
                raise Exception("Scheduled date is required for scheduled campaigns")
        else:  # immediate
            status = 1
            sdate = ""
        
        # Form data for campaign creation
        form_data = {
            "type": "single",
            "name": campaign_name,
            "sdate": sdate,
            "status": status,
            "public": 1,
            "tracklinks": "all",
            "trackreads": 1,
            "trackreplies": 0,
            "htmlunsub": 1,
            "textunsub": 1,
            "analytics_campaign_name": campaign_name,
            # Address ID (0 for default, or specific address ID)
            "addressid": address_id if address_id else 0,
            # List to send to
            f"p[{list_id}]": list_id,
            # Message to use (100 means 100% of recipients)
            f"m[{message_id}]": 100,
            # Sender info
            "fromemail": sender_email or self.sender_email,
            "fromname": sender_name or self.sender_name,
            "reply2": sender_email or self.sender_email,
            "subject": subject
        }
        
        async with httpx.AsyncClient() as client:
            logger.info(f"Creating campaign: name={campaign_name}, status={campaign_status}, list={list_id}, message={message_id}")
            
            response = await client.post(
                f"{self.base_url}/admin/api.php",
                params=params,
                data=form_data,
                timeout=30.0
            )
            data = self._handle_response_v1(response, "Create campaign (v1)")
            campaign_id = str(data.get('id'))
            
            logger.info(f"Campaign created: ID={campaign_id}, status={campaign_status}")
            return campaign_id
    
    async def push_newsletter(
        self,
        list_id: str,
        campaign_name: str,
        subject: str,
        html_content: str,
        campaign_status: str = "draft",  # "draft", "scheduled", "immediate"
        address_id: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None
    ) -> dict:
        """
        Complete flow to push a newsletter to ActiveCampaign.
        
        This orchestrates:
        1. Create message with HTML content (v3 API)
        2. Create campaign with message and list (v1 API)
        
        Args:
            list_id: Target subscriber list ID
            campaign_name: Name for the campaign
            subject: Email subject line
            html_content: Full HTML content
            campaign_status: "draft", "scheduled", or "immediate"
            address_id: Mailing address ID for the campaign
            scheduled_date: ISO date string for scheduled campaigns
            sender_name: Optional sender name override
            sender_email: Optional sender email override
            
        Returns:
            Dict with campaign_id, message_id, and status
        """
        try:
            # Step 1: Create message using v3 API
            logger.info(f"Step 1: Creating message with subject: {subject}")
            message_id = await self.create_message_v3(
                subject=subject,
                html_content=html_content,
                sender_name=sender_name,
                sender_email=sender_email
            )
            logger.info(f"Step 1 complete: Message ID = {message_id}")
        except Exception as e:
            logger.error(f"Step 1 FAILED (create_message): {e}")
            raise Exception(f"Failed to create message: {e}")
        
        try:
            # Step 2: Create campaign using v1 API
            logger.info(f"Step 2: Creating campaign: {campaign_name} for list: {list_id}")
            campaign_id = await self.create_campaign_v1(
                list_id=list_id,
                message_id=message_id,
                campaign_name=campaign_name,
                subject=subject,
                campaign_status=campaign_status,
                scheduled_date=scheduled_date,
                address_id=address_id,
                sender_name=sender_name,
                sender_email=sender_email
            )
            logger.info(f"Step 2 complete: Campaign ID = {campaign_id}")
        except Exception as e:
            logger.error(f"Step 2 FAILED (create_campaign): {e}")
            raise Exception(f"Failed to create campaign: {e}")
        
        return {
            "campaign_id": campaign_id,
            "message_id": message_id,
            "status": campaign_status
        }


# Singleton instance
_service_instance: Optional[ActiveCampaignService] = None


def get_activecampaign_service() -> ActiveCampaignService:
    """Get or create the ActiveCampaign service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ActiveCampaignService()
    return _service_instance

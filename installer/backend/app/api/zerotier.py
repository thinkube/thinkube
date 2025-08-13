# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
ZeroTier API integration for network configuration
"""
import httpx
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["zerotier"])

class ZeroTierNetworkRequest(BaseModel):
    network_id: str
    api_token: str

class ZeroTierNetworkResponse(BaseModel):
    success: bool
    network_name: str = ""
    cidr: str = ""
    message: str = ""

class ZeroTierMembersResponse(BaseModel):
    success: bool
    members: list = []
    used_ips: list = []
    message: str = ""

@router.post("/fetch-zerotier-network", response_model=ZeroTierNetworkResponse)
async def fetch_zerotier_network(request: ZeroTierNetworkRequest):
    """
    Fetch ZeroTier network configuration including CIDR range
    """
    print(f"Fetching ZeroTier network: {request.network_id}")
    try:
        url = f"https://api.zerotier.com/api/v1/network/{request.network_id}"
        print(f"ZeroTier API URL: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {request.api_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            print(f"ZeroTier API response status: {response.status_code}")
            print(f"ZeroTier API response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"ZeroTier API response body: {response.text}")
            
            
            if response.status_code == 200:
                network_data = response.json()
                print(f"ZeroTier network data: {json.dumps(network_data, indent=2)}")
                
                # Extract CIDR from routes (in config section)
                config = network_data.get("config", {})
                routes = config.get("routes", [])
                print(f"ZeroTier routes: {routes}")
                cidr = ""
                
                if routes:
                    # Look for the main network route (usually the first one)
                    for route in routes:
                        target = route.get("target", "")
                        print(f"Checking route target: {target}")
                        if "/" in target and not target.startswith("169.254"):  # Skip link-local
                            cidr = target
                            print(f"Found CIDR: {cidr}")
                            break
                
                if not cidr:
                    return ZeroTierNetworkResponse(
                        success=False,
                        message="No valid CIDR range found in network routes"
                    )
                
                return ZeroTierNetworkResponse(
                    success=True,
                    network_name=network_data.get("name", ""),
                    cidr=cidr,
                    message="Network details retrieved successfully"
                )
                
            elif response.status_code == 401:
                return ZeroTierNetworkResponse(
                    success=False,
                    message="Invalid API token"
                )
            elif response.status_code == 404:
                return ZeroTierNetworkResponse(
                    success=False,
                    message="Network not found or no access"
                )
            else:
                return ZeroTierNetworkResponse(
                    success=False,
                    message=f"ZeroTier API error: {response.status_code}"
                )
                
    except httpx.TimeoutException:
        return ZeroTierNetworkResponse(
            success=False,
            message="Request timeout - check network connection"
        )
    except Exception as e:
        return ZeroTierNetworkResponse(
            success=False,
            message=f"Error fetching network details: {str(e)}"
        )

@router.post("/fetch-zerotier-members", response_model=ZeroTierMembersResponse)
async def fetch_zerotier_members(request: ZeroTierNetworkRequest):
    """
    Fetch ZeroTier network members and their assigned IPs
    """
    print(f"Fetching ZeroTier members for network: {request.network_id}")
    try:
        url = f"https://api.zerotier.com/api/v1/network/{request.network_id}/member"
        print(f"ZeroTier Members API URL: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {request.api_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            print(f"ZeroTier Members API response status: {response.status_code}")
            
            if response.status_code == 200:
                members_data = response.json()
                print(f"Found {len(members_data)} members")
                
                members = []
                used_ips = []
                
                for member in members_data:
                    member_info = {
                        "nodeId": member.get("nodeId"),
                        "name": member.get("name", ""),
                        "online": member.get("online", False),
                        "authorized": member.get("config", {}).get("authorized", False),
                        "ipAssignments": member.get("config", {}).get("ipAssignments", [])
                    }
                    members.append(member_info)
                    
                    # Collect all assigned IPs
                    for ip in member_info["ipAssignments"]:
                        if ip and ip not in used_ips:
                            used_ips.append(ip)
                
                print(f"Used IPs: {used_ips}")
                
                return ZeroTierMembersResponse(
                    success=True,
                    members=members,
                    used_ips=sorted(used_ips),
                    message=f"Found {len(members)} members with {len(used_ips)} assigned IPs"
                )
                
            elif response.status_code == 401:
                return ZeroTierMembersResponse(
                    success=False,
                    message="Invalid API token"
                )
            elif response.status_code == 404:
                return ZeroTierMembersResponse(
                    success=False,
                    message="Network not found or no access"
                )
            else:
                return ZeroTierMembersResponse(
                    success=False,
                    message=f"ZeroTier API error: {response.status_code}"
                )
                
    except httpx.TimeoutException:
        return ZeroTierMembersResponse(
            success=False,
            message="Request timeout - check network connection"
        )
    except Exception as e:
        return ZeroTierMembersResponse(
            success=False,
            message=f"Error fetching members: {str(e)}"
        )